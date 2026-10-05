from sqlalchemy.orm import Session
from app.core.logger import logger
from app.models.conversation_model import Conversation


def save_message(
    db: Session,
    session_id: str,
    role: str,
    message: str
):
    """
    Save a user or assistant message.
    """

    logger.info(
        f"Conversation updated for session {session_id}"
    )

    conversation = Conversation(
        session_id=session_id,
        role=role,
        message=message
    )

    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_conversation_history(
    db: Session,
    session_id: str,
    limit: int = 10
):
    """
    Return only the last `limit` messages.
    """

    history = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )

    # Reverse so the oldest message comes first
    history.reverse()

    return history


def clear_conversation(
    db: Session,
    session_id: str
):
    """
    Delete all messages for a conversation.
    """

    db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).delete()

    db.commit()


def trim_history(
    db: Session,
    session_id: str,
    max_messages: int = 10
):
    """
    Keep only the latest max_messages for a session.
    """

    messages = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id
        )
        .order_by(Conversation.created_at.desc())
        .all()
    )

    if len(messages) <= max_messages:
        return

    for message in messages[max_messages:]:
        db.delete(message)

    db.commit()


def get_all_conversations(db: Session):
    """
    Get all unique chat sessions.

    Uses saved title if available.
    Otherwise uses the first user message as the title.
    Existing conversations are not modified.
    """

    conversations = (
        db.query(Conversation)
        .order_by(Conversation.created_at.asc())
        .all()
    )

    seen_sessions = set()
    result = []

    for conversation in conversations:

        session_id = conversation.session_id

        if session_id in seen_sessions:
            continue

        # Only create sidebar entry from user messages
        if conversation.role != "user":
            continue

        seen_sessions.add(session_id)

        title = (
            conversation.title
            if conversation.title
            else conversation.message[:50]
        )

        result.append({
            "session_id": session_id,
            "title": title,
            "created_at": conversation.created_at
        })

    # Newest conversations first
    result.reverse()

    return result


def rename_conversation(
    db: Session,
    session_id: str,
    title: str
):
    """
    Rename a conversation.
    Updates the title for all messages belonging
    to the same session.
    """

    conversations = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id
        )
        .all()
    )

    if not conversations:
        return None

    for conversation in conversations:
        conversation.title = title

    db.commit()

    return {
        "session_id": session_id,
        "title": title
    }

def delete_conversation(
    db: Session,
    session_id: str
):
    """
    Delete all messages belonging to a conversation.
    """

    deleted_count = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id
        )
        .delete(
            synchronize_session=False
        )
    )

    db.commit()

    return deleted_count