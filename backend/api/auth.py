from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from db.database import get_db
from models.user import User
from schemas.schema import UserCreate, UserResponse, Token, TokenRefresh, LoginRequest
from core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from datetime import timedelta
from core.config import settings
from core.logger import logger

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    logger.info(f"🔍 [DEBUG 1] register函数开始执行")
    try:
        logger.info(f"👤 用户注册请求: {user_data.username}")
        
        logger.info(f"🔍 [DEBUG 2] 开始查询数据库")
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        logger.info(f"🔍 [DEBUG 3] 数据库查询完成, result: {existing_user}")

        if existing_user:
            logger.warning(f"❌ 用户名已存在: {user_data.username}")
            raise HTTPException(status_code=400, detail="用户名已存在")

        existing_email = db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            logger.warning(f"❌ 邮箱已被注册: {user_data.email}")
            raise HTTPException(status_code=400, detail="邮箱已被注册")

        logger.info(f"🔐 正在创建用户: {user_data.username}")
        hashed_password = get_password_hash(user_data.password)
        logger.info(f"🔐 密码加密完成")
        
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            hashed_password=hashed_password
        )
        logger.info(f"💾 正在保存用户到数据库")
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"💾 用户已保存到数据库，ID: {user.id}")
        
        logger.info(f"✅ 用户注册成功: {user_data.username} (ID: {user.id})")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 注册异常: {str(e)}")
        import traceback
        logger.error(f"❌ 异常堆栈: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(status_code=400, detail=f"注册失败: {str(e)}")


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    try:
        logger.info(f"🔐 用户登录请求: {login_data.username}")
        
        user = db.query(User).filter(User.username == login_data.username).first()
        if not user or not verify_password(login_data.password, user.hashed_password):
            logger.warning(f"❌ 登录失败: 用户名或密码错误 - {login_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            logger.warning(f"❌ 用户已被禁用: {login_data.username}")
            raise HTTPException(status_code=400, detail="用户已被禁用")

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )

        logger.info(f"✅ 用户登录成功: {login_data.username} (ID: {user.id})")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 登录异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"登录失败: {str(e)}")


@router.post("/refresh", response_model=Token)
async def refresh_token(token_data: TokenRefresh, db: Session = Depends(get_db)):
    try:
        logger.info("🔄 刷新令牌请求")
        
        payload = verify_token(token_data.refresh_token, "refresh")
        if payload is None:
            logger.warning("❌ 无效的刷新令牌")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()

        if not user or not user.is_active:
            logger.warning(f"❌ 用户不存在或已被禁用: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )

        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        new_refresh_token = create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        )

        logger.info(f"✅ 令牌刷新成功: {user.username} (ID: {user.id})")
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 刷新令牌异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"刷新令牌失败: {str(e)}")
