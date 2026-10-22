"""管理后台接口：用户管理、角色调整与数据看板（仅管理员）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models import Conversation, Document, Message, User
from app.schemas import AdminStats, ApiResponse, RoleUpdateRequest, UserOut

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


@router.get(
    "/users",
    response_model=ApiResponse[list[UserOut]],
    summary="用户列表",
    description="返回全部注册用户及其角色、注册时间。",
)
def list_users(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> ApiResponse[list[UserOut]]:
    """用户列表。"""
    users = list(db.scalars(select(User).order_by(User.id)))
    return ApiResponse[list[UserOut]](data=[UserOut.model_validate(item) for item in users])


@router.put(
    "/users/{user_id}/role",
    response_model=ApiResponse[UserOut],
    summary="修改用户角色",
    description="管理员调整其他用户角色；系统必须保留至少一名管理员，因此不能把最后一名管理员降为普通用户。",
)
def update_user_role(
    user_id: int,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ApiResponse[UserOut]:
    """调整用户角色。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user.role == payload.role:
        return ApiResponse[UserOut](message="角色未发生变化", data=UserOut.model_validate(user))

    if user.role == "admin" and payload.role == "user":
        admin_count = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系统至少需要保留一名管理员，无法降权最后一名管理员",
            )
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能降低自己的管理员权限，请由其他管理员操作",
            )

    user.role = payload.role
    db.commit()
    db.refresh(user)
    return ApiResponse[UserOut](message="角色已更新", data=UserOut.model_validate(user))


@router.get(
    "/stats",
    response_model=ApiResponse[AdminStats],
    summary="数据看板",
    description="返回用户数、文档数、会话数、消息数四项统计。",
)
def stats(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> ApiResponse[AdminStats]:
    """统计数据。"""
    data = AdminStats(
        users=db.scalar(select(func.count(User.id))) or 0,
        documents=db.scalar(select(func.count(Document.id))) or 0,
        conversations=db.scalar(select(func.count(Conversation.id))) or 0,
        messages=db.scalar(select(func.count(Message.id))) or 0,
    )
    return ApiResponse[AdminStats](data=data)
