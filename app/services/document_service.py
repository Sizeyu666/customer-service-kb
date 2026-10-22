"""知识库文档服务：文件落盘、索引维护、删除三处一致性处理。"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Document
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)
settings = get_settings()

# 白名单扩展名与大小限制
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


class DocumentError(Exception):
    """文档操作异常，消息为可直接展示的中文提示。"""


def _safe_name(filename: str) -> str:
    """清洗文件名，去掉路径分隔符与非法字符，避免目录穿越。"""
    name = Path(filename).name
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name).strip()
    return name or "未命名文档"


def _ensure_upload_dir() -> Path:
    """确保上传目录存在。"""
    path = Path(settings.upload_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _find_stored_file(document_id: int) -> Path | None:
    """按「文档ID_原文件名」规则定位磁盘文件。"""
    upload_dir = _ensure_upload_dir()
    matches = sorted(upload_dir.glob(f"{document_id}_*"))
    return matches[0] if matches else None


async def save_and_index(db: Session, upload: UploadFile, user_id: int) -> Document:
    """保存上传文件并构建向量索引。

    :raises DocumentError: 扩展名不合法、文件为空或超出大小限制
    """
    original_name = upload.filename or ""
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise DocumentError(
            f"文件「{original_name or '未命名'}」类型不支持，仅允许 PDF、DOCX、TXT、MD。"
        )

    content = await upload.read()
    if not content:
        raise DocumentError(f"文件「{original_name}」内容为空，请重新选择。")
    if len(content) > MAX_FILE_SIZE:
        raise DocumentError(
            f"文件「{original_name}」超过 20MB 限制，请拆分后再上传。"
        )

    document = Document(
        filename=original_name,
        file_type=suffix.lstrip("."),
        status="processing",
        uploaded_by=user_id,
        chunk_count=0,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    target = _ensure_upload_dir() / f"{document.id}_{_safe_name(original_name)}"
    try:
        target.write_bytes(content)
    except OSError as exc:
        document.status = "failed"
        document.error_msg = f"文件保存失败：{exc}"
        db.commit()
        db.refresh(document)
        return document

    try:
        chunk_count = RagService.instance().add_document(document.id, original_name, target)
        document.status = "ready"
        document.chunk_count = chunk_count
        document.error_msg = None
    except Exception as exc:
        logger.exception("文档 %s 索引失败", document.id)
        document.status = "failed"
        document.error_msg = f"解析或索引失败：{exc}"
        # 失败不入库：清理磁盘文件，仅保留失败记录便于排查
        target.unlink(missing_ok=True)

    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document) -> dict:
    """删除文档：向量 → 磁盘文件 → 数据库记录，逐步执行并汇总失败原因。"""
    problems: list[str] = []

    try:
        RagService.instance().delete_document(document.id)
    except Exception as exc:
        logger.exception("删除文档 %s 向量失败", document.id)
        problems.append(f"向量删除失败：{exc}")

    try:
        stored = _find_stored_file(document.id)
        if stored is not None:
            stored.unlink(missing_ok=True)
    except OSError as exc:
        problems.append(f"文件删除失败：{exc}")

    db.delete(document)
    db.commit()

    return {"ok": not problems, "problems": problems}


def rebuild_all(db: Session) -> dict:
    """清空并全量重建索引，同时校正数据库中的块数与状态。"""
    result = RagService.instance().rebuild_all(settings.upload_dir)

    for item in result["items"]:
        document_id = item.get("document_id")
        if document_id is None:
            continue
        document = db.get(Document, document_id)
        if document is None:
            continue
        if item["error"] is None:
            document.status = "ready"
            document.chunk_count = item["chunk_count"]
            document.error_msg = None
        else:
            document.status = "failed"
            document.chunk_count = 0
            document.error_msg = f"重建失败：{item['error']}"
    db.commit()

    # 数据库中有记录但磁盘已无文件的，标记为失败，避免状态误导
    for document in db.query(Document).all():
        if _find_stored_file(document.id) is None and document.status != "failed":
            document.status = "failed"
            document.chunk_count = 0
            document.error_msg = "重建时未找到原始文件，请重新上传"
            db.commit()

    return result
