from sqlalchemy.orm import Session

from app.services.conversation_service import (
    save_message,
    get_conversation_history
)

from app.services.knowledge_search_service import search_knowledge
from app.services.llm_service import generate_answer
from app.services.query_understanding_service import QueryUnderstandingService


query_service = QueryUnderstandingService()


def ask_question(
    db: Session,
    question: str,
    session_id: str,
    subject: str = None,
    top_k: int = 3
):
    """
    Complete RAG pipeline:

    User Question
        ↓
    Conversation History
        ↓
    Save User Message
        ↓
    Query Understanding
        ↓
    Expanded Query
        ↓
    Semantic Search + BM25
        ↓
    CrossEncoder
        ↓
    Top Chunks
        ↓
    Context Builder
        ↓
    LLM + Conversation History
        ↓
    Save Assistant Message
        ↓
    Final Answer
    """

    # -----------------------------------------
    # 1. Get previous conversation history
    # -----------------------------------------

    history_messages = get_conversation_history(
        db=db,
        session_id=session_id,
        limit=6
    )

    history_parts = []

    for message in history_messages:
        history_parts.append(
            f"{message.role.upper()}: {message.message}"
        )

    history = "\n".join(history_parts)

    # -----------------------------------------
    # 2. Save current user message
    # -----------------------------------------

    save_message(
        db=db,
        session_id=session_id,
        role="user",
        message=question
    )

    # -----------------------------------------
    # 3. Query Understanding
    # -----------------------------------------

    analysis = query_service.analyze_query(
        query=question,
        history=history
    )

    expanded_query = analysis.get(
        "expanded_query",
        question
    )

    print("\n========== QUERY UNDERSTANDING ==========")

    print("ORIGINAL QUESTION:")
    print(question)

    print("\nCONVERSATION HISTORY:")
    print(history)

    print("\nQUERY ANALYSIS:")
    print(analysis)

    print("\nEXPANDED QUERY:")
    print(expanded_query)

    print("==========================================")

    # -----------------------------------------
    # 4. Search relevant knowledge
    # -----------------------------------------

    documents = search_knowledge(
        db=db,
        question=expanded_query,
        query_analysis=analysis,
        top_k=top_k
    )
    # -----------------------------------------
    # 5. If nothing is found
    # -----------------------------------------

    if not documents:

        answer = (
            "I couldn't find sufficient information "
            "in the available ICAI study material."
        )

        save_message(
            db=db,
            session_id=session_id,
            role="assistant",
            message=answer
        )

        return {
            "answer": answer,
            "sources": []
        }

    # -----------------------------------------
    # 6. Build clean structured context
    # -----------------------------------------

    context_parts = []
    sources = []

    for i, document in enumerate(
        documents,
        start=1
    ):

        context_parts.append(
            f"""
SOURCE {i}
====================

SOURCE INFORMATION:
Subject: {document["subject"]}
Module: {document["module"]}
Chapter: {document["chapter"]}
Page: {document["page_number"]}

CONTENT:
{document["content"]}

END SOURCE {i}
====================
"""
        )

        source = {
            "subject": document["subject"],
            "module": document["module"],
            "chapter": document["chapter"],
            "page": document["page_number"]
        }

        if source not in sources:
            sources.append(source)

    context = "\n".join(context_parts)

    # -----------------------------------------
    # 7. Generate answer using history
    # -----------------------------------------

    print("\n========== RAG CONTEXT ==========")
    print(context)
    print("=================================")

    answer = generate_answer(
        context=context,
        question=question,
        history=history
    )

    # -----------------------------------------
    # 8. Save assistant message
    # -----------------------------------------

    save_message(
        db=db,
        session_id=session_id,
        role="assistant",
        message=answer
    )

    # -----------------------------------------
    # 9. Return answer + sources
    # -----------------------------------------

    return {
        "answer": answer,
        "sources": sources
    }