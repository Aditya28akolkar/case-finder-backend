from sqlalchemy.orm import Session

from app.services.hybrid_search_service import hybrid_search
from app.services.llm_service import generate_answer
from app.services.conversation_service import (
    save_message,
    get_conversation_history
)

from sqlalchemy.orm import Session

from app.services.hybrid_search_service import hybrid_search
from app.services.llm_service import generate_answer
from app.services.conversation_service import (
    save_message,
    get_conversation_history
)


def ask_question(
    db: Session,
    session_id: str,
    question: str
):

    # Load previous conversation
    history = get_conversation_history(
        db=db,
        session_id=session_id,
        limit=10
    )
    # Search relevant cases
    results = hybrid_search(
        db=db,
        query=question,
        top_k=5
    )

    if not results:
        return {
            "answer": "No relevant legal cases found.",
            "sources": []
        }

    # Build conversation history
    conversation = ""

    for msg in history:
        conversation += f"{msg.role}: {msg.message}\n"

    # Build legal context
    context = ""

    for result in results:

        context += f"""
Case Title: {result['title']}
Court: {result['court']}
Citation: {result['citation']}

Content:
{result['text']}

----------------------------------------
"""

    # Final prompt
    prompt = f"""
You are an AI Legal Assistant.

Use ONLY the legal context below.

Conversation History:

{conversation}

Legal Context:

{context}

Current Question:

{question}

Answer:
"""

    print("=" * 80)
    print("Conversation History")
    print(conversation)
    print("=" * 80)


    # Generate answer
    answer = generate_answer(prompt)

    # Save current conversation
    save_message(
        db,
        session_id,
        "user",
        question
    )

    save_message(
        db,
        session_id,
        "assistant",
        answer
    )

    return {
        "session_id": session_id,
        "answer": answer,
        "sources": results
    }