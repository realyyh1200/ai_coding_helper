from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import AsyncGenerator
from db.database import get_db
from models.user import User, Conversation, Message
from schemas.schema import ChatRequest, ConversationCreate, ConversationResponse, ConversationUpdate
from core.security import get_current_active_user
from services.anthropic_service import AnthropicService
from services.memory_service import MemoryService
from core.logger import logger
import json

router = APIRouter()


@router.post("/stream")
async def chat_stream(
    chat_data: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"💬 用户 {current_user.username} 发起聊天请求 (会话ID: {chat_data.conversation_id})")

        if not chat_data.message.strip():
            logger.warning(f"❌ 空消息 - 用户: {current_user.username}")
            raise HTTPException(status_code=400, detail="消息不能为空")

        memory_service = MemoryService(db, current_user.id, chat_data.conversation_id)

        conversation = None
        if chat_data.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == chat_data.conversation_id,
                Conversation.user_id == current_user.id
            ).first()
            if not conversation:
                logger.warning(f"❌ 会话不存在 - ID: {chat_data.conversation_id}")
                raise HTTPException(status_code=404, detail="对话不存在")

        if not conversation:
            conversation = Conversation(
                user_id=current_user.id,
                title=chat_data.message[:50] + "..." if len(chat_data.message) > 50 else chat_data.message
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            logger.info(f"✅ 创建新会话 - ID: {conversation.id}, 用户: {current_user.username}")

        user_message = Message(
            conversation_id=conversation.id,
            role="user",
            content=chat_data.message
        )
        db.add(user_message)
        db.commit()

        messages_history = []
        messages = db.query(Message).filter(
            Message.conversation_id == conversation.id
        ).order_by(Message.created_at).all()

        for msg in messages:
            messages_history.append({"role": msg.role, "content": msg.content})

        memory_context = memory_service.get_context_for_ai(include_recent=5)
        enhanced_system_prompt = f"{chat_data.system_prompt}\n\n{memory_context}"

        async def stream_response() -> AsyncGenerator[str, None]:
            anthroic_service = AnthropicService()

            full_response = ""
            try:
                logger.info(f"🤖 开始AI响应生成 - 会话ID: {conversation.id}")
                async for chunk in anthroic_service.stream_chat(
                    messages=messages_history,
                    system_prompt=enhanced_system_prompt
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

                assistant_message = Message(
                    conversation_id=conversation.id,
                    role="assistant",
                    content=full_response
                )
                db.add(assistant_message)
                conversation.updated_at = conversation.updated_at
                db.commit()

                memory_service.add_message("user", chat_data.message)
                memory_service.add_message("assistant", full_response)

                logger.info(f"✅ AI响应完成 - 会话ID: {conversation.id}, 响应长度: {len(full_response)}")
                yield f"data: {json.dumps({'content': '', 'done': True, 'conversation_id': conversation.id})}\n\n"

            except Exception as e:
                logger.error(f"❌ AI响应失败 - 会话ID: {conversation.id}, 错误: {str(e)}")
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 聊天流异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"聊天失败: {str(e)}")


@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"📋 用户 {current_user.username} 获取会话列表")
        conversations = db.query(Conversation).filter(
            Conversation.user_id == current_user.id
        ).order_by(Conversation.updated_at.desc()).all()
        logger.info(f"✅ 获取会话列表成功 - 数量: {len(conversations)}")
        return conversations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取会话列表异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取会话列表失败: {str(e)}")


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"➕ 用户 {current_user.username} 创建新会话: {conversation_data.title}")
        conversation = Conversation(
            user_id=current_user.id,
            title=conversation_data.title
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        logger.info(f"✅ 会话创建成功 - ID: {conversation.id}")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 创建会话异常: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"创建会话失败: {str(e)}")


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"📖 用户 {current_user.username} 获取会话详情 - ID: {conversation_id}")
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

        if not conversation:
            logger.warning(f"❌ 会话不存在 - ID: {conversation_id}")
            raise HTTPException(status_code=404, detail="对话不存在")

        logger.info(f"✅ 获取会话详情成功 - ID: {conversation_id}")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取会话详情异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取会话详情失败: {str(e)}")


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"✏️ 用户 {current_user.username} 更新会话 - ID: {conversation_id}")
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

        if not conversation:
            logger.warning(f"❌ 会话不存在 - ID: {conversation_id}")
            raise HTTPException(status_code=404, detail="对话不存在")

        if update_data.title is not None:
            conversation.title = update_data.title

        db.commit()
        db.refresh(conversation)
        logger.info(f"✅ 会话更新成功 - ID: {conversation_id}, 新标题: {update_data.title}")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新会话异常: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"更新会话失败: {str(e)}")


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"🗑️ 用户 {current_user.username} 删除会话 - ID: {conversation_id}")
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        ).first()

        if not conversation:
            logger.warning(f"❌ 会话不存在 - ID: {conversation_id}")
            raise HTTPException(status_code=404, detail="对话不存在")

        memory_service = MemoryService(db, current_user.id, conversation_id)
        memory_service.clear_conversation_memory()

        db.delete(conversation)
        db.commit()
        logger.info(f"✅ 会话删除成功 - ID: {conversation_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除会话异常: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"删除会话失败: {str(e)}")
