
"""
Legal Context Filter
--------------------

Purpose:
    Clean retrieved ICAI chunks before sending them to the LLM.

Main problems this module is designed to handle:

    1. One retrieved chunk containing multiple unrelated legal topics.
    2. Section/topic contamination inside a retrieved chunk.
    3. Relevant legal content surrounded by unrelated content.
    4. AGM / General Meeting / Board Meeting confusion.
    5. Prospectus / Red Herring Prospectus confusion.
    6. Annual Return / AGM confusion.
    7. Notice-related content mixed with unrelated penalties.
    8. Selecting relevant logical units instead of blindly passing
       the complete retrieved chunk to the LLM.

IMPORTANT:

    This file is standalone.

    It does NOT modify the main retrieval pipeline.

    It does NOT write anything to PostgreSQL.

    It does NOT call an LLM.

    It only works on text that has already been retrieved.
"""

import re
from typing import Any, Dict, List, Set


# ============================================================
# CONFIGURATION
# ============================================================

MAX_OUTPUT_CHARS = 5000

# Minimum score required for a unit to be considered relevant.
MIN_RELEVANCE_SCORE = 3.0

# How close another unit must be to the best unit before
# we consider keeping it.
#
# Example:
#
# Best unit = 20
# Secondary unit = 16
#
# 16 / 20 = 0.80
#
# This is close enough ONLY if the unit is also about the
# same legal topic.
SECONDARY_SCORE_RATIO = 0.78

# Maximum number of logical units we allow from one chunk.
MAX_SELECTED_UNITS = 3


# ============================================================
# REGEX PATTERNS
# ============================================================

SECTION_PATTERN = re.compile(
    r"(?i)(?<!sub-)(?<!sub)"
    r"\b(?:section|sec\.?)\s+"
    r"\d+[A-Za-z]?"
    r"(?:\s*\(\s*\d+\s*\))?"
)
# Examples:
#
# Question 13
# Question 14.
# Ques. 15
#
EXPLICIT_QUESTION_PATTERN = re.compile(
    r"(?i)"
    r"(?:^|\n)\s*"
    r"(?:question|ques\.?)"
    r"\s*\d*\s*[:.)-]?"
)

# ICAI frequently has:
#
# 14. According to section 101...
#
# We require a capital letter after the number so that:
#
# 21 days
# 60 days
# 2013.
#
# are not treated as question boundaries.
NUMBERED_QUESTION_PATTERN = re.compile(
    r"(?<!\d)"
    r"(\d{1,3})\.\s+"
    r"(?=[A-Z])"
)

ANSWER_PATTERN = re.compile(
    r"(?im)"
    r"(?:^|\n)\s*"
    r"answer\s*\d*\s*[:.)-]?"
)


# ============================================================
# LEGAL TOPIC DEFINITIONS
# ============================================================
#
# These are TOPIC signals, not answer mappings.
#
# We are not saying:
#
#     AGM -> Section 101
#
# Instead we are saying:
#
#     these words usually belong to this legal topic.
#
# This helps identify contamination.
#

LEGAL_TOPIC_PATTERNS = {
    "agm_general_meeting": [
        "annual general meeting",
        "general meeting",
        "agm",
        "clear twenty-one days",
        "21 clear days",
        "notice of a meeting",
        "shorter notice",
        "members",
        "shareholders",
    ],

    "board_meeting": [
        "board meeting",
        "meeting of the board",
        "board of directors",
        "directors",
        "every director",
        "seven days",
        "7 days",
        "notice to every director",
    ],

    "annual_return": [
        "annual return",
        "section 92",
        "section 92(5)",
        "section 92 (5)",
        "filing annual return",
        "penalty for filing",
        "annual return filing",
    ],

    "prospectus": [
        "prospectus",
        "red herring prospectus",
        "rhp",
        "subscription list",
        "public offer",
        "opening of the subscription list",
        "opening of the offer",
    ],

    "allotment": [
        "allotment",
        "return of allotment",
        "section 39",
        "section 42",
        "private placement",
    ],

    "proxy": [
        "proxy",
        "proxy form",
        "appoint a proxy",
        "proxy holder",
    ],

    "quorum": [
        "quorum",
        "quorum for meeting",
        "presence of members",
        "minimum number of members",
    ],

    "explanatory_statement": [
        "explanatory statement",
        "material facts",
        "section 102",
    ],

    "minutes": [
        "minutes",
        "minutes of meeting",
        "minutes book",
        "section 118",
    ],

    "notice": [
        "notice",
        "notice period",
        "notice to members",
        "notice to directors",
        "notice of meeting",
    ],

    "penalty": [
        "penalty",
        "penal provisions",
        "liable to a penalty",
        "fine",
        "continuing failure",
    ],
}


