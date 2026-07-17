from sqlalchemy.orm import Session

from app.models.search_session_model import SearchSession


def save_search_results(
    db: Session,
    session_id: str,
    case_ids: list[int]
):
    """
    Save the retrieved case IDs for a search session.
    Any previous search results for this session are replaced.
    """

    # Remove old search results
    db.query(SearchSession).filter(
        SearchSession.session_id == session_id
    ).delete()

    # Save new search results
    for rank, case_id in enumerate(case_ids, start=1):

        search_session = SearchSession(
            session_id=session_id,
            case_id=case_id,
            rank=rank
        )

        db.add(search_session)

    db.commit()


def get_search_results(
    db: Session,
    session_id: str
):
    """
    Return the case IDs stored for a search session
    in their original search order.
    """

    results = (
        db.query(SearchSession)
        .filter(
            SearchSession.session_id == session_id
        )
        .order_by(SearchSession.rank)
        .all()
    )

    return [result.case_id for result in results]


def clear_search_session(
    db: Session,
    session_id: str
):
    """
    Delete all stored search results for a session.
    """

    db.query(SearchSession).filter(
        SearchSession.session_id == session_id
    ).delete()

    db.commit()