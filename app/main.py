"""FastAPI 应用入口：路由注册、静态资源挂载、统一异常处理。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import init_db
from app.routers import admin, auth, chat, documents, pages
from app.services.rag_service import RagService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent

# 校验错误的中文字段名与类型说明，避免把英文报错暴露给前端
FIELD_LABELS = {
    "username": "用户名",
    "password": "密码",
    "question": "问题内容",
    "role": "角色",
    "rating": "评价",
    "title": "标题",
    "files": "上传文件",
}
TYPE_MESSAGES = {
    "missing": "不能为空",
    "string_too_short": "长度不足",
    "string_too_long": "长度超出限制",
    "string_pattern_mismatch": "格式不正确",
    "literal_error": "取值不在允许范围内",
    "int_parsing": "必须为整数",
    "value_error": "取值不合法",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用启动时准备目录与数据表。"""
    for directory in (settings.upload_dir, settings.vector_store_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)
    init_db()
    # 预热向量化模型：避免首次问答因加载 bge 阻塞数十秒
    try:
        RagService.instance()._ensure_embeddings()
        logger.info("向量化模型预热完成，首次问答将快速响应")
    except Exception as exc:
        logger.warning("向量化模型预热失败，将在首次问答时懒加载：%s", exc)
    logger.info("%s 启动完成", settings.app_name)
    yield


app = FastAPI(
    title=settings.app_name,
    description=(
        "面向中小企业的智能客服知识库系统后端接口。\n\n"
        "统一响应格式：`{\"code\": 0, \"message\": \"成功\", \"data\": ...}`；"
        "统一异常格式：`{\"code\": <HTTP状态码>, \"message\": \"中文提示\", \"data\": null}`。\n\n"
        "鉴权方式：登录后在请求头携带 `Authorization: Bearer <token>`。"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(admin.router)


@app.get("/health", tags=["系统"], summary="健康检查", description="用于部署后探活，返回服务状态。")
def health() -> dict:
    """健康检查接口。"""
    return {"status": "ok"}


def _error_response(status_code: int, message: str) -> JSONResponse:
    """构造统一异常响应。"""
    return JSONResponse(
        status_code=status_code,
        content={"code": status_code, "message": message, "data": None},
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    """HTTP 异常统一返回中文提示。"""
    detail = exc.detail if isinstance(exc.detail, str) else "请求处理失败"
    return _error_response(exc.status_code, detail)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """参数校验异常统一返回中文提示。"""
    first = exc.errors()[0] if exc.errors() else {}
    location = [part for part in first.get("loc", []) if part not in ("body", "query", "path")]
    field = str(location[-1]) if location else "参数"
    label = FIELD_LABELS.get(field, field)
    reason = TYPE_MESSAGES.get(first.get("type", ""), "格式不正确")
    return _error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, f"{label}{reason}")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """兜底异常处理：记录完整堆栈，对外仅返回中文提示。"""
    logger.exception("未处理异常：%s %s", request.method, request.url.path)
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, "服务器内部错误，请稍后重试"
    )
