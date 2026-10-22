"""会话与问答接口（均需登录，且只能操作本人数据）。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Conversation, Feedback, Message, User
from app.schemas import (
    ApiResponse,
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationOut,
    FeedbackRequest,
    MessageOut,
)
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["会话与问答"])

HISTORY_ROUNDS = 6  # 多轮改写时携带的历史轮数
DEFAULT_TITLE = "新会话"


def _get_own_conversation(db: Session, conversation_id: int, user: User) -> Conversation:
    """获取本人会话；不存在返回 404，越权返回 403。"""
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在或已被删除")
    if conversation.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问他人的会话")
    return conversation


def _parse_sources(raw: str | None) -> list[str]:
    """把数据库中的 JSON 字符串还原为文件名列表。"""
    if not raw:
        return []
    try:
        value = json.loads(raw)
        return [str(item) for item in value] if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _serialize_message(message: Message, feedback: str | None = None) -> MessageOut:
    """把 ORM 消息转换为响应模型。"""
    return MessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        sources=_parse_sources(message.sources),
        feedback=feedback,
        created_at=message.created_at,
    )


@router.get(
    "/conversations",
    response_model=ApiResponse[list[ConversationOut]],
    summary="获取我的会话列表",
    description="返回当前登录用户的全部会话，按创建时间倒序，附带消息条数。",
)
def list_conversations(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> ApiResponse[list[ConversationOut]]:
    """列出本人会话。"""
    rows = db.execute(
        select(Conversation, func.count(Message.id))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id)
        .group_by(Conversation.id)
        .order_by(Conversation.id.desc())
    ).all()

    data = [
        ConversationOut(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            message_count=count,
        )
        for conversation, count in rows
    ]
    return ApiResponse[list[ConversationOut]](data=data)


@router.post(
    "/conversations",
    response_model=ApiResponse[ConversationOut],
    summary="新建会话",
    description="为当前用户创建一个新会话，未传标题时默认「新会话」。",
)
def create_conversation(
    payload: ConversationCreateRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ConversationOut]:
    """新建会话。"""
    title = (payload.title if payload and payload.title else "").strip() or DEFAULT_TITLE
    conversation = Conversation(user_id=current_user.id, title=title[:120])
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return ApiResponse[ConversationOut](
        message="会话创建成功",
        data=ConversationOut(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            message_count=0,
        ),
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ApiResponse[list[MessageOut]],
    summary="获取会话消息",
    description="返回指定会话的全部消息；仅限本人会话，越权访问返回 403。",
)
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[MessageOut]]:
    """列出会话消息。"""
    conversation = _get_own_conversation(db, conversation_id, current_user)
    messages = list(
        db.scalars(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.id)
        )
    )

    # 一次性取出反馈，避免逐条查询
    feedback_map: dict[int, str] = {}
    if messages:
        rows = db.execute(
            select(Feedback.message_id, Feedback.rating).where(
                Feedback.message_id.in_([m.id for m in messages])
            )
        ).all()
        feedback_map = {message_id: rating for message_id, rating in rows}

    return ApiResponse[list[MessageOut]](
        data=[_serialize_message(m, feedback_map.get(m.id)) for m in messages]
    )


@router.delete(
    "/conversations/{conversation_id}",
    response_model=ApiResponse[dict],
    summary="删除会话",
    description="删除本人会话，并级联删除该会话下的全部消息与反馈。",
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """删除会话。"""
    conversation = _get_own_conversation(db, conversation_id, current_user)
    db.delete(conversation)
    db.commit()
    return ApiResponse[dict](message="会话已删除", data={"id": conversation_id})


@router.post(
    "/conversations/{conversation_id}/chat",
    response_model=ApiResponse[ChatResponse],
    summary="智能客服问答",
    description=(
        "提交问题并获取基于知识库的回答。支持多轮指代改写，回答附参考来源；"
        "知识库无相关内容时返回固定话术，避免编造。"
    ),
)
def chat(
    conversation_id: int,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[ChatResponse]:
    """保存提问并生成回答。"""
    conversation = _get_own_conversation(db, conversation_id, current_user)
    question = payload.question.strip()

    # 先取历史（不含本次提问），最近 6 轮
    history_rows = list(
        db.scalars(
            select(Message)
            .where(Message.conversation_id == conversation.id)
            .order_by(Message.id.desc())
            .limit(HISTORY_ROUNDS * 2)
        )
    )
    history_rows.reverse()
    history = [{"role": m.role, "content": m.content} for m in history_rows]

    user_message = Message(conversation_id=conversation.id, role="user", content=question)
    db.add(user_message)

    # 首条消息自动生成标题
    if not history and conversation.title == DEFAULT_TITLE:
        conversation.title = question[:15] or DEFAULT_TITLE

    db.commit()
    db.refresh(user_message)
    db.refresh(conversation)

    try:
        result = RagService.instance().ask(question, history)
    except Exception as exc:
        logger.exception("问答失败，会话 %s", conversation.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"智能客服回答失败：{exc}",
        ) from exc

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=result["answer"],
        sources=json.dumps(result.get("sources") or [], ensure_ascii=False),
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)

    return ApiResponse[ChatResponse](
        data=ChatResponse(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            title=conversation.title,
            answer=assistant_message.content,
            sources=result.get("sources") or [],
        )
    )


@router.post(
    "/messages/{message_id}/feedback",
    response_model=ApiResponse[dict],
    summary="回答点赞/点踩",
    description="对助手回答提交 up 或 down 评价，重复提交会更新为最新评价。",
)
def submit_feedback(
    message_id: int,
    payload: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[dict]:
    """提交或更新反馈。"""
    message = db.get(Message, message_id)
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    conversation = db.get(Conversation, message.conversation_id)
    if conversation is None or conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权评价他人的消息")
    if message.role != "assistant":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持对客服回答评价")

    feedback = db.scalar(select(Feedback).where(Feedback.message_id == message_id))
    if feedback is None:
        db.add(Feedback(message_id=message_id, rating=payload.rating))
    else:
        feedback.rating = payload.rating
    db.commit()

    return ApiResponse[dict](
        message="感谢您的反馈", data={"message_id": message_id, "rating": payload.rating}
    )