# ============================================================
# GENERIC STOP WORDS
# ============================================================

STOP_WORDS = {
    "the",
    "and",
    "are",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "whether",
    "this",
    "that",
    "with",
    "from",
    "into",
    "does",
    "did",
    "have",
    "has",
    "been",
    "being",
    "under",
    "explain",
    "requirement",
    "required",
    "according",
    "company",
    "question",
    "following",
    "given",
    "case",
    "also",
    "only",
    "before",
    "after",
    "such",
    "their",
    "there",
    "they",
    "them",
    "then",
    "than",
    "because",
    "should",
    "would",
    "could",
    "into",
    "from",
    "for",
    "its",
    "not",
    "all",
    "any",
    "each",
}


# ============================================================
# BASIC TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    """
    Normalize whitespace while preserving paragraph boundaries.
    """

    if not text:
        return ""

    text = str(text)

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Normalize tabs/spaces.
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# NORMALIZE SECTION
# ============================================================

def normalize_section(section: str) -> str:
    """
    Convert section text into a consistent representation.

    Examples:

        Section 101(1)
        section 101 (1)

    both become:

        section 101(1)
    """

    section = section.lower()
    section = re.sub(r"\s+", " ", section)
    section = re.sub(r"\s*\(\s*", "(", section)
    section = re.sub(r"\s*\)\s*", ")", section)

    return section.strip()


# ============================================================
# EXTRACT SECTIONS
# ============================================================

def extract_sections(text: str) -> List[str]:
    """
    Extract all section references from text.
    """

    matches = SECTION_PATTERN.findall(text)

    return [
        normalize_section(match)
        for match in matches
    ]


# ============================================================
# EXTRACT QUERY CONCEPTS
# ============================================================

def extract_query_concepts(question: str) -> Dict[str, Any]:
    """
    Extract deterministic legal concepts from the user question.

    No LLM is used here.

    Returns:

        sections
        topics
        concepts
        keywords
        phrases
    """

    question_clean = clean_text(question)
    question_lower = question_clean.lower()

    # --------------------------------------------------------
    # Sections
    # --------------------------------------------------------

    sections = extract_sections(question_clean)

    # --------------------------------------------------------
    # Topic detection
    # --------------------------------------------------------

    topics = []

    for topic, patterns in LEGAL_TOPIC_PATTERNS.items():

        for pattern in patterns:

            if pattern.lower() in question_lower:

                topics.append(topic)
                break

    topics = sorted(set(topics))

    # --------------------------------------------------------
    # Concepts
    # --------------------------------------------------------

    important_concepts = [
        "annual general meeting",
        "general meeting",
        "agm",
        "board meeting",
        "board of directors",
        "director",
        "notice",
        "clear days",
        "shorter notice",
        "quorum",
        "proxy",
        "explanatory statement",
        "red herring prospectus",
        "prospectus",
        "subscription list",
        "offer",
        "allotment",
        "depreciation",
        "annual return",
        "penalty",
        "shareholder",
        "member",
        "minutes",
    ]

    concepts = [
        concept
        for concept in important_concepts
        if concept in question_lower
    ]

    # --------------------------------------------------------
    # Keywords
    # --------------------------------------------------------

    words = re.findall(
        r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b",
        question_lower,
    )

    keywords = sorted(
        {
            word
            for word in words
            if word not in STOP_WORDS
        }
    )

    # --------------------------------------------------------
    # Important multi-word phrases
    # --------------------------------------------------------

    phrases = []

    phrase_candidates = [
        "annual general meeting",
        "general meeting",
        "board meeting",
        "board of directors",
        "clear days",
        "shorter notice",
        "annual return",
        "red herring prospectus",
        "subscription list",
        "explanatory statement",
        "notice to every director",
        "notice to members",
    ]

    for phrase in phrase_candidates:

        if phrase in question_lower:
            phrases.append(phrase)

    return {
        "sections": sections,
        "topics": topics,
        "concepts": concepts,
        "keywords": keywords,
        "phrases": phrases,
    }


# ============================================================
# DETECT LEGAL TOPICS IN A UNIT
# ============================================================

def detect_unit_topics(text: str) -> Set[str]:
    """
    Detect legal topic signals inside one logical unit.
    """

    text_lower = text.lower()

    topics = set()

    for topic, patterns in LEGAL_TOPIC_PATTERNS.items():

        for pattern in patterns:

            if pattern.lower() in text_lower:

                topics.add(topic)
                break

    return topics


# ============================================================
# LOGICAL UNIT SPLITTING
# ============================================================

# ============================================================
# ICAI HEADING-BASED SPLITTING
# ============================================================

ICAI_LEGAL_HEADINGS = [
    "timing of issue the red herring prospectus",
    "timing of issue of the red herring prospectus",
    "filing of red herring prospectus with the registrar",
    "filing of red herring prospectus with registrar",
    "obligations under red herring prospectus vis-à-vis prospectus",
    "obligations under red herring prospectus vis a vis prospectus",
    "filing with registrar and sebi upon closing of offer",
    "filing with registrar and sebi upon closing of the offer",
    "concept of abridged prospectus",
]


def split_by_icai_headings(text: str) -> List[str]:
    """
    Split ICAI material using known legal headings.

    This is especially useful when an ICAI chunk contains
    multiple prospectus sub-topics but does not contain
    Question/Answer boundaries.
    """

    text = clean_text(text)

    if not text:
        return []

    lower_text = text.lower()

    boundaries = []

    for heading in ICAI_LEGAL_HEADINGS:
        start = 0

        while True:
            position = lower_text.find(
                heading,
                start,
            )

            if position == -1:
                break

            boundaries.append(
                position
            )

            start = position + len(heading)

    boundaries = sorted(set(boundaries))

    if len(boundaries) < 2:
        return [text]

    units = []

    # Preserve content before the first heading.
    if boundaries[0] > 0:
        prefix = text[:boundaries[0]].strip()

        if prefix:
            units.append(prefix)

    for index, boundary in enumerate(boundaries):

        if index + 1 < len(boundaries):
            end = boundaries[index + 1]
        else:
            end = len(text)

        unit = text[boundary:end].strip()

        if unit:
            units.append(unit)

    return units


def split_into_logical_units(text: str) -> List[str]:
    """
    Split ICAI content into logical legal/question units.

    Handles:

        Question 13
        Question 14

    and:

        ... previous answer ... 14. According to section 101...

    Also preserves the prefix before the first numbered question,
    because ICAI chunks often begin in the middle of an answer.
    """

    text = clean_text(text)

    if not text:
        return []

    matches = []

    # --------------------------------------------------------
    # Explicit Question markers
    # --------------------------------------------------------

    for match in EXPLICIT_QUESTION_PATTERN.finditer(text):
        matches.append(match)

    # --------------------------------------------------------
    # ICAI numbered question markers
    # --------------------------------------------------------

    for match in NUMBERED_QUESTION_PATTERN.finditer(text):
        matches.append(match)

    # --------------------------------------------------------
    # Sort boundaries
    # --------------------------------------------------------

    matches = sorted(
        matches,
        key=lambda match: match.start(),
    )

    # Remove duplicate positions.
    unique_matches = []

    for match in matches:

        if not unique_matches:
            unique_matches.append(match)
            continue

        previous = unique_matches[-1]

        if match.start() != previous.start():
            unique_matches.append(match)

    matches = unique_matches

    # --------------------------------------------------------
    # Split on question boundaries.
    # --------------------------------------------------------

    if matches:

        units = []

        # Prefix before first question.
        first_start = matches[0].start()

        if first_start > 0:

            prefix = text[:first_start].strip()

            if prefix:
                units.append(prefix)

        # Question units.
        for index, match in enumerate(matches):

            start = match.start()

            if index + 1 < len(matches):
                end = matches[index + 1].start()
            else:
                end = len(text)

            unit = text[start:end].strip()

            if unit:
                units.append(unit)

        if len(units) >= 2:
            return units

    # --------------------------------------------------------
    # Fallback: Answer boundaries.
    # --------------------------------------------------------

    answer_matches = list(
        ANSWER_PATTERN.finditer(text)
    )

    if len(answer_matches) >= 2:

        units = []

        for index, match in enumerate(answer_matches):

            start = match.start()

            if index + 1 < len(answer_matches):
                end = answer_matches[index + 1].start()
            else:
                end = len(text)

            unit = text[start:end].strip()

            if unit:
                units.append(unit)

        if len(units) >= 2:
            return units

    # --------------------------------------------------------
    # ICAI heading-based fallback.
    # --------------------------------------------------------

    heading_units = split_by_icai_headings(text)

    if len(heading_units) >= 2:
        return heading_units

    # --------------------------------------------------------
    # No reliable boundary.
    # Preserve original chunk.
    # --------------------------------------------------------

    return [text]

# ============================================================
# ANALYZE UNIT
# ============================================================

def analyze_unit(unit: str) -> Dict[str, Any]:
    """
    Extract searchable information from one logical unit.
    """

    unit_clean = clean_text(unit)
    unit_lower = unit_clean.lower()

    sections = set(
        extract_sections(unit_clean)
    )

    topics = detect_unit_topics(unit_clean)

    words = set(
        re.findall(
            r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b",
            unit_lower,
        )
    )

    return {
        "text": unit_clean,
        "lower": unit_lower,
        "sections": sections,
        "topics": topics,
        "words": words,
    }


# ============================================================
# SCORE UNIT
# ============================================================

def score_unit(
    question: str,
    query_info: Dict[str, Any],
    unit: str,
) -> Dict[str, Any]:
    """
    Score one logical unit against the user's question.

    This score represents contextual relevance.

    It is NOT a legal correctness score.
    """

    unit_info = analyze_unit(unit)

    unit_text = unit_info["lower"]

    score = 0.0
    reasons = []

    # ========================================================
    # 1. EXACT SECTION MATCH
    # ========================================================

    query_sections = set(query_info["sections"])
    unit_sections = unit_info["sections"]

    matching_sections = (
        query_sections.intersection(unit_sections)
    )

    if matching_sections:

        score += 15.0 * len(matching_sections)

        reasons.append(
            "section match: "
            + ", ".join(sorted(matching_sections))
        )

    # ========================================================
    # 2. QUERY TOPIC MATCH
    # ========================================================

    query_topics = set(query_info["topics"])
    unit_topics = unit_info["topics"]

    matching_topics = (
        query_topics.intersection(unit_topics)
    )

    if matching_topics:

        score += 6.0 * len(matching_topics)

        reasons.append(
            "topic match: "
            + ", ".join(sorted(matching_topics))
        )

    # ========================================================
    # 3. COMPETING TOPIC PENALTY
    # ========================================================

    competing_topics = unit_topics - query_topics

    # Some topics are especially dangerous when they occur
    # inside an otherwise related chunk.
    #
    # Example:
    #
    # User = AGM notice
    #
    # Unit = Section 92 annual return penalty
    #
    # Both mention company/AGM, but annual_return is a
    # competing legal topic.

    dangerous_competing_topics = {
        "annual_return",
        "penalty",
        "allotment",
        "proxy",
        "quorum",
        "minutes",
        "explanatory_statement",
    }

    dangerous_conflicts = (
        competing_topics.intersection(
            dangerous_competing_topics
        )
    )

    if dangerous_conflicts:

        penalty = 5.0 * len(
            dangerous_conflicts
        )

        score -= penalty

        reasons.append(
            "competing legal topic penalty: "
            + ", ".join(
                sorted(dangerous_conflicts)
            )
        )

    # ========================================================
    # 4. PHRASE MATCH
    # ========================================================

    phrase_matches = []

    for phrase in query_info["phrases"]:

        if phrase in unit_text:

            phrase_matches.append(phrase)

    if phrase_matches:

        score += 3.0 * len(
            phrase_matches
        )

        reasons.append(
            "phrase match: "
            + ", ".join(phrase_matches)
        )

    # ========================================================
    # 5. CONCEPT MATCH
    # ========================================================

    concept_matches = []

    for concept in query_info["concepts"]:

        if concept in unit_text:

            concept_matches.append(concept)

    if concept_matches:

        # Cap generic concept contribution.
        concept_score = min(
            len(concept_matches) * 1.5,
            6.0,
        )

        score += concept_score

        reasons.append(
            "concept match: "
            + ", ".join(concept_matches)
        )

    # ========================================================
    # 6. KEYWORD OVERLAP
    # ========================================================

    query_keywords = set(
        query_info["keywords"]
    )

    unit_words = unit_info["words"]

    overlapping_words = (
        query_keywords.intersection(unit_words)
    )

    if overlapping_words:

        keyword_score = min(
            len(overlapping_words) * 0.4,
            4.0,
        )

        score += keyword_score

        reasons.append(
            f"keyword overlap: "
            f"{len(overlapping_words)}"
        )

    # ========================================================
    # 7. NOTICE CONTEXT
    # ========================================================

    notice_terms = {
        "notice",
        "meeting",
        "director",
        "member",
        "clear",
    }

    notice_matches = []

    for term in notice_terms:

        if term in query_keywords and term in unit_text:

            notice_matches.append(term)

    if notice_matches:

        notice_score = min(
            len(notice_matches) * 0.5,
            2.0,
        )

        score += notice_score

        reasons.append(
            "notice context: "
            + ", ".join(notice_matches)
        )

    # ========================================================
    # 8. QUESTION UNIT BONUS
    # ========================================================

    if re.search(
        r"(?i)\bquestion\b",
        unit_text,
    ):

        score += 0.5

        reasons.append(
            "logical question unit"
        )

    # ========================================================
    # 9. CLAMP
    # ========================================================

    score = round(score, 4)

    return {
        "score": score,
        "text": unit,
        "reasons": reasons,
        "sections": sorted(unit_sections),
        "topics": sorted(unit_topics),
        "matching_topics": sorted(matching_topics),
        "competing_topics": sorted(competing_topics),
    }


# ============================================================
# SELECT RELEVANT UNITS
# ============================================================

def select_relevant_units(
    scored_units: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Select relevant logical units.

    Important:

        We DO NOT simply select the top N units.

    A unit must either:

        1. Be the strongest relevant unit, or
        2. Be close enough to the strongest unit AND
           share the same legal topic.

    This is what prevents Section 92 material from being
    carried forward together with Section 101 material.
    """

    if not scored_units:
        return []

    ranked = sorted(
        scored_units,
        key=lambda item: item["score"],
        reverse=True,
    )

    best = ranked[0]
    best_score = best["score"]

    # --------------------------------------------------------
    # If nothing has meaningful relevance, preserve the
    # strongest unit as a safety fallback.
    # --------------------------------------------------------

    if best_score < MIN_RELEVANCE_SCORE:
        return [best]

    selected = [best]

    best_topics = set(
        best.get("topics", [])
    )

    # --------------------------------------------------------
    # Consider additional units.
    # --------------------------------------------------------

    for candidate in ranked[1:]:

        candidate_score = candidate["score"]

        if candidate_score < MIN_RELEVANCE_SCORE:
            continue

        # Score ratio.
        if best_score > 0:

            score_ratio = (
                candidate_score / best_score
            )

        else:
            score_ratio = 0

        if score_ratio < SECONDARY_SCORE_RATIO:
            continue

        candidate_topics = set(
            candidate.get("topics", [])
        )

        # ----------------------------------------------------
        # Same legal topic?
        # ----------------------------------------------------

        same_topic = bool(
            best_topics.intersection(
                candidate_topics
            )
        )

        # ----------------------------------------------------
        # Require actual question-level overlap as well.
        # A generic topic match such as "prospectus" is not
        # enough to keep another legal unit.
        # ----------------------------------------------------
        candidate_reasons = candidate.get("reasons", [])

        has_specific_match = any(
            reason.startswith("section match:")
            or reason.startswith("phrase match:")
            or reason.startswith("concept match:")
            for reason in candidate_reasons
        )

        if same_topic and has_specific_match:
            selected.append(candidate)
        # ----------------------------------------------------
        # If no explicit topic exists, allow a close score
        # only when there is strong phrase/concept overlap.
        # ----------------------------------------------------

        elif not best_topics and not candidate_topics:

            selected.append(candidate)

        # Otherwise discard it.
        else:

            candidate["rejected_reason"] = (
                "different legal topic from best unit"
            )

    return selected[:MAX_SELECTED_UNITS]


