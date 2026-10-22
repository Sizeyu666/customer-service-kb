"""Pydantic 数据模型（请求体 / 响应体）。

统一响应格式：{"code": 0, "message": "成功", "data": ...}
异常响应格式：{"code": <HTTP 状态码>, "message": "中文提示", "data": null}
"""

from datetime import datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应包装。"""

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="成功", description="中文提示信息")
    data: T | None = Field(default=None, description="业务数据")


# ---------------------------------------------------------------------------
# 用户与鉴权
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    """注册请求。"""

    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=r"^[A-Za-z0-9_\u4e00-\u9fa5]+$",
        description="用户名：3-32 位，支持中英文、数字、下划线",
        examples=["admin"],
    )
    password: str = Field(min_length=6, max_length=72, description="密码：至少 6 位", examples=["admin123"])


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str = Field(min_length=1, max_length=32, description="用户名", examples=["admin"])
    password: str = Field(min_length=1, max_length=72, description="密码", examples=["admin123"])


class UserOut(BaseModel):
    """用户信息（不含密码）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="用户 ID")
    username: str = Field(description="用户名")
    role: str = Field(description="角色：user / admin")
    created_at: datetime = Field(description="注册时间")


class TokenOut(BaseModel):
    """登录成功后返回的令牌信息。"""

    access_token: str = Field(description="JWT 访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    username: str = Field(description="用户名")
    role: str = Field(description="角色：user / admin")


class RoleUpdateRequest(BaseModel):
    """管理员修改用户角色。"""

    role: Literal["user", "admin"] = Field(description="目标角色", examples=["admin"])


# ---------------------------------------------------------------------------
# 知识库文档
# ---------------------------------------------------------------------------
class DocumentOut(BaseModel):
    """知识库文档信息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="文档 ID")
    filename: str = Field(description="原始文件名")
    file_type: str = Field(description="文件类型：pdf/docx/txt/md")
    chunk_count: int = Field(description="文本块数量")
    status: str = Field(description="状态：processing / ready / failed")
    error_msg: str | None = Field(default=None, description="失败原因")
    created_at: datetime = Field(description="上传时间")


class UploadResult(BaseModel):
    """批量上传结果。"""

    success: list[DocumentOut] = Field(default_factory=list, description="上传成功的文档")
    failed: list[dict] = Field(default_factory=list, description="失败的文档及中文原因")
    message: str = Field(description="整体结果说明")


class RebuildResult(BaseModel):
    """重建索引结果。"""

    total: int = Field(description="参与重建的文档数")
    success: int = Field(description="重建成功数")
    failed: int = Field(description="重建失败数")
    message: str = Field(description="结果说明")


# ---------------------------------------------------------------------------
# 会话与消息
# ---------------------------------------------------------------------------
class ConversationOut(BaseModel):
    """会话概要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="会话 ID")
    title: str = Field(description="会话标题")
    created_at: datetime = Field(description="创建时间")
    message_count: int = Field(default=0, description="消息条数")


class ConversationCreateRequest(BaseModel):
    """新建会话请求。"""

    title: str | None = Field(default=None, max_length=120, description="会话标题，默认「新会话」")


class MessageOut(BaseModel):
    """单条消息。"""

    id: int = Field(description="消息 ID")
    conversation_id: int = Field(description="所属会话 ID")
    role: str = Field(description="角色：user / assistant")
    content: str = Field(description="消息内容")
    sources: list[str] = Field(default_factory=list, description="参考来源文件名列表")
    feedback: str | None = Field(default=None, description="当前评价：up / down")
    created_at: datetime = Field(description="创建时间")


class ChatRequest(BaseModel):
    """提问请求。"""

    question: str = Field(min_length=1, max_length=2000, description="用户问题", examples=["支持七天无理由退货吗"])


class ChatResponse(BaseModel):
    """问答响应。"""

    conversation_id: int = Field(description="会话 ID")
    message_id: int = Field(description="本次助手消息 ID")
    title: str = Field(description="会话标题")
    answer: str = Field(description="助手回答")
    sources: list[str] = Field(default_factory=list, description="参考来源文件名列表")


class FeedbackRequest(BaseModel):
    """点赞 / 点踩请求。"""

    rating: Literal["up", "down"] = Field(description="评价：up 点赞，down 点踩")


# ---------------------------------------------------------------------------
# 管理看板
# ---------------------------------------------------------------------------
class AdminStats(BaseModel):
    """管理后台统计看板数据。"""

    users: int = Field(description="用户数")
    documents: int = Field(description="文档数")
    conversations: int = Field(description="会话数")
    messages: int = Field(description="消息数")
