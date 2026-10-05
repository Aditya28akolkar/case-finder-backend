from app.services.legal_context_filter import filter_retrieved_chunks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.services.legal_retrieval_service import (
    retrieve_by_legal_concept,
    retrieve_legal_consequences,
    merge_legal_candidates,
)
from app.services.rerank_service import rerank
from app.models.knowledge_document_model import KnowledgeDocument
from app.embeddings.embedding_service import generate_embedding
from pathlib import Path
from datetime import datetime
import json

# ============================================================
# RETRIEVAL DEBUG LOGGING
# ============================================================
DEBUG_LOG_FILE = Path("retrieval_debug.log")


def debug_log(message):
    """
    Writes debugging information to retrieval_debug.log
    so terminal output is not required.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{timestamp}] {message}\n")


def debug_separator(title):
    with open(DEBUG_LOG_FILE, "a", encoding="utf-8") as f:
        f.write("\n")
        f.write("=" * 90 + "\n")
        f.write(f"{title}\n")
        f.write("=" * 90 + "\n")


def debug_chunk(stage, rank, chunk):
    """
    Safely logs the important information from a chunk/result.
    Works with dictionaries or objects.
    """
    def get_value(obj, *names):
        for name in names:
            if isinstance(obj, dict):
                if name in obj:
                    return obj[name]
            if hasattr(obj, name):
                return getattr(obj, name)
        return None

    chunk_id = get_value(
        chunk,
        "id",
        "chunk_id",
        "document_id"
    )
    page = get_value(
        chunk,
        "page",
        "page_number"
    )
    retrieval_score = get_value(
        chunk,
        "retrieval_score",
        "similarity",
        "score"
    )
    reranker_score = get_value(
        chunk,
        "reranker_score",
        "rerank_score",
        "cross_encoder_score"
    )
    content = get_value(
        chunk,
        "content",
        "text",
        "page_content"
    )
    debug_log(
        f"""
STAGE: {stage}
RANK: {rank}
CHUNK ID: {chunk_id}
PAGE: {page}
RETRIEVAL SCORE: {retrieval_score}
RERANKER SCORE: {reranker_score}
CONTENT PREVIEW:
{str(content)[:1000]}
"""
    )


def debug_chunks(stage, chunks):
    """
    Logs an entire candidate list.
    """
    debug_separator(
        f"{stage} | TOTAL CHUNKS: {len(chunks) if chunks else 0}"
    )
    if not chunks:
        debug_log("NO CHUNKS FOUND")
        return
    for rank, chunk in enumerate(chunks, start=1):
        debug_chunk(stage, rank, chunk)


def debug_find_chunk(chunks, target_id=10596, stage="UNKNOWN"):
    """
    Specifically searches for chunk 10596.
    """
    debug_separator(
        f"TRACE CHUNK {target_id} | STAGE: {stage}"
    )
    found = False
    if not chunks:
        debug_log("Candidate list is EMPTY")
        return
    for rank, chunk in enumerate(chunks, start=1):
        if isinstance(chunk, dict):
            chunk_id = (
                chunk.get("id")
                or chunk.get("chunk_id")
                or chunk.get("document_id")
            )
        else:
            chunk_id = (
                getattr(chunk, "id", None)
                or getattr(chunk, "chunk_id", None)
                or getattr(chunk, "document_id", None)
            )
        if str(chunk_id) == str(target_id):
            found = True
            debug_log(
                f"""
TARGET CHUNK FOUND
Stage       : {stage}
Rank        : {rank}
Chunk ID    : {chunk_id}
Retrieval   : {getattr(chunk, 'retrieval_score', None) if not isinstance(chunk, dict) else chunk.get('retrieval_score')}
Reranker    : {getattr(chunk, 'reranker_score', None) if not isinstance(chunk, dict) else chunk.get('reranker_score')}
FULL OBJECT:
{chunk}
"""
            )
            break
    if not found:
        debug_log(
            f"TARGET CHUNK {target_id} WAS NOT FOUND AT THIS STAGE"
        )


def debug_target_score(results, target_id=10596, stage="UNKNOWN"):
    debug_separator(
        f"TARGET SCORE TRACE | ID {target_id} | {stage}"
    )
    if not results:
        debug_log("RESULT LIST IS EMPTY")
        return
    for rank, result in enumerate(results, start=1):
        if isinstance(result, dict):
            chunk_id = result.get("id")
            rerank_score = result.get("rerank_score")
            term_bonus = result.get("term_bonus")
            final_score = result.get("final_score")
        else:
            chunk_id = getattr(result, "id", None)
            rerank_score = getattr(result, "rerank_score", None)
            term_bonus = getattr(result, "term_bonus", None)
            final_score = getattr(result, "final_score", None)
        if str(chunk_id) == str(target_id):
            debug_log(
                f"""