# ============================================================
# FILTER ONE CHUNK
# ============================================================

def filter_chunk(
    question: str,
    chunk: str,
    max_units: int = MAX_SELECTED_UNITS,
) -> Dict[str, Any]:
    """
    Process one retrieved chunk.
    """

    question = clean_text(question)
    chunk = clean_text(chunk)

    if not question:
        raise ValueError(
            "Question cannot be empty."
        )

    if not chunk:
        raise ValueError(
            "Chunk cannot be empty."
        )

    query_info = extract_query_concepts(
        question
    )

    units = split_into_logical_units(
        chunk
    )

    scored_units = []

    for unit in units:

        result = score_unit(
            question=question,
            query_info=query_info,
            unit=unit,
        )

        scored_units.append(result)

    scored_units.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    selected = select_relevant_units(
        scored_units
    )

    # Respect caller's requested maximum.
    selected = selected[:max_units]

    clean_context = "\n\n".join(
        item["text"]
        for item in selected
    )

    if len(clean_context) > MAX_OUTPUT_CHARS:

        clean_context = (
            clean_context[:MAX_OUTPUT_CHARS]
            .rstrip()
        )

    return {
        "question": question,
        "query_info": query_info,
        "original_chunk": chunk,
        "total_units": len(units),
        "units": scored_units,
        "selected_units": selected,
        "clean_context": clean_context,
    }


