
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.knowledge_document_model import KnowledgeDocument


# ============================================================
# LEGAL CONCEPT MAP
# ============================================================
# Maps natural-language descriptions to legal terms/phrases
# that are commonly present in ICAI study material.
#
# IMPORTANT:
# Not every phrase has the same retrieval importance.
#
# Strong phrases:
#   Highly specific legal terminology.
#
# Medium phrases:
#   Useful legal phrases but can occur in multiple chapters.
#
# Weak phrases:
#   Generic words that should NOT dominate retrieval.
# ============================================================

LEGAL_CONCEPTS = {

    # --------------------------------------------------------
    # PRIVATE PLACEMENT
    # --------------------------------------------------------
    "private placement": {
        "strong": [
            "private placement",
            "private placement offer cum application letter",
            "persons identified by the board",
            "PAS-4",
            "PAS-3",
        ],
        "medium": [
            "selected investors",
            "select group",
            "offer letter",
            "special resolution",
            "bank account of the person subscribing",
        ],
        "weak": [
            "subscription",
        ],
    },

    # --------------------------------------------------------
    # RED HERRING PROSPECTUS
    # --------------------------------------------------------
    "red herring prospectus": {
        "strong": [
            "red herring prospectus",
            "opening of the subscription list",
        ],
        "medium": [
            "RHP",
            "subscription list",
            "public offer",
        ],
        "weak": [
            "registrar",
        ],
    },

    # --------------------------------------------------------
    # PROSPECTUS
    # --------------------------------------------------------
    "prospectus": {
        "strong": [
            "prospectus",
            "issue of securities",
        ],
        "medium": [
            "public offer",
            "subscription list",
        ],
        "weak": [
            "registrar",
        ],
    },

    # --------------------------------------------------------
    # RIGHTS ISSUE
    # --------------------------------------------------------
    "rights issue": {
        "strong": [
            "rights issue",
            "rights offer",
            "offer to existing shareholders",
        ],
        "medium": [
            "existing shareholders",
            "further issue",
        ],
        "weak": [],
    },

    # --------------------------------------------------------
    # BONUS ISSUE
    # --------------------------------------------------------
    "bonus issue": {
        "strong": [
            "bonus issue",
            "bonus shares",
            "capitalisation of profits",
        ],
        "medium": [
            "free reserves",
            "securities premium account",
        ],
        "weak": [],
    },

    # --------------------------------------------------------
    # BUY BACK
    # --------------------------------------------------------
    "buy back": {
        "strong": [
            "buy-back",
            "buyback",
            "purchase of own securities",
            "buy back of securities",
        ],
        "medium": [
            "equity shares",
        ],
        "weak": [],
    },

    # --------------------------------------------------------
    # RELATED PARTY TRANSACTION
    # --------------------------------------------------------
    "related party transaction": {
        "strong": [
            "related party transaction",
            "related party",
        ],
        "medium": [
            "ordinary resolution",
            "special resolution",
            "director",
            "relative",
        ],
        "weak": [],
    },

    # --------------------------------------------------------
    # ANNUAL GENERAL MEETING
    # --------------------------------------------------------
    "annual general meeting": {
        "strong": [
            "annual general meeting",
            "AGM",
        ],
        "medium": [
            "annual meeting",
            "general meeting",
        ],
        "weak": [],
    },

    # --------------------------------------------------------
    # BOARD MEETING
    # --------------------------------------------------------
    "board meeting": {
        "strong": [
            "board meeting",
            "meeting of the board",
            "meetings of the board",
        ],
        "medium": [],
        "weak": [],
    },

    # --------------------------------------------------------
    # DIVIDEND
    # --------------------------------------------------------
    "dividend": {
        "strong": [
            "dividend",
            "declaration of dividend",
        ],
        "medium": [
            "interim dividend",
            "final dividend",
        ],
        "weak": [],
    },
}


# ============================================================
# PHRASE WEIGHTS
# ============================================================

