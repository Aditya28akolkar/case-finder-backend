import json

from groq import Groq
from app.core.config import GROQ_API_KEY


class QueryUnderstandingService:

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def _is_follow_up_query(self, query: str, history: str = "") -> bool:
        """
        Decide whether the query needs conversation history.

        Simple standalone questions do not need an extra Groq call.
        Follow-up questions still use Query Understanding.
        """

        if not history:
            return False

        query_lower = query.lower().strip()

        follow_up_patterns = [
            "what about",
            "how about",
            "and what about",
            "what is the rate",
            "what's the rate",
            "what is its rate",
            "what is the limit",
            "what's the limit",
            "what about the limit",
            "what about the rate",
            "explain this",
            "explain that",
            "tell me more",
            "why?",
            "why",
            "then what",
            "what then",
            "and then",
            "this section",
            "that section",
            "this provision",
            "that provision",
            "this rule",
            "that rule",
            "this case",
            "that case",
            "give me in more detail",
            "explain in more detail",
            "more detail",
            "elaborate",
            "explain more"
        ]

        for pattern in follow_up_patterns:
            if pattern in query_lower:
                return True
        return False

        # # Very short questions are often follow-ups.
        # words = query_lower.split()

        # if len(words) <= 5:
        #     return True

        # return False
    def _get_previous_user_query(self, history: str) -> str:
        if not history:
            return ""

        lines = history.splitlines()

        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()

            if line.lower().startswith("user:"):
                query = line.split(":", 1)[1].strip()

                if query:
                    return query

        return ""






    def analyze_query(
        self,
        query: str,
        history: str = ""
    ):

        # ==================================================
        # FAST PATH
        # ==================================================
        # If this is a standalone question, don't call Groq.
        # This saves one LLM API call and reduces response time.
        # ==================================================
        query_lower = query.lower().strip()

        generic_followups = {
            "give me in more detail",
            "give me more detail",
            "explain more",
            "explain this",
            "tell me more",
            "more detail",
            "more details",
            "elaborate",
            "explain in more detail",
            "give more details",
            "give me more information",
        }
        print("\n========== FOLLOW-UP DEBUG ==========")
        print("CURRENT QUERY:", query)
        print("HISTORY:")
        print(repr(history))
        print("=====================================\n")

        if query_lower in generic_followups:
            




            previous_query = self._get_previous_user_query(history)

            if previous_query:
                return {
                    "legal_domain": "",
                    "section": "",
                    "topic": "",
                    "entities": [],
                    "keywords": [],
                    "jurisdiction": "India",
                    "intent": "detailed explanation",
                    "expanded_query": (
                        f"{previous_query}. "
                        f"Provide a more detailed explanation based only on the ICAI study material."
                    )
                }





        if not self._is_follow_up_query(query, history):

            print("\n========== QUERY UNDERSTANDING ==========")
            print("Standalone query detected.")
            print("Skipping Groq query understanding.")
            print("=========================================\n")

            return {
                "legal_domain": "",
                "section": "",
                "topic": "",
                "entities": [],
                "keywords": query.split(),
                "jurisdiction": "India",
                "intent": "",
                "expanded_query": query
            }

        # ==================================================
        # FOLLOW-UP QUERY
        # ==================================================
        # Only follow-up questions come here.
        # Groq is used to understand the conversation context.
        # ==================================================

        prompt = f"""
You are a query-understanding assistant for an Indian CA academic chatbot.

Convert the CURRENT USER QUERY into a standalone search query for retrieving relevant ICAI study material.

Use conversation history ONLY to resolve missing context or follow-up references.

Rules:
1. Identify the legal/tax domain when possible.
2. Identify the section number when mentioned or clearly established by history.
3. Identify the main topic.
4. Resolve follow-up references using conversation history when necessary.
5. Expand abbreviations such as "sec" to "section" and "u/s" to "under section".
6. Make expanded_query a complete, standalone search query.
7. Do not add unnecessary information from history.
8. Do not invent facts.
9. Do not answer the question.
10. Return ONLY valid JSON.
11. Do not use Markdown or code fences.

Example:

History:
USER: What is depreciation under section 32?
ASSISTANT: Section 32 deals with depreciation.

Current Query:
What is the rate?

Expanded Query:
What is the depreciation rate under section 32 of the Income Tax Act?

Required JSON:
{{
    "legal_domain": "",
    "section": "",
    "topic": "",
    "entities": [],
    "keywords": [],
    "jurisdiction": "India",
    "intent": "",
    "expanded_query": ""
}}

Conversation History:
{history}

Current User Query:
{query}
"""

        response = self.client.chat.completions.create(
            model="openai/gpt-oss-20b",
            reasoning_effort="low",
            include_reasoning=False,




            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise CA query-understanding "
                        "assistant. Return only valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=500,
            
        )

        # ==================================================
        # DEBUG GROQ RESPONSE
        # ==================================================

        print("\n========== QUERY UNDERSTANDING DEBUG ==========")

        print("\nFinish reason:")
        print(response.choices[0].finish_reason)

        print("\nRaw content:")
        print(repr(response.choices[0].message.content))

        print("===============================================")

        # ==================================================
        # GET CONTENT
        # ==================================================

        content = response.choices[0].message.content

        if not content or not content.strip():

            raise ValueError(
                "Groq returned an empty response. "
                f"Finish reason: {response.choices[0].finish_reason}"
            )

        content = content.strip()

        # ==================================================
        # REMOVE MARKDOWN CODE FENCES
        # ==================================================

        if content.startswith("```"):
            content = content.replace("```json", "", 1)
            content = content.replace("```", "", 1)
            content = content.strip()

        # ==================================================
        # PARSE JSON
        # ==================================================

        try:
            analysis = json.loads(content)

        except json.JSONDecodeError as e:

            print("\n========== INVALID JSON ==========")
            print(content)
            print("==================================")

            raise ValueError(
                "Groq returned invalid or incomplete JSON."
            ) from e

        # ==================================================
        # VALIDATE JSON STRUCTURE
        # ==================================================

        if not isinstance(analysis, dict):

            raise ValueError(
                "Query understanding response must be a JSON object."
            )

        required_fields = [
            "legal_domain",
            "section",
            "topic",
            "entities",
            "keywords",
            "jurisdiction",
            "intent",
            "expanded_query"
        ]

        for field in required_fields:

            if field not in analysis:
                raise ValueError(
                    f"Query understanding JSON is missing field: {field}"
                )

        # ==================================================
        # VALIDATE EXPANDED QUERY
        # ==================================================

        if not isinstance(
            analysis["expanded_query"],
            str
        ) or not analysis["expanded_query"].strip():

            raise ValueError(
                "Query understanding returned an empty expanded_query."
            )

        return analysis