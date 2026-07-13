from typing import List


def search_cases_from_web(query: str) -> List[dict]:
    """
    Placeholder function.

    Later this function will call
    Indian Kanoon / Google / CourtListener etc.
    """

    print(f"[WEB SEARCH] Searching web for: {query}")

    return [
        {
            "title": f"Sample Case for {query}",
            "court": "Unknown Court",
            "citation": "N/A",
            "judge": "Unknown",
            "summary": f"Automatically fetched for '{query}'",
            "full_text": f"This is placeholder judgement text for '{query}'.",
            "source": "Web"
        }
    ]