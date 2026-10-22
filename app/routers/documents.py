"""知识库文档管理接口（仅管理员）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models import Document, User
from app.schemas import (
    ApiResponse,
    DocumentOut,
    RebuildResult,
    UploadResult,
)
from app.services import document_service
from app.services.document_service import DocumentError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/documents", tags=["知识库管理"])


@router.post(
    "",
    response_model=ApiResponse[UploadResult],
    summary="上传文档并建立索引",
    description=(
        "支持多文件上传 PDF/DOCX/TXT/MD，单文件不超过 20MB。"
        "上传后自动解析、切分并写入向量库，返回每个文件的处理结果；失败文件不入库并给出中文原因。"
    ),
)
async def upload_documents(
    files: list[UploadFile] = File(..., description="待上传的文档，可多选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> ApiResponse[UploadResult]:
    """批量上传并索引文档。"""
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请至少选择一个文件")

    success: list[DocumentOut] = []
    failed: list[dict] = []
    for upload in files:
        name = upload.filename or "未命名文档"
        try:
            document = await document_service.save_and_index(db, upload, current_user.id)
        except DocumentError as exc:
            failed.append({"filename": name, "reason": str(exc)})
            continue
        except Exception as exc:  # 未预期异常也不打断其余文件
            logger.exception("上传文档 %s 失败", name)
            failed.append({"filename": name, "reason": f"服务器处理失败：{exc}"})
            continue

        if document.status == "ready":
            success.append(DocumentOut.model_validate(document))
        else:
            failed.append({"filename": name, "reason": document.error_msg or "索引失败"})

    message = f"上传完成：成功 {len(success)} 个，失败 {len(failed)} 个"
    return ApiResponse[UploadResult](
        message=message,
        data=UploadResult(success=success, failed=failed, message=message),
    )


@router.get(
    "",
    response_model=ApiResponse[list[DocumentOut]],
    summary="获取文档列表",
    description="返回知识库全部文档，含类型、状态、文本块数与上传时间。",
)
def list_documents(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> ApiResponse[list[DocumentOut]]:
    """文档列表。"""
    documents = list(db.scalars(select(Document).order_by(Document.id.desc())))
    return ApiResponse[list[DocumentOut]](
        data=[DocumentOut.model_validate(item) for item in documents]
    )


@router.delete(
    "/{document_id}",
    response_model=ApiResponse[dict],
    summary="删除文档",
    description="删除文档记录、磁盘原始文件以及向量库中该文档的全部向量。",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> ApiResponse[dict]:
    """删除文档。"""
    document = db.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在或已被删除")

    result = document_service.delete_document(db, document)
    if not result["ok"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文档已从列表移除，但存在未完成操作：" + "；".join(result["problems"]),
        )
    return ApiResponse[dict](message="文档已删除", data={"id": document_id})


@router.post(
    "/rebuild",
    response_model=ApiResponse[RebuildResult],
    summary="全部重建索引",
    description="清空向量库后按 uploads 目录中的原始文件重新构建索引，过程为同步执行。",
)
def rebuild(
    db: Session = Depends(get_db), _: User = Depends(require_admin)
) -> ApiResponse[RebuildResult]:
    """全量重建索引。"""
    result = document_service.rebuild_all(db)
    message = f"重建完成：共 {result['total']} 个文档，成功 {result['success']} 个，失败 {result['failed']} 个"
    return ApiResponse[RebuildResult](
        message=message,
        data=RebuildResult(
            total=result["total"],
            success=result["success"],
            failed=result["failed"],
            message=message,
        ),
    )
