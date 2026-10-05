import re

from sentence_transformers import CrossEncoder


# ============================================================
# CROSS ENCODER MODEL
# ============================================================

model = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L4-v2"
)


# ============================================================
# EXTRACT SECTION NUMBERS
# ============================================================

def extract_sections(text: str):

    if not text:
        return set()

    matches = re.findall(
        r"\bsections?\s+(\d+[A-Za-z]?)",
        text,
        flags=re.IGNORECASE
    )

    return {
        match.lower()
        for match in matches
    }


# ============================================================
# DEBUG: IMPORTANT QUERY TERMS
# ============================================================

DEBUG_TERMS = [

    "red herring prospectus",

    "filing",
    "file",
    "registrar",

    "subscription list",

    "offer",
    "offer of securities",

    "opening",

    "timeline",
    "time-frame",
    "time frame",

    "three days",

    "public offer",

    "legal consequence",

]


# ============================================================
# DEBUG TERM MATCHING
# ============================================================

def find_matching_terms(query: str, text: str):

    query_lower = query.lower()
    text_lower = text.lower()

    query_terms = []
    matched_terms = []

    for term in DEBUG_TERMS:

        if term in query_lower:

            query_terms.append(term)

            if term in text_lower:

                matched_terms.append(term)

    return query_terms, matched_terms


# ============================================================
# RERANK
# ============================================================

def rerank(query: str, results: list):

    if not results:

        return []

    print("\n")
    print("============================================================")
    print("                 RERANK DEBUGGING")
    print("============================================================")

    print("\nQUERY:")
    print(query)

    # ========================================================
    # QUERY SECTION DEBUG
    # ========================================================

    query_sections = extract_sections(query)

    print("\n========== QUERY SECTION DEBUG ==========")

    print(
        "QUERY SECTIONS:",
        query_sections
    )

    # ========================================================
    # QUERY TERM DEBUG
    # ========================================================

    query_terms = []

    for term in DEBUG_TERMS:

        if term in query.lower():

            query_terms.append(term)

    print("\n========== QUERY TERM DEBUG ==========")

    print(
        "TERMS FOUND IN QUERY:"
    )

    for term in query_terms:

        print(
            "  ✓",
            term
        )

    if not query_terms:

        print(
            "  No DEBUG_TERMS found in query."
        )

    # ========================================================
    # CROSS ENCODER
    # ========================================================

    print("\n========== CROSSENCODER ==========")

    pairs = [
        (query, result["text"])
        for result in results
    ]

    scores = model.predict(pairs)

    print(
        "CrossEncoder evaluated:",
        len(scores),
        "documents"
    )

    # ========================================================
    # ANALYZE EVERY RESULT
    # ========================================================

    for result, score in zip(results, scores):

        rerank_score = float(score)

        document_text = result["text"]

        document_sections = extract_sections(
            document_text
        )

        # ----------------------------------------------------
        # SECTION MATCH
        # ----------------------------------------------------

        section_match = bool(
            query_sections.intersection(
                document_sections
            )
        )

        # ----------------------------------------------------
        # TERM MATCHING
        # ----------------------------------------------------

        query_terms_found, matched_terms = find_matching_terms(
            query,
            document_text
        )

        # ----------------------------------------------------
        # DEBUG ONLY
        #
        # DO NOT CHANGE THE ACTUAL SCORE
        # ----------------------------------------------------

        print("\n------------------------------------------------------------")

        print(
            "ID:",
            result["id"]
        )

        print(
            "PAGE:",
            result.get("page_number")
        )

        print(
            "RERANK SCORE:",
            rerank_score
        )

        print(
            "SECTION MATCH:",
            section_match
        )

        print(
            "DOCUMENT SECTIONS:",
            document_sections
        )

        print(
            "QUERY TERMS:",
            query_terms_found
        )

        print(
            "MATCHED TERMS:",
            matched_terms
        )

        print(
            "MATCH COUNT:",
            len(matched_terms)
        )

        print(
            "\nDOCUMENT TEXT:"
        )

        print(
            document_text[:800]
        )

    # ========================================================
    # CURRENT RANKING
    #
    # IMPORTANT:
    # This keeps your ORIGINAL ranking logic.
    # ========================================================

    for result, score in zip(results, scores):

        rerank_score = float(score)

        document_text = result["text"]

        document_sections = extract_sections(
            document_text
        )

        # ----------------------------------------------------
        # SECTION MATCH
        # ----------------------------------------------------

        section_match = bool(
            query_sections.intersection(
                document_sections
            )
        )

        # ----------------------------------------------------
        # YOUR CURRENT BONUS
        # ----------------------------------------------------

        section_bonus = 0.0

        if section_match:

            section_bonus = 3.0

        final_score = (
            rerank_score
            + section_bonus
        )

        # ----------------------------------------------------
        # SAVE VALUES
        # ----------------------------------------------------

        result["rerank_score"] = rerank_score

        result["section_match"] = section_match

        result["section_bonus"] = section_bonus

        result["final_score"] = final_score
    # ========================================================
    # SORT
    # ========================================================

    results.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    # ========================================================
    # FINAL DEBUG
    # ========================================================

    print("\n")
    print("============================================================")
    print("                 FINAL DEBUG RANKING")
    print("============================================================")

    for i, result in enumerate(
        results[:15],
        start=1
    ):

        print(
            f"\nRANK: {i}"
        )

        print(
            "ID:",
            result["id"]
        )

        print(
            "PAGE:",
            result.get("page_number")
        )

        print(
            "RERANK SCORE:",
            result.get("rerank_score")
        )

        print(
            "SECTION MATCH:",
            result.get("section_match")
        )

        print(
            "SECTION BONUS:",
            result.get("section_bonus")
        )

        print(
            "FINAL SCORE:",
            result.get("final_score")
        )

        print(
            "TEXT:",
            result["text"][:500]
        )

        print("--------------------------------------------")

    print("\n")
    print("============================================================")
    print("              END RERANK DEBUGGING")
    print("============================================================")

    return results