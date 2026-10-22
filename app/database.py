"""数据库连接与会话管理。

开发环境使用 SQLite，生产环境通过 DATABASE_URL 切换到 MySQL 8。
"""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()


def _build_engine():
    """按 DATABASE_URL 创建引擎。

    SQLite 需要关闭线程检查（FastAPI 多线程执行同步函数），
    MySQL 则启用连接池预检，避免长时间空闲后连接失效。
    """
    url = settings.database_url
    kwargs: dict = {"future": True, "pool_pre_ping": True}

    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        # 确保 SQLite 文件所在目录存在，否则首次启动会报 unable to open database file
        db_path = url.replace("sqlite:///", "", 1)
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    return create_engine(url, **kwargs)


engine = _build_engine()

# expire_on_commit=False：提交后仍可读取对象属性，便于直接返回给 Pydantic
SessionLocal = sessionmaker(
    bind=engine, autocommit=False, autoflush=False, expire_on_commit=False, class_=Session
)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供请求级数据库会话，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """创建所有数据表（开发期使用；生产建议改为迁移脚本）。"""
    from app import models  # noqa: F401  确保模型已注册到 metadata

    Base.metadata.create_all(bind=engine)
