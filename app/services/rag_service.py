from sqlalchemy.orm import Session

from app.services.conversation_service import (
    save_message,
    get_conversation_history
)

from app.services.knowledge_search_service import search_knowledge
from app.services.llm_service import generate_answer
from app.services.query_understanding_service import QueryUnderstandingService
from app.services.knowledge_search_service import (
    debug_log,
    debug_separator,
    debug_chunk,
    debug_chunks,
    debug_find_chunk,
    debug_llm_context,
)

query_service = QueryUnderstandingService()


def get_previous_assistant_answer(history_messages) -> str:
    """
    Get the complete most recent assistant answer.

    We read directly from the conversation messages instead of
    parsing the formatted history string. This prevents
    multi-line answers from being truncated.
    """

    if not history_messages:
        return ""

    for message in reversed(history_messages):

        if message.role.lower() == "assistant":

            answer = message.message

            if answer and answer.strip():
                return answer.strip()

    return ""


def ask_question(
    db: Session,
    question: str,
    session_id: str,
    subject: str = None,
    top_k: int = 5
):


    debug_separator("NEW RETRIEVAL TRACE")

    debug_log(
        f"""
    QUESTION:
    {question}
    """
    )

    """
    Complete CA knowledge chatbot pipeline.

    User Question
        ↓
    Conversation History
        ↓
    Save User Message
        ↓
    Query Understanding
        ↓
    ┌───────────────────────────────┐
    │ New question                  │
    │ Follow-up question            │
    │ Format previous answer        │
    └───────────────────────────────┘
        ↓
    Knowledge Search
        ↓
    Context
        ↓
    LLM
        ↓
    Save Assistant Answer
        ↓
    Final Answer
    """

    # ==================================================
    # 1. GET PREVIOUS CONVERSATION
    # ==================================================

    history_messages = get_conversation_history(
        db=db,
        session_id=session_id,
        limit=3
    )

    history_parts = []

    for message in history_messages:

        history_parts.append(
            f"{message.role.upper()}: {message.message}"
        )

    history = "\n".join(history_parts)

    # ==================================================
    # 2. SAVE CURRENT USER MESSAGE
    # ==================================================

    save_message(
        db=db,
        session_id=session_id,
        role="user",
        message=question
    )

    # ==================================================
    # 3. UNDERSTAND USER REQUEST
    # ==================================================

    analysis = query_service.analyze_query(
        query=question,
        history=history
    )

    request_type = analysis.get(
        "request_type",
        "new_question"
    )

    expanded_query = analysis.get(
        "expanded_query",
        question
    )
    print("\n========== EXPANDED QUERY ==========")
    print(expanded_query)
    print("====================================\n")
    from pathlib import Path



    print("\n========== QUERY UNDERSTANDING ==========")

    print("ORIGINAL QUESTION:")
    print(question)

    print("\nREQUEST TYPE:")
    print(request_type)

    print("\nCONVERSATION HISTORY:")
    print(history)

    print("\nQUERY ANALYSIS:")
    print(analysis)

    print("\nEXPANDED QUERY:")
    print(expanded_query)

    print("==========================================")
    debug_file = Path("query_debug.txt")

    with debug_file.open("w", encoding="utf-8") as f:
        f.write("========== ORIGINAL QUESTION ==========\n")
        f.write(str(question))
        f.write("\n\n")

        f.write("========== CONVERSATION HISTORY ==========\n")
        f.write(str(history))
        f.write("\n\n")

        f.write("========== QUERY ANALYSIS ==========\n")
        f.write(str(analysis))
        f.write("\n\n")

        f.write("========== EXPANDED QUERY ==========\n")
        f.write(str(expanded_query))
        f.write("\n")
    # ==================================================
    # 4. FORMAT PREVIOUS ANSWER
    # ==================================================

    if request_type == "format_follow_up":

        previous_answer = get_previous_assistant_answer(
            history_messages
        )

        if previous_answer:

            format_instruction = analysis.get(
                "format_instruction",
                ""
            )

            if not format_instruction:
                format_instruction = (
                    "Rewrite the previous answer according "
                    "to the user's requested format."
                )

            print("\n========== FORMAT FOLLOW-UP ==========")

            print("FORMAT:")
            print(analysis.get("format"))

            print("POINT COUNT:")
            print(analysis.get("point_count"))

            print("WORD COUNT:")
            print(analysis.get("word_count"))

            print("FORMAT INSTRUCTION:")
            print(format_instruction)

            print("\nPREVIOUS ANSWER:")
            print(previous_answer)

            print("======================================")

            answer = generate_answer(
                context=previous_answer,
                question=format_instruction,
                history=""
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

        # --------------------------------------------------
        # If there is no previous answer, don't try to format
        # nothing. Continue as a normal question.
        # --------------------------------------------------

        print(
            "\nNo previous assistant answer found. "
            "Continuing as normal question."
        )

    # ==================================================
    # 5. SEARCH KNOWLEDGE
    # ==================================================
    print("========== FULL CHAT RETRIEVAL INPUT ==========")
    print("ORIGINAL QUESTION:", question)
    print("EXPANDED QUERY:", expanded_query)
    print("SUBJECT:", subject)


    with open("full_chat_debug.txt", "a", encoding="utf-8") as f:
        f.write("\n\n========== FULL CHAT RETRIEVAL ==========\n")
        f.write(f"ORIGINAL QUESTION: {question}\n")
        f.write(f"EXPANDED QUERY: {expanded_query}\n")
        f.write(f"SUBJECT: {subject}\n")




    documents = search_knowledge(
        db=db,
        question=expanded_query,
        query_analysis=analysis,
        subject=subject,
        top_k=top_k
    )

    with open("full_chat_debug.txt", "a", encoding="utf-8") as f:
        f.write("\n========== RETRIEVAL TEST ==========\n")
        f.write(f"QUESTION: {question}\n")
        f.write(f"EXPANDED: {expanded_query}\n")
        f.write(f"SUBJECT: {subject}\n")
        f.write(f"DOCUMENT COUNT: {len(documents) if documents else 0}\n")
        for i, doc in enumerate(documents[:10], 1):
            f.write(
                f"RESULT {i}: ID={doc.get('id')}, "
                f"SUBJECT={doc.get('subject')}, "
                f"PAGE={doc.get('page_number')}\n"
            )
    # ==================================================
    # 6. NO KNOWLEDGE FOUND
    # ==================================================


    if not documents:
        answer = (
            "I couldn't find sufficient information "
            "to answer this question."
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

    # ==================================================
    # 7. BUILD CONTEXT
    # ==================================================

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

    # Keep the complete retrieved context
    print("Total context characters:", len(context))

    with open("llm_context_debug.txt", "w", encoding="utf-8") as f:
        f.write(context)
    # ==================================================
    # 8. GENERATE ANSWER
    # ==================================================

    print("\n========== RETRIEVED DOCUMENTS ==========")

    for i, document in enumerate(documents, start=1):
        print(f"\nRANK: {i}")
        print(f"ID: {document.get('id')}")
        print(f"SUBJECT: {document.get('subject')}")
        print(f"MODULE: {document.get('module')}")
        print(f"CHAPTER: {document.get('chapter')}")
        print(f"PAGE: {document.get('page_number')}")
        print(f"SCORE: {document.get('score')}")
        print("CONTENT:")
        print(document.get('content'))
        print("------------------------------------------")

    print("### STEP A: ABOUT TO CALL LLM ###")

    answer = generate_answer(
        context=context,
        question=expanded_query,
        history=history
    )

    print("### STEP B: LLM CALL FINISHED ###")
    print("LLM ANSWER:", answer)
    # ==================================================
    # 9. SAVE ASSISTANT ANSWER
    # ==================================================

    save_message(
        db=db,
        session_id=session_id,
        role="assistant",
        message=answer
    )

    # ==================================================
    # 10. RETURN ANSWER
    # ==================================================

    return {
        "answer": answer,
        "sources": sources
    }