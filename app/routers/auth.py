"""鉴权路由：注册、登录、当前用户。"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import User
from app.schemas import ApiResponse, LoginRequest, RegisterRequest, TokenOut, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["鉴权"])


@router.post(
    "/register",
    response_model=ApiResponse[UserOut],
    summary="用户注册",
    description="注册新用户。系统首个注册账号自动成为管理员，其余为普通用户。",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> ApiResponse[UserOut]:
    """注册新用户。"""
    exists = db.scalar(select(User).where(User.username == payload.username))
    if exists is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该用户名已被注册，请更换后重试"
        )

    is_first_user = (db.scalar(select(func.count(User.id))) or 0) == 0
    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="admin" if is_first_user else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    message = "注册成功，您是系统首位用户，已自动成为管理员" if is_first_user else "注册成功"
    return ApiResponse[UserOut](message=message, data=UserOut.model_validate(user))


@router.post(
    "/login",
    response_model=ApiResponse[TokenOut],
    summary="用户登录",
    description="校验用户名与密码，成功后返回 JWT 访问令牌，前端需在请求头携带 Authorization: Bearer <token>。",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> ApiResponse[TokenOut]:
    """登录并签发 JWT。"""
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    token = create_access_token(subject=str(user.id), role=user.role)
    return ApiResponse[TokenOut](
        message="登录成功",
        data=TokenOut(access_token=token, username=user.username, role=user.role),
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserOut],
    summary="获取当前登录用户",
    description="根据请求头中的 JWT 返回当前用户信息，用于前端判断登录态与角色。",
)
def me(current_user: User = Depends(get_current_user)) -> ApiResponse[UserOut]:
    """返回当前用户信息。"""
    return ApiResponse[UserOut](data=UserOut.model_validate(current_user))