TARGET FOUND
STAGE       : {stage}
RANK        : {rank}
ID          : {chunk_id}
RERANK      : {rerank_score}
TERM BONUS  : {term_bonus}
FINAL SCORE : {final_score}
"""
            )
            return
    debug_log(
        f"TARGET {target_id} NOT FOUND AT THIS STAGE"
    )


def debug_target_presence(results, target_id=10596, stage="UNKNOWN"):
    debug_separator(
        f"TARGET PRESENCE | ID {target_id} | {stage}"
    )
    if not results:
        debug_log("RESULT LIST IS EMPTY")
        return
    for rank, result in enumerate(results, start=1):
        if isinstance(result, dict):
            result_id = result.get("id")
        else:
            result_id = getattr(result, "id", None)
        if str(result_id) == str(target_id):
            debug_log(
                f"""
TARGET FOUND
STAGE       : {stage}
POSITION    : {rank}
ID          : {result_id}
"""
            )
            return
    debug_log(
        f"TARGET {target_id} NOT FOUND"
    )


def debug_llm_context(context):
    """
    Logs the exact context that is about to be sent to the LLM.
    """
    debug_separator("FINAL LLM CONTEXT")
    debug_log(
        f"CONTEXT TYPE: {type(context)}"
    )
    debug_log(
        f"CONTEXT LENGTH: {len(str(context))}"
    )
    debug_log(
        "\nACTUAL CONTEXT:\n"
        + str(context)
    )


PROBE_TERMS = [
    "section 173",
    "board meeting",
    "meeting of the board",
    "notice of board",
    "every director",
    "seven days",
    "notice to directors",
]


def probe(stage, items):
    lines = []
    lines.append(f"\n[PROBE] {stage}: {len(items)} items")
    found = False
    for pos, item in enumerate(items, start=1):
        if isinstance(item, dict):
            text = str(item.get("content", "")).lower()
            item_id = item.get("id", "N/A")
            page = item.get("page_number", "N/A")
        else:
            text = str(item.content).lower()
            item_id = item.id
            page = getattr(item, "page_number", "N/A")
        hits = [term for term in PROBE_TERMS if term in text]
        if hits:
            found = True
            lines.append(
                f"HIT pos={pos} id={item_id} page={page} hits={hits}"
            )
    if not found:
        lines.append("NO HITS")
    output = "\n".join(lines)
    print(output)
    with open("probe_output.txt", "a", encoding="utf-8") as f:
        f.write(output + "\n")


# ============================================================
# EXACT LEGAL TERM BOOST
# ============================================================
def calculate_legal_term_bonus(
    question: str,
    document_text: str
) -> float:
    import re
    question_lower = question.lower()
    document_lower = document_text.lower()
    bonus = 0.0
    # Exact section number mentioned in the question
    detected_sections = re.findall(
        r"\bsections?\s+(\d+[A-Za-z]?)",
        question,
        flags=re.IGNORECASE
    )
    for section_number in detected_sections:
        # Strong match only when the document has an explicit
        # section heading/reference, not just any occurrence.
        section_patterns = [
            rf"\[\s*section\s+{re.escape(section_number)}\s*\]",
            rf"\bsection\s+{re.escape(section_number)}\s*[\]\):\-]",
            rf"\bsection\s+{re.escape(section_number)}\s*\(",
        ]
        if any(
            re.search(pattern, document_lower, flags=re.IGNORECASE)
            for pattern in section_patterns
        ):
            bonus += 10.0
    # Existing legal term matching
    important_terms = [
        "board meeting",
        "section 173",
        "notice of board",
        "seven days",
        "directors"
    ]
    for term in important_terms:
        if term in question_lower and term in document_lower:
            bonus += 2.0
    return bonus


# ============================================================
# SEARCH KNOWLEDGE
# ============================================================
def search_knowledge(
    db: Session,
    question: str,
    query_analysis: dict = None,
    subject: str = None,
    top_k: int = 8
):
    print("\n========================================")
    print("KNOWLEDGE SEARCH")
    print("========================================")
    print("QUESTION:", question)
    section = None
    topic = None
    expanded_query = ""
    # ========================================================
    # SCENARIO-AWARE RETRIEVAL
    # ========================================================
    is_scenario = False
    legal_issue = ""
    legal_retrieval_query = ""
    retrieval_query = question
    if query_analysis:
        section = query_analysis.get("section")
        topic = query_analysis.get("topic")
        is_scenario = bool(
            query_analysis.get("is_scenario", False)
        )
        legal_issue = (
            query_analysis.get("legal_issue") or ""
        ).strip()
        legal_retrieval_query = (
            query_analysis.get("legal_retrieval_query") or ""
        ).strip()
        expanded_query = (
            query_analysis.get("expanded_query")
            or question
        )
    # --------------------------------------------------------
    # Choose query used for retrieval
    # --------------------------------------------------------
    if is_scenario and legal_retrieval_query:
        retrieval_query = legal_retrieval_query
    else:
        retrieval_query = expanded_query or question
    print("\n========== RETRIEVAL MODE ==========")
    print("IS SCENARIO:", is_scenario)
    print("LEGAL ISSUE:", legal_issue)
    print("LEGAL RETRIEVAL QUERY:", legal_retrieval_query)
    print("RETRIEVAL QUERY:", retrieval_query)
    print("====================================")
    
    print("SECTION:", section)
    print("TOPIC:", topic)
    print("EXPANDED QUERY:", expanded_query)
    # ============================================================
    # 1. GENERATE QUESTION EMBEDDING
    # ============================================================
    question_embedding = generate_embedding(retrieval_query)
    if not question_embedding:
        print("WARNING: Failed to generate question embedding")
    # ============================================================
    # 2. SEMANTIC SEARCH
    # ============================================================
    semantic_documents = []
    try:
        semantic_query = db.query(KnowledgeDocument).filter(
            KnowledgeDocument.embedding.isnot(None)
        )
        if subject:
            semantic_query = semantic_query.filter(
                KnowledgeDocument.subject == subject
            )
        semantic_documents = (
            semantic_query
            .order_by(
                KnowledgeDocument.embedding.cosine_distance(
                    question_embedding
                )
            )
            .limit(30)
            .all()
        )
        print(
            f"\nSEMANTIC SEARCH: {len(semantic_documents)} documents"
        )
        probe(
            "SEMANTIC",
            semantic_documents
        )
    except Exception as e:
        print("SEMANTIC SEARCH ERROR:", str(e))
    # ============================================================
    # 3. KEYWORD SEARCH
    # ============================================================
    print("\n========================================")
    print("KEYWORD SEARCH")
    print("========================================")
    keyword_documents = []
    try:
        import re
        keyword_filters = []
        # --------------------------------------------------------
        # 3A. GET KEYWORDS FROM QUERY UNDERSTANDING
        # --------------------------------------------------------
        if query_analysis:
            query_keywords = query_analysis.get(
                "keywords",
                []
            )
            print(
                "QUERY UNDERSTANDING KEYWORDS:",
                query_keywords
            )
            for keyword in query_keywords:
                if not keyword:
                    continue
                keyword = str(keyword).strip()
                if len(keyword) >= 2:
                    keyword_filters.append(
                        KnowledgeDocument.content.ilike(
                            f"%{keyword}%"
                        )
                    )
        # --------------------------------------------------------
        # 3A-S. SCENARIO LEGAL TERMS
        # --------------------------------------------------------
        if is_scenario and legal_retrieval_query:
            print(
                "SCENARIO LEGAL RETRIEVAL TERMS:",
                legal_retrieval_query
            )
            # Search the complete legal retrieval query
            keyword_filters.append(
                KnowledgeDocument.content.ilike(
                    f"%{legal_retrieval_query}%"
                )
            )
            # Also search individual legal terms
            retrieval_words = re.findall(
                r"\b[A-Za-z][A-Za-z\-]{2,}\b",
                legal_retrieval_query
            )
            scenario_stop_words = {
                "the",
                "and",
                "with",
                "for",
                "before",
                "after",
                "whether",
                "within",
                "required",
                "minimum",
            }
            for word in retrieval_words:
                if word.lower() in scenario_stop_words:
                    continue
                keyword_filters.append(
                    KnowledgeDocument.content.ilike(
                        f"%{word}%"
                    )
                )
        # --------------------------------------------------------
        # 3B. SEARCH EXPANDED QUERY
        # --------------------------------------------------------
        if expanded_query:
            expanded_terms = re.findall(
                r"[A-Za-z0-9]+(?:\s+[A-Za-z0-9]+){0,5}",
                expanded_query
            )
            for term in expanded_terms:
                term = term.strip()
                if len(term) >= 4:
                    keyword_filters.append(
                        KnowledgeDocument.content.ilike(
                            f"%{term}%"
                        )
                    )
        # --------------------------------------------------------
        # 3C. SECTION NUMBER
        # --------------------------------------------------------
        section_numbers = re.findall(
            r"(?:section|sec\.?)\s*(\d+[A-Za-z]?)",
            question,
            flags=re.IGNORECASE
        )
        for section_number in section_numbers:
            keyword_filters.append(
                KnowledgeDocument.content.ilike(
                    f"%{section_number}%"
                )
            )
        # --------------------------------------------------------
        # 3D. IMPORTANT LEGAL PHRASES
        # --------------------------------------------------------
        legal_phrases = [
            # RHP / Prospectus
            "red herring prospectus",
            "opening of the subscription list",
            "subscription list",
            "filing of red herring prospectus",
            "red herring",
            "RHP",
            "prospectus",
            "public offer",
            "issue of securities",
            # Corporate law
            "board meeting",
            "notice of board meeting",
            "seven days",
            "general meeting",
            "registered office",
            "annual return",
            "financial statements",
            "auditor",
            "private placement",
            "related party transaction",
            # General legal terms
            "registrar",
            "company",
            "securities",
            "shareholders",
            "directors"
        ]
        for phrase in legal_phrases:
            if phrase.lower() in question.lower():
                keyword_filters.append(
                    KnowledgeDocument.content.ilike(
                        f"%{phrase}%"
                    )
                )
        # --------------------------------------------------------
        # 3E. RHP-SPECIFIC TERMS
        #
        # IMPORTANT:
        # Search these independently.
        # Do NOT search only:
        # "RHP subscription list"
        # --------------------------------------------------------
        rhp_terms = [
            "red herring prospectus",
            "opening of the subscription list",
            "subscription list",
            "filing of red herring prospectus",
            "red herring",
            "RHP",
            "prospectus",
            "public offer",
            "issue of securities"
        ]
        if (
            "rhp" in question.lower()
            or "red herring" in question.lower()
            or "prospectus" in question.lower()
            or "subscription list" in question.lower()
        ):
            print(
                "\nRHP QUERY DETECTED"
            )
            for term in rhp_terms:
                keyword_filters.append(
                    KnowledgeDocument.content.ilike(
                        f"%{term}%"
                    )
                )
        # --------------------------------------------------------
        # 3F. FALLBACK QUESTION TERMS
        # --------------------------------------------------------
        if not keyword_filters:
            words = re.findall(
                r"\b[A-Za-z]{3,}\b",
                question
            )
            stop_words = {
                "what",
                "when",
                "where",
                "which",
                "who",
                "how",
                "why",
                "does",
                "this",
                "that",
                "from",
                "with",
                "before",
                "after",
                "minimum",
                "period"
            }
            for word in words:
                if word.lower() in stop_words:
                    continue
                keyword_filters.append(
                    KnowledgeDocument.content.ilike(
                        f"%{word}%"
                    )
                )
        # --------------------------------------------------------
        # 3G. REMOVE DUPLICATE FILTERS
        # --------------------------------------------------------
        unique_filters = []
        seen_filter_strings = set()
        for filter_condition in keyword_filters:
            filter_string = str(filter_condition)
            if filter_string not in seen_filter_strings:
                seen_filter_strings.add(
                    filter_string
                )
                unique_filters.append(
                    filter_condition
                )
        keyword_filters = unique_filters
        print(
            "TOTAL KEYWORD FILTERS:",
            len(keyword_filters)
        )
        # --------------------------------------------------------
        # 3H. EXECUTE KEYWORD SEARCH
        # --------------------------------------------------------
        if keyword_filters:
            keyword_query = (
                db.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.embedding.isnot(None)
                )
                .filter(
                    or_(*keyword_filters)
                )
            )
            if subject:
                keyword_query = keyword_query.filter(
                    KnowledgeDocument.subject == subject
                )
            keyword_documents = (
                keyword_query
                .order_by(
                    KnowledgeDocument.embedding.cosine_distance(
                        question_embedding
                    )
                )
                .limit(50)
                .all()
            )
        print(
            f"KEYWORD SEARCH RESULTS: "
            f"{len(keyword_documents)}"
        )
        # --------------------------------------------------------
        # 3I. CHECK TARGET DOCUMENT
        # --------------------------------------------------------
        debug_target_presence(
            keyword_documents,
            target_id=10596,
            stage="KEYWORD SEARCH"
        )
        # --------------------------------------------------------
        # 3J. RHP DEBUG
        # --------------------------------------------------------
        for document in keyword_documents:
            content_lower = (
                document.content or ""
            ).lower()
            matched_rhp_terms = [
                term
                for term in rhp_terms
                if term.lower() in content_lower
            ]
            if matched_rhp_terms:
                print(
                    "\nRHP KEYWORD MATCH"
                )
                print(
                    "ID:",
                    document.id
                )
                print(
                    "MATCHED TERMS:",
                    matched_rhp_terms
                )
                print(
                    "SUBJECT:",
                    document.subject
                )
                print(
                    "CHAPTER:",
                    document.chapter
                )
                print(
                    "PAGE:",
                    document.page_number
                )
    except Exception as e:
        print(
            "KEYWORD SEARCH ERROR:",
            str(e)
        )
    # ============================================================
    # 4. COMBINE SEMANTIC + KEYWORD RESULTS
    # ============================================================
    combined_documents = {}
    for document in semantic_documents:
        if document.id not in combined_documents:
            combined_documents[
                document.id
            ] = document
    for document in keyword_documents:
        if document.id not in combined_documents:
            combined_documents[
                document.id
            ] = document
    print(
        "\nCOMBINED RESULTS:",
        len(combined_documents)
    )
    # ============================================================
    # 5. LEGAL CONCEPT RETRIEVAL
    # ============================================================

    try:
        legal_documents = retrieve_by_legal_concept(
            db=db,
            question=retrieval_query,
            topic=topic,
            expanded_query=retrieval_query,
            subject=subject,
            limit=30,
        )

        print(
            "\nLEGAL CONCEPT RESULTS:",
            len(legal_documents),
        )

        debug_target_presence(
            legal_documents,
            target_id=10596,
            stage="LEGAL CONCEPT SEARCH",
        )

        # merge_legal_candidates expects a list of documents,
        # not a dictionary of documents.
        combined_list = merge_legal_candidates(
            list(combined_documents.values()),
            legal_documents,
        )

        combined_documents = {
            document.id: document
            for document in combined_list
        }

    except Exception as e:
        print(
            "\nLEGAL CONCEPT RETRIEVAL ERROR:",
            str(e),
        )

    # ============================================================
    # 5B. LEGAL CONSEQUENCE RETRIEVAL
    # ============================================================

    consequence_query_text = " ".join(
        [
            question or "",
            retrieval_query or "",
            legal_issue or "",
        ]
    ).lower()

    consequence_intent_terms = [
        "consequence",
        "consequences",
        "penalty",
        "penalties",
        "liable",
        "liability",
        "punishment",
        "punishable",
        "fine",
        "contravention",
        "non-compliance",
        "non compliance",
        "failure to comply",
        "legal effect",
        "what happens",
        "did .* comply",
    ]

    import re

    asks_for_consequence = any(
        re.search(term, consequence_query_text)
        for term in consequence_intent_terms
    )

    if asks_for_consequence:
        debug_log(">>> STEP 5 BRANCH ENTERED: Consequence retrieval triggered")
        print("\n>>> STEP 5 BRANCH ENTERED <<<", flush=True)
        try:

            print("\n>>> STEP 5: ABOUT TO CALL LEGAL CONSEQUENCE RETRIEVAL <<<")
            debug_log(">>> STEP 5: Calling retrieve_legal_consequences")
            consequence_documents = retrieve_legal_consequences(
                db=db,
                question=question,
                topic=topic,
                expanded_query=retrieval_query,
                subject=subject,
                limit=10,
            )


            # FALLBACK: Search for consequence provisions in the same chapter
            # when the dedicated consequence retriever returns no results.

            if not consequence_documents:
                debug_log(
                    "STEP 5 FALLBACK: Dedicated consequence retrieval "
                    "returned no documents."
                )

                consequence_terms = [
                    "penalty",
                    "penalties",
                    "shall be liable",
                    "liable to a penalty",
                    "punishable",
                    "punishment",
                    "fine",
                    "imprisonment",
                    "contravention",
                    "offence",
                    "offense",
                    "shall be liable to",
                ]

                # Identify the relevant chapter(s) from the primary
                # documents already retrieved for the question.
                relevant_chapters = {
                    document.chapter
                    for document in combined_documents.values()
                    if getattr(document, "chapter", None)
                    and (
                        not subject
                        or getattr(document, "subject", None) == subject
                    )
                }

                consequence_filters = [
                    KnowledgeDocument.content.ilike(f"%{term}%")
                    for term in consequence_terms
                ]

                fallback_query = db.query(KnowledgeDocument).filter(
                    or_(*consequence_filters)
                )

                if subject:
                    fallback_query = fallback_query.filter(
                        KnowledgeDocument.subject == subject
                    )

                # Prefer provisions in the same chapter as the primary rule.
                if relevant_chapters:
                    fallback_query = fallback_query.filter(
                        KnowledgeDocument.chapter.in_(relevant_chapters)
                    )

                fallback_documents = (
                    fallback_query
                    .order_by(
                        KnowledgeDocument.id
                    )
                    .limit(20)
                    .all()
                )

                consequence_documents = fallback_documents

                debug_log(
                    "STEP 5 FALLBACK RESULT COUNT: "
                    f"{len(consequence_documents)}"
                )

                for document in consequence_documents:
                    debug_log(
                        "STEP 5 FALLBACK DOCUMENT: "
                        f"ID={document.id}, "
                        f"SUBJECT={document.subject}, "
                        f"CHAPTER={document.chapter}, "
                        f"PAGE={document.page_number}"
                    )






            # DEBUG: Show how many documents were retrieved.
            print(
                "\nLEGAL CONSEQUENCE RESULT COUNT:",
                len(consequence_documents),
            )
            debug_log(f"STEP 5 RESULT COUNT: {len(consequence_documents)}")

            # DEBUG: Show details of every returned document.
            for document in consequence_documents:
                print(
                    "CONSEQUENCE RESULT:",
                    "ID =", document.id,
                    "| Subject =", document.subject,
                    "| Chapter =", document.chapter,
                    "| Page =", document.page_number,
                )
                debug_log(
                    f"CONSEQUENCE DOC: ID={document.id}, "
                    f"Subject={document.subject}, "
                    f"Chapter={document.chapter}, "
                    f"Page={document.page_number}"
                )

            # Existing target-presence check.
            debug_target_presence(
                consequence_documents,
                target_id=10596,
                stage="LEGAL CONSEQUENCE SEARCH",
            )

            combined_list = merge_legal_candidates(
                list(combined_documents.values()),
                consequence_documents,
            )

            combined_documents = {
                document.id: document
                for document in combined_list
            }

            print(
                "\nCANDIDATES AFTER CONSEQUENCE MERGE:",
                len(combined_documents),
            )
            debug_log(f"CANDIDATES AFTER CONSEQUENCE MERGE: {len(combined_documents)}")

        except Exception as e:
            print(
                "\nLEGAL CONSEQUENCE RETRIEVAL ERROR:",
                str(e),
            )
            debug_log(f"STEP 5 ERROR: {str(e)}")

    else:
        print(
            "\nLEGAL CONSEQUENCE RETRIEVAL SKIPPED: "
            "The query does not explicitly ask about a consequence."
        )
        debug_log("STEP 5 SKIPPED: No consequence intent detected")


    print(
        "\nFINAL CANDIDATE POOL BEFORE RERANK:",
        len(combined_documents)
    )
    debug_target_presence(
        list(combined_documents.values()),
        target_id=10596,
        stage="AFTER MERGE"
    )
    # ============================================================
    # 6. PREPARE RESULTS FOR RERANKER
    # ============================================================
    results_for_rerank = []
    seen_content = set()
    for document in combined_documents.values():
        content = (
            document.content
            or ""
        ).strip()
        if not content:
            continue
        content_key = content.lower()
        if content_key in seen_content:
            continue
        seen_content.add(
            content_key
        )
        results_for_rerank.append(
            {
                "id": document.id,
                "content": content,
                "text": content,
                "subject": document.subject,
                "chapter": document.chapter,
                "module": document.module,
                "page_number": document.page_number,
                "document_id": getattr(
                    document,
                    "document_id",
                    None
                ),
                "metadata": getattr(
                    document,
                    "metadata",
                    None
                )
            }
        )
    print(
        "\nRESULTS PREPARED FOR RERANK:",
        len(results_for_rerank)
    )
    # ============================================================
    # 7. RERANK
    # ============================================================
    try:
        reranked_results = rerank(
            query=retrieval_query,
            results=results_for_rerank
        )
        print(
            "\nRERANKED RESULTS:",
            len(reranked_results)
        )
    except Exception as e:
        print(
            "RERANK ERROR:",
            str(e)
        )
        reranked_results = results_for_rerank
    # ============================================================
    # 8. LEGAL TERM BOOST
    # ============================================================
    try:
        for result in reranked_results:
            bonus = calculate_legal_term_bonus(
                question,
                result.get("content", "")
            )
            original_score = result.get(
                "score",
                0
            )
            result["original_score"] = (
                original_score
            )
            result["legal_bonus"] = bonus
            result["score"] = (
                original_score + bonus
            )
    except Exception as e:
        print(
            "LEGAL TERM BOOST ERROR:",
            str(e)
        )
    # ============================================================
    # 9. SORT BY FINAL SCORE
    # ============================================================
    reranked_results.sort(
        key=lambda x: x.get(
            "score",
            0
        ),
        reverse=True
    )
    print(
        "\nTOP RESULTS AFTER RERANK + LEGAL BOOST:"
    )
    for index, result in enumerate(
        reranked_results[:15],
        start=1
    ):
        print(
            f"{index}. "
            f"ID={result.get('id')} "
            f"SCORE={result.get('score')} "
            f"LEGAL_BONUS={result.get('legal_bonus')}"
        )
        print(
            "   SUBJECT:",
            result.get("subject")
        )
        print(
            "   CHAPTER:",
            result.get("chapter")
        )
        print(
            "   PAGE:",
            result.get("page_number")
        )
        print(
            "   CONTENT:",
            (
                result.get("content", "")[:250]
                .replace("\n", " ")
            )
        )
    # ============================================================
    # 10. CHECK TARGET AFTER RERANK
    # ============================================================
    debug_target_presence(
        reranked_results,
        target_id=10596,
        stage="AFTER RERANK"
    )
    # ============================================================
    # 11. TOP-K RESULTS
    # ============================================================
    # ========================================================
    # SCENARIO CONTEXT LIMIT
    # ========================================================
    selection_limit = (
        min(top_k, 5)
        if is_scenario
        else top_k
    )
    top_results = reranked_results[:selection_limit]
    print(
        "SELECTION LIMIT:",
        selection_limit
    )
    print(
        "\nTOP K RESULTS:",
        len(top_results)
    )
    # ============================================================
    # 12. ADD NEIGHBORING CHUNKS
    # ============================================================
    try:
        existing_ids = {
            result.get("id")
            for result in top_results
        }
        base_results = list(
            top_results
        )
        for result in base_results:
            result_id = result.get(
                "id"
            )
            if not result_id:
                continue
            document = (
                db.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.id
                    == result_id
                )
                .first()
            )
            if not document:
                continue
            chapter = document.chapter
            subject_name = document.subject
            if not chapter:
                continue
            neighbor_documents = (
                db.query(KnowledgeDocument)
                .filter(
                    KnowledgeDocument.subject
                    == subject_name
                )
                .filter(
                    KnowledgeDocument.chapter
                    == chapter
                )
                .filter(
                    KnowledgeDocument.id
                    >= result_id - 2
                )
                .filter(
                    KnowledgeDocument.id
                    <= result_id + 2
                )
                .order_by(
                    KnowledgeDocument.id
                )
                .all()
            )
            for neighbor in neighbor_documents:
                if neighbor.id in existing_ids:
                    continue
                neighbor_content = (
                    neighbor.content
                    or ""
                ).strip()
                if not neighbor_content:
                    continue
                top_results.append(
                    {
                        "id": neighbor.id,
                        "content": neighbor_content,
                        "text": neighbor_content,
                        "subject": neighbor.subject,
                        "chapter": neighbor.chapter,
                        "module": neighbor.module,
                        "page_number": (
                            neighbor.page_number
                        ),
                        "document_id": getattr(
                            neighbor,
                            "document_id",
                            None
                        ),
                        "metadata": getattr(
                            neighbor,
                            "metadata",
                            None
                        ),
                        "is_neighbor": True
                    }
                )
                existing_ids.add(
                    neighbor.id
                )
                if len(top_results) >= selection_limit + 6:
                    break
            if len(top_results) >= selection_limit + 6:
                break
    except Exception as e:
        print(
            "NEIGHBOR CHUNK ERROR:",
            str(e)
        )
    # ============================================================
    # 13. FINAL TARGET CHECK BEFORE CONTEXT FILTER
    # ============================================================
    debug_target_presence(
        top_results,
        target_id=10596,
        stage="BEFORE CONTEXT FILTER"
    )
    # ============================================================
    # 14. LEGAL CONTEXT FILTER
    # ============================================================
    try:
        filtered_results = filter_retrieved_chunks(
            question=retrieval_query,
            chunks=top_results
        )
        print(
            "\nLEGAL CONTEXT FILTER:"
        )
        print(
            "BEFORE:",
            len(top_results)
        )
        print(
            "AFTER:",
            len(filtered_results)
        )
        top_results = filtered_results
    except Exception as e:
        print(
            "LEGAL CONTEXT FILTER ERROR:",
            str(e)
        )
    # ============================================================
    # 15. CONTEXT PRIORITIZATION
    # ============================================================

    if is_scenario and top_results:

        print("\nSCENARIO CONTEXT PRIORITIZATION")

        # Keep the highest-ranked retrieved result first.
        # The reranker has already ordered the results by relevance.
        prioritized_results = []

        # --------------------------------------------------------
        # 1. Primary legal rule
        # --------------------------------------------------------

        primary_result = top_results[0]

        primary_result["context_priority"] = "PRIMARY LEGAL RULE"

        prioritized_results.append(primary_result)

        print(
            "PRIMARY RULE:",
            primary_result.get("id")
        )

        # --------------------------------------------------------
        # 2. Supporting legal sources
        # --------------------------------------------------------

        for result in top_results[1:]:

            result["context_priority"] = "SUPPORTING SOURCE"

            prioritized_results.append(result)

        top_results = prioritized_results

        print(
            "PRIORITIZED CONTEXT:",
            len(top_results)
        )


    # ============================================================
    # 16. CLEAN FINAL CONTEXT
    # ============================================================

    for result in top_results:

        content = (
            result.get("content")
            or result.get("text")
            or ""
        )

        result["content"] = content
        result["text"] = content






    # ============================================================
    # 16. FINAL TARGET CHECK
    # ============================================================
    debug_target_presence(
        top_results,
        target_id=10596,
        stage="FINAL RESULTS"
    )
    # ============================================================
    # 17. FINAL DEBUG
    # ============================================================
    print(
        "\n========================================"
    )
    print(
        "FINAL KNOWLEDGE SEARCH RESULTS"
    )
    print(
        "========================================"
    )
    for index, result in enumerate(
        top_results,
        start=1
    ):
        print(
            f"\n[{index}]"
        )
        print(
            "ID:",
            result.get("id")
        )
        print(
            "SUBJECT:",
            result.get("subject")
        )
        print(
            "MODULE:",
            result.get("module")
        )
        print(
            "CHAPTER:",
            result.get("chapter")
        )
        print(
            "PAGE:",
            result.get("page_number")
        )
        print(
            "SCORE:",
            result.get("score")
        )
        print(
            "LEGAL BONUS:",
            result.get("legal_bonus")
        )
        print(
            "CONTENT:",
            (
                result.get("content", "")[:500]
                .replace("\n", " ")
            )
        )
    print(
        "\nRETURNING",
        len(top_results),
        "RESULTS"
    )
    print(
        "========================================\n"
    )
    return top_results