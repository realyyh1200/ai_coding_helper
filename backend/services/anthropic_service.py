import anthropic
from typing import AsyncGenerator, List, Dict, Any
from core.config import settings
from core.logger import logger


class AnthropicService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, base_url=settings.ANTHROPIC_API_BASE)
        self.model = settings.ANTHROPIC_MODEL
        logger.info(f"🤖 Anthropic服务初始化 - 模型: {self.model}")

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "你是一个专业的AI编程助手，帮助用户解决编程问题。"
    ) -> AsyncGenerator[str, None]:
        logger.debug(f"📤 发送到AI的消息数量: {len(messages)}")
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            ) as stream:
                for text in stream.text_stream:
                    yield text
            logger.debug("✅ AI流式响应完成")
        except Exception as e:
            logger.error(f"❌ AI服务错误: {str(e)}")
            yield f"Error: {str(e)}"

    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str = "你是一个专业的AI编程助手，帮助用户解决编程问题。"
    ) -> str:
        logger.debug(f"📤 发送同步请求到AI, 消息数量: {len(messages)}")
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=messages
            )
            logger.debug("✅ AI同步响应完成")
            return response.content[0].text
        except Exception as e:
            logger.error(f"❌ AI同步服务错误: {str(e)}")
            return f"Error: {str(e)}"
