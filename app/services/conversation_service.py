from sqlalchemy.orm import Session

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
        .filter(Conversation.session_id == session_id)
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