# Strong legal phrase:
# Very specific and highly relevant.
STRONG_WEIGHT = 100

# Medium phrase:
# Useful supporting evidence.
MEDIUM_WEIGHT = 30

# Weak phrase:
# Generic terms. Useful only as supporting evidence.
WEAK_WEIGHT = 5


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def _normalize(text: str) -> str:
    """
    Normalize text so that searches work consistently.

    Examples:

        "Red-Herring Prospectus"
            ->
        "red herring prospectus"

        "PAS-4"
            ->
        "pas 4"
    """

    if not text:
        return ""

    return " ".join(
        text.lower()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


# ============================================================
# PHRASE MATCHING
# ============================================================

def _phrase_matches(
    content: str,
    phrase: str,
) -> bool:
    """
    Check whether a normalized phrase exists in normalized content.
    """

    normalized_content = _normalize(content)
    normalized_phrase = _normalize(phrase)

    if not normalized_phrase:
        return False

    return normalized_phrase in normalized_content


# ============================================================
# DETECT LEGAL CONCEPT
# ============================================================

def detect_legal_concepts(
    question: str,
    topic: Optional[str] = None,
    expanded_query: Optional[str] = None,
) -> List[str]:

    combined_text = " ".join(
        [
            question or "",
            topic or "",
            expanded_query or "",
        ]
    )

    text = _normalize(combined_text)

    detected = []

    for concept, phrase_groups in LEGAL_CONCEPTS.items():

        all_phrases = []

        all_phrases.extend(
            phrase_groups.get("strong", [])
        )

        all_phrases.extend(
            phrase_groups.get("medium", [])
        )

        all_phrases.extend(
            phrase_groups.get("weak", [])
        )

        for phrase in all_phrases:

            normalized_phrase = _normalize(phrase)

            if not normalized_phrase:
                continue

            if normalized_phrase in text:
                detected.append(concept)
                break

    return list(dict.fromkeys(detected))


# ============================================================
# BUILD SEARCH PHRASES
# ============================================================

def _build_search_phrases(
    detected_concepts: List[str],
) -> List[Tuple[str, int, str]]:
    """
    Build weighted search phrases.

    Returns:

        [
            ("red herring prospectus", 100, "strong"),
            ("opening of the subscription list", 100, "strong"),
            ("subscription list", 30, "medium"),
            ("registrar", 5, "weak"),
        ]
    """

    phrases: List[Tuple[str, int, str]] = []

    for concept in detected_concepts:

        concept_data = LEGAL_CONCEPTS.get(
            concept,
            {}
        )

        # ----------------------------------------------------
        # Strong phrases
        # ----------------------------------------------------

        for phrase in concept_data.get(
            "strong",
            []
        ):

            normalized_phrase = _normalize(
                phrase
            )

            if normalized_phrase:
                phrases.append(
                    (
                        normalized_phrase,
                        STRONG_WEIGHT,
                        "strong",
                    )
                )

        # ----------------------------------------------------
        # Medium phrases
        # ----------------------------------------------------

        for phrase in concept_data.get(
            "medium",
            []
        ):

            normalized_phrase = _normalize(
                phrase
            )

            if normalized_phrase:
                phrases.append(
                    (
                        normalized_phrase,
                        MEDIUM_WEIGHT,
                        "medium",
                    )
                )

        # ----------------------------------------------------
        # Weak phrases
        # ----------------------------------------------------

        for phrase in concept_data.get(
            "weak",
            []
        ):

            normalized_phrase = _normalize(
                phrase
            )

            if normalized_phrase:
                phrases.append(
                    (
                        normalized_phrase,
                        WEAK_WEIGHT,
                        "weak",
                    )
                )

    # --------------------------------------------------------
    # Remove duplicate phrases while keeping the highest
    # weight.
    # --------------------------------------------------------

    phrase_map: Dict[str, Tuple[int, str]] = {}

    for phrase, weight, strength in phrases:

        if (
            phrase not in phrase_map
            or weight > phrase_map[phrase][0]
        ):
            phrase_map[phrase] = (
                weight,
                strength,
            )

    return [
        (
            phrase,
            weight,
            strength,
        )
        for phrase, (weight, strength)
        in phrase_map.items()
    ]


# ============================================================
# SCORE DOCUMENT
# ============================================================

def _score_document(
    document: KnowledgeDocument,
    search_phrases: List[Tuple[str, int, str]],
) -> Tuple[int, List[str]]:

    content = _normalize(
        document.content or ""
    )

    score = 0
    matched_phrases = []

    for phrase, weight, strength in search_phrases:

        if not phrase:
            continue

        if phrase in content:

            score += weight

            matched_phrases.append(
                f"{phrase} [{strength} +{weight}]"
            )

    return score, matched_phrases


# ============================================================
# CONCEPT RETRIEVAL
# ============================================================

def retrieve_by_legal_concept(
    db: Session,
    question: str,
    topic: Optional[str] = None,
    expanded_query: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = 30,
) -> List[KnowledgeDocument]:

    # ========================================================
    # 1. DETECT CONCEPTS
    # ========================================================

    detected_concepts = detect_legal_concepts(
        question=question,
        topic=topic,
        expanded_query=expanded_query,
    )

    print(
        "\n========== LEGAL CONCEPT RETRIEVAL =========="
    )

    print(
        "Detected legal concepts:",
        detected_concepts,
    )

    if not detected_concepts:

        print(
            "No legal concept detected."
        )

        return []


    # ========================================================
    # 2. BUILD WEIGHTED PHRASES
    # ========================================================

    search_phrases = _build_search_phrases(
        detected_concepts
    )

    print(
        "\nWeighted legal phrases:"
    )

    for phrase, weight, strength in search_phrases:

        print(
            f"  [{strength.upper()}] "
            f"{phrase} -> {weight}"
        )


    if not search_phrases:

        print(
            "No usable legal phrases found."
        )

        return []


    # ========================================================
    # 3. BUILD DATABASE FILTERS
    # ========================================================
    #
    # IMPORTANT:
    #
    # We retrieve candidates using the legal phrases, but
    # we DO NOT use `.limit(limit)` directly here.
    #
    # The previous implementation did:
    #
    #     OR(all phrases).limit(30).all()
    #
    # That meant PostgreSQL could return arbitrary matching
    # documents before our reranker ever saw them.
    #
    # We instead retrieve a larger candidate pool and perform
    # deterministic legal scoring in Python.
    # ========================================================

    filters = []

    for phrase, weight, strength in search_phrases:

        if not phrase:
            continue

        filters.append(
            KnowledgeDocument.content.ilike(
                f"%{phrase}%"
            )
        )


    if not filters:

        return []


    query = (
        db.query(
            KnowledgeDocument
        )
        .filter(
            or_(*filters)
        )
    )


    # ========================================================
    # 4. SUBJECT FILTER
    # ========================================================
    #
    # If query understanding already identified:
    #
    #     Corporate and Other Laws
    #
    # then keep legal retrieval inside that subject.
    # ========================================================

    if subject:

        query = query.filter(
            KnowledgeDocument.subject == subject
        )

        print(
            "Subject filter:",
            subject,
        )


    # ========================================================
    # 5. RETRIEVE LARGE CANDIDATE POOL
    # ========================================================
    #
    # We intentionally retrieve more than the final `limit`.
    #
    # Example:
    #
    # final limit = 30
    # candidate pool = 200
    #
    # This gives our deterministic scorer enough documents
    # to find the strongest legal matches.
    # ========================================================

    candidate_pool_size = max(
        limit * 10,
        100,
    )

    candidate_pool_size = min(
        candidate_pool_size,
        500,
    )

    documents = (
        query
        .limit(candidate_pool_size)
        .all()
    )

    print(
        "Raw legal concept candidates:",
        len(documents),
    )


    if not documents:

        print(
            "No legal concept candidates found."
        )

        return []


    # ========================================================
    # 6. SCORE EVERY DOCUMENT
    # ========================================================

    scored_documents = []

    for document in documents:

        score, matched_phrases = (
            _score_document(
                document=document,
                search_phrases=search_phrases,
            )
        )

        if score <= 0:
            continue

        scored_documents.append(
            (
                score,
                document,
                matched_phrases,
            )
        )


    # ========================================================
    # 7. SORT BY LEGAL RELEVANCE
    # ========================================================
    #
    # This is the important fix.
    #
    # Documents containing:
    #
    #     "red herring prospectus"
    #
    # receive +100.
    #
    # Documents containing:
    #
    #     "opening of the subscription list"
    #
    # receive another +100.
    #
    # A document containing only:
    #
    #     "registrar"
    #
    # receives only +5.
    #
    # Therefore generic documents cannot dominate the results.
    # ========================================================

    scored_documents.sort(
        key=lambda item: (
            item[0],
            len(item[2]),
        ),
        reverse=True,
    )


    # ========================================================
    # 8. TAKE FINAL RESULTS
    # ========================================================

    final_results = [
        document
        for score, document, matched_phrases
        in scored_documents[:limit]
    ]


    # ========================================================
    # 9. DEBUG OUTPUT
    # ========================================================

    print(
        "\n========== RANKED LEGAL CANDIDATES =========="
    )

    for rank, (
        score,
        document,
        matched_phrases,
    ) in enumerate(
        scored_documents[:limit],
        start=1,
    ):

        print(
            f"\nRank: {rank}"
        )

        print(
            f"Score: {score}"
        )

        print(
            f"ID: {document.id}"
        )

        print(
            f"SUBJECT: {document.subject}"
        )

        print(
            f"PAGE: {document.page_number}"
        )

        print(
            f"CHAPTER: {document.chapter}"
        )

        print(
            "Matched phrases:"
        )

        for phrase in matched_phrases:

            print(
                f"  - {phrase}"
            )

        print(
            "Content:"
        )

        print(
            (document.content or "")[:400]
        )

        print(
            "-------------------------------------------"
        )


    print(
        "\nFinal legal concept candidates:",
        len(final_results),
    )


    return final_results


# ============================================================
# MERGE WITH EXISTING RETRIEVAL RESULTS
# ============================================================

def merge_legal_candidates(
    existing_documents: List[KnowledgeDocument],
    legal_documents: List[KnowledgeDocument],
) -> List[KnowledgeDocument]:

    documents_by_id = {}

    # ========================================================
    # EXISTING RETRIEVAL FIRST
    # ========================================================

    for document in existing_documents:

        documents_by_id[
            document.id
        ] = document


    # ========================================================
    # ADD LEGAL CONCEPT CANDIDATES
    # ========================================================

    for document in legal_documents:

        documents_by_id[
            document.id
        ] = document


    # ========================================================
    # CREATE MERGED LIST
    # ========================================================

    merged_documents = list(
        documents_by_id.values()
    )


    print(
        "\nMerged retrieval candidates:",
        len(merged_documents),
    )


    return merged_documents




# ============================================================
# LEGAL CONSEQUENCE RETRIEVAL
# ============================================================

LEGAL_CONSEQUENCE_TERMS = [
    "penalty",
    "penalties",
    "liable",
    "liability",
    "shall be liable",
    "punishable",
    "punishment",
    "fine",
    "imprisonment",
    "contravention",
    "offence",
    "offense",
    "default",
    "non-compliance",
    "non compliance",
    "failure to comply",
    "prosecution",
    "adjudication",
    "void",
    "invalid",
    "compensation",
    "consequences",
    "consequence",
    "shall be punished",
]




import re
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

# Keep your existing imports for:
# KnowledgeDocument, LEGAL_CONCEPTS, LEGAL_CONSEQUENCE_TERMS


def retrieve_legal_consequences(
    db: Session,
    question: str,
    topic: Optional[str] = None,
    expanded_query: Optional[str] = None,
    subject: Optional[str] = None,
    limit: int = 10,
) -> List[KnowledgeDocument]:
    """
    Retrieve only consequence chunks matching the requested
    legal section and concept. Never infer a consequence.
    """

    def log(message: str) -> None:
        print(f"[LEGAL CONSEQUENCE] {message}", flush=True)

    query_text = " ".join(
        part.strip()
        for part in (question, topic, expanded_query)
        if part and part.strip()
    )

    if not query_text:
        log("Rejected: empty query")
        return []

    # Extract the section explicitly referenced by the question.
    section_match = re.search(
        r"\b(?:section|sec\.?)\s*(\d+[A-Z]?)\b",
        query_text,
        flags=re.IGNORECASE,
    )

    if not section_match:
        log("Rejected: no explicit legal section found")
        return []

    section_number = section_match.group(1).upper()
    section_pattern = re.compile(
        rf"\b(?:section|sec\.?)\s*{re.escape(section_number)}"
        rf"(?!\d)",
        flags=re.IGNORECASE,
    )
    query_lower = query_text.lower()

    # Use specific concept phrases, not generic words like "registrar".
    concept_anchors = []

    for concept_name, concept_data in LEGAL_CONCEPTS.items():
        phrases = concept_data.get("strong", [])

        matched = (
            concept_name.lower() in query_lower
            or any(p.lower() in query_lower for p in phrases)
        )

        if matched:
            concept_anchors.extend(phrases)

    concept_anchors = list(dict.fromkeys(
        p.strip().lower()
        for p in concept_anchors
        if p and p.strip()
    ))

    if not concept_anchors:
        log("Rejected: no specific legal concept found")
        return []

    # Build a bounded candidate query. Subject filtering helps
    # prevent similarly numbered sections from other Acts matching.
    concept_filters = [
        KnowledgeDocument.content.ilike(f"%{phrase}%")
        for phrase in concept_anchors
    ]

    query = db.query(KnowledgeDocument).filter(
        or_(*concept_filters)
    )

    if subject:
        query = query.filter(
            KnowledgeDocument.subject.ilike(f"%{subject}%")
        )

    candidate_limit = min(max(limit * 30, 100), 500)
    candidates = query.limit(candidate_limit).all()

    log(
        f"Section={section_number}, subject={subject!r}, "
        f"candidates={len(candidates)}"
    )

    results = []
    seen_ids = set()

    consequence_terms = [
        term.lower()
        for term in LEGAL_CONSEQUENCE_TERMS
        if term
    ]

    for document in candidates:
        content = document.content or ""
        normalized_content = content.lower()

        # 1. The same legal section must be explicitly referenced.
        if not section_pattern.search(content):
            log(f"REJECT ID={document.id}: section mismatch")
            continue

        # 2. The same specific legal concept must occur in the chunk.
        matched_concepts = [
            phrase for phrase in concept_anchors
            if phrase in normalized_content
        ]

        if not matched_concepts:
            log(f"REJECT ID={document.id}: concept mismatch")
            continue

        # 3. The chunk must explicitly contain consequence language.
        matched_terms = [
            term for term in consequence_terms
            if term in normalized_content
        ]

        if not matched_terms:
            log(f"REJECT ID={document.id}: no consequence evidence")
            continue

        # 4. Verify subject again before accepting.
        if subject:
            document_subject = (document.subject or "").lower()
            if subject.lower() not in document_subject:
                log(f"REJECT ID={document.id}: subject mismatch")
                continue

        if document.id in seen_ids:
            continue

        seen_ids.add(document.id)
        results.append(document)

        log(
            f"ACCEPT ID={document.id}, "
            f"chapter={document.chapter!r}, "
            f"page={document.page_number}, "
            f"concepts={matched_concepts}, "
            f"consequence_terms={matched_terms}"
        )

        if len(results) >= limit:
            break

    log(f"Final consequence results: {len(results)}")
    return results