# ============================================================
# FILTER MULTIPLE RETRIEVED CHUNKS
# ============================================================


def filter_retrieved_chunks(
    question: str,
    chunks: List[Dict[str, Any]],
    max_units_per_chunk: int = MAX_SELECTED_UNITS,
) -> List[Dict[str, Any]]:
    """
    Filter retrieved chunks without changing the original
    reranker order.

    The legal filter is responsible for deciding:
        - relevant
        - irrelevant

    The reranker is responsible for ordering.

    Therefore:
        INPUT ORDER  = preserved
        FILTER SCORE = used only for relevance decisions
        OUTPUT ORDER = same as input order
    """

    if not question:
        return []

    if not chunks:
        return []

    # ========================================================
    # STEP 1: FILTER EACH CHUNK INDIVIDUALLY
    # ========================================================

    intermediate_results = []

    for original_index, chunk in enumerate(chunks):

        content = (
            chunk.get("content")
            or chunk.get("text")
            or ""
        )

        if not content:
            continue

        filtered = filter_chunk(
            question=question,
            chunk=content,
            max_units=max_units_per_chunk,
        )

        selected_units = filtered.get(
            "selected_units",
            [],
        )

        if not selected_units:
            continue

        best_unit = max(
            selected_units,
            key=lambda item: item.get(
                "score",
                0.0,
            ),
        )

        best_score = best_unit.get(
            "score",
            0.0,
        )

        result = dict(chunk)

        result["clean_context"] = filtered[
            "clean_context"
        ]

        result["logical_units"] = filtered[
            "units"
        ]

        result["selected_units"] = selected_units

        # Internal filter information
        result["_filter_best_score"] = best_score
        result["_filter_best_unit"] = best_unit
        result["_original_order"] = original_index

        intermediate_results.append(result)

    # ========================================================
    # STEP 2: NOTHING SURVIVED
    # ========================================================

    if not intermediate_results:
        return []

    # ========================================================
    # STEP 3: FIND STRONGEST CHUNK
    # ========================================================
    #
    # IMPORTANT:
    # This score is ONLY used to determine the strongest
    # legal context.
    #
    # It must NOT change the final output order.
    # ========================================================

    best_chunk = max(
        intermediate_results,
        key=lambda item: item.get(
            "_filter_best_score",
            0.0,
        ),
    )

    best_score = best_chunk.get(
        "_filter_best_score",
        0.0,
    )

    # ========================================================
    # STEP 4: EXTRACT STRONGEST CHUNK CONTEXT
    # ========================================================

    best_unit = best_chunk.get(
        "_filter_best_unit",
        {},
    )

    best_topics = set(
        best_unit.get(
            "topics",
            [],
        )
    )

    best_sections = set(
        best_unit.get(
            "sections",
            [],
        )
    )

    # ========================================================
    # STEP 5: DETERMINE WHICH CHUNKS SURVIVE
    # ========================================================

    accepted_ids = {
        best_chunk["id"]
    }

    for candidate in intermediate_results:

        if candidate["id"] == best_chunk["id"]:
            continue

        candidate_score = candidate.get(
            "_filter_best_score",
            0.0,
        )

        candidate_unit = candidate.get(
            "_filter_best_unit",
            {},
        )

        candidate_topics = set(
            candidate_unit.get(
                "topics",
                [],
            )
        )

        candidate_sections = set(
            candidate_unit.get(
                "sections",
                [],
            )
        )

        candidate_reasons = candidate_unit.get(
            "reasons",
            [],
        )

        # ----------------------------------------------------
        # SECTION MATCH
        # ----------------------------------------------------

        same_section = bool(
            best_sections.intersection(
                candidate_sections
            )
        )

        # ----------------------------------------------------
        # TOPIC MATCH
        # ----------------------------------------------------

        same_topic = bool(
            best_topics.intersection(
                candidate_topics
            )
        )

        # ----------------------------------------------------
        # SPECIFIC LEGAL MATCH
        # ----------------------------------------------------

        has_specific_match = any(
            reason.startswith(
                "section match:"
            )
            or reason.startswith(
                "phrase match:"
            )
            or reason.startswith(
                "concept match:"
            )
            for reason in candidate_reasons
        )

        keep_candidate = False

        # Same legal section
        if same_section:
            keep_candidate = True

        # Same legal topic + specific match
        elif same_topic and has_specific_match:
            keep_candidate = True

        # No topic/section available
        elif (
            not best_topics
            and not candidate_topics
            and not best_sections
            and not candidate_sections
            and best_score > 0
            and (
                candidate_score / best_score
                >= SECONDARY_SCORE_RATIO
            )
            and has_specific_match
        ):
            keep_candidate = True

        if keep_candidate:

            accepted_ids.add(
                candidate["id"]
            )

        else:

            candidate["_filter_rejected"] = True

            candidate["_filter_rejected_reason"] = (
                "global relevance gate: "
                "different legal provision/topic "
                "or insufficient specific overlap"
            )

    # ========================================================
    # STEP 6: RETURN IN ORIGINAL RERANKER ORDER
    # ========================================================
    #
    # THIS IS THE IMPORTANT FIX.
    #
    # intermediate_results already has the same order as
    # the input `chunks`.
    #
    # The input `chunks` came from reranked_results.
    #
    # Therefore this preserves reranker order.
    # ========================================================

    final_results = []

    for result in intermediate_results:

        if result["id"] not in accepted_ids:
            continue

        result.pop(
            "_filter_best_score",
            None,
        )

        result.pop(
            "_filter_best_unit",
            None,
        )

        result.pop(
            "_original_order",
            None,
        )

        result.pop(
            "_filter_rejected",
            None,
        )

        result.pop(
            "_filter_rejected_reason",
            None,
        )

        final_results.append(
            result
        )

    return final_results

