from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from schemas.schema import UserResponse, UserUpdate
from core.security import get_current_active_user, get_password_hash
from core.logger import logger

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    try:
        logger.info(f"👤 用户 {current_user.username} 获取个人信息")
        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取用户信息异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"获取用户信息失败: {str(e)}")


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"✏️ 用户 {current_user.username} 更新个人信息")
        
        if update_data.email:
            existing_user = db.query(User).filter(
                User.email == update_data.email,
                User.id != current_user.id
            ).first()
            if existing_user:
                logger.warning(f"❌ 邮箱已被使用: {update_data.email}")
                raise HTTPException(status_code=400, detail="邮箱已被其他用户使用")

        if update_data.full_name is not None:
            current_user.full_name = update_data.full_name

        if update_data.email:
            current_user.email = update_data.email

        if update_data.password:
            current_user.hashed_password = get_password_hash(update_data.password)

        if update_data.project_folder is not None:
            current_user.project_folder = update_data.project_folder

        db.commit()
        db.refresh(current_user)
        logger.info(f"✅ 用户信息更新成功: {current_user.username}")
        return current_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新用户信息异常: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"更新用户信息失败: {str(e)}")


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"🗑️ 用户 {current_user.username} 删除账户")
        db.delete(current_user)
        db.commit()
        logger.info(f"✅ 用户账户删除成功: {current_user.username}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 删除用户账户异常: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"删除用户账户失败: {str(e)}")
