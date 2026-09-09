from sqlalchemy.orm import Session

from app.models.conversation_model import Conversation


def get_conversation_history(
    db: Session,
    session_id: str
):
    """
    Return all messages for a session.
    """

    conversations = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id
        )
        .order_by(Conversation.created_at.asc())
        .all()
    )

    return conversations


def delete_conversation_history(
    db: Session,
    session_id: str
):
    """
    Delete all messages for a session.
    """

    deleted = (
        db.query(Conversation)
        .filter(
            Conversation.session_id == session_id
        )
        .delete()
    )

    db.commit()

    return {
        "deleted_messages": deleted
    }