# ============================================================
# DEBUG DISPLAY
# ============================================================

def print_debug_result(
    result: Dict[str, Any]
) -> None:
    """
    Print a detailed debugging report.
    """

    print("\n")
    print("=" * 80)
    print("LEGAL CONTEXT FILTER DEBUG")
    print("=" * 80)

    print("\nQUESTION:")
    print(result["question"])

    print("\nQUERY INFORMATION:")
    print("-" * 80)
    print("Sections:", result["query_info"]["sections"])
    print("Topics:", result["query_info"]["topics"])
    print("Concepts:", result["query_info"]["concepts"])
    print("Phrases:", result["query_info"]["phrases"])

    print("\nTOTAL LOGICAL UNITS:")
    print(result["total_units"])

    print("\nRANKED UNITS:")
    print("-" * 80)

    for index, unit in enumerate(
        result["units"],
        start=1,
    ):

        print(
            f"\nUNIT {index}"
        )

        print(
            f"SCORE: {unit['score']}"
        )

        print(
            "SECTIONS:",
            unit["sections"]
        )

        print(
            "TOPICS:",
            unit["topics"]
        )

        print(
            "MATCHING TOPICS:",
            unit["matching_topics"]
        )

        print(
            "COMPETING TOPICS:",
            unit["competing_topics"]
        )

        print(
            "REASONS:"
        )

        for reason in unit["reasons"]:
            print(
                f"  - {reason}"
            )

        if "rejected_reason" in unit:

            print(
                "REJECTED:",
                unit["rejected_reason"]
            )

        print("\nTEXT:")
        print(unit["text"])

    print("\n")
    print("=" * 80)
    print("SELECTED UNITS")
    print("=" * 80)

    for index, unit in enumerate(
        result["selected_units"],
        start=1,
    ):

        print(
            f"\nSELECTED UNIT {index}"
        )

        print(
            f"SCORE: {unit['score']}"
        )

        print(
            "TOPICS:",
            unit["topics"]
        )

        print(
            "SECTIONS:",
            unit["sections"]
        )

        print(unit["text"])

    print("\n")
    print("=" * 80)
    print("FINAL CLEAN CONTEXT")
    print("=" * 80)

    print(
        result["clean_context"]
    )

    print("\n")
