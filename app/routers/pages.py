"""页面路由：返回 Jinja2 渲染的 HTML 页面。

页面本身不做服务端鉴权（前端通过 /api/auth/me 判断登录态与角色），
所有数据访问均由 /api 接口鉴权，避免越权。
"""

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.config import get_settings

settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

router = APIRouter(tags=["页面"], include_in_schema=False)


def _render(request: Request, name: str) -> HTMLResponse:
    """渲染模板并注入通用上下文。"""
    return templates.TemplateResponse(
        request=request, name=name, context={"app_name": settings.app_name}
    )


@router.get("/", summary="首页跳转")
def index() -> RedirectResponse:
    """根路径跳转到问答页。"""
    return RedirectResponse(url="/chat")


@router.get("/login", summary="登录页")
def login_page(request: Request) -> HTMLResponse:
    """登录页面。"""
    return _render(request, "login.html")


@router.get("/register", summary="注册页")
def register_page(request: Request) -> HTMLResponse:
    """注册页面。"""
    return _render(request, "register.html")


@router.get("/chat", summary="客服问答页")
def chat_page(request: Request) -> HTMLResponse:
    """对话页面。"""
    return _render(request, "chat.html")


@router.get("/history", summary="历史记录页")
def history_page(request: Request) -> HTMLResponse:
    """历史记录页面。"""
    return _render(request, "history.html")


@router.get("/documents", summary="知识库管理页")
def documents_page(request: Request) -> HTMLResponse:
    """知识库管理页面（仅管理员可操作）。"""
    return _render(request, "documents.html")


@router.get("/admin", summary="用户管理页")
def admin_page(request: Request) -> HTMLResponse:
    """用户管理与数据看板页面（仅管理员）。"""
    return _render(request, "admin.html")
