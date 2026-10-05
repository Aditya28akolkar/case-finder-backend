import json
import re
from groq import Groq
from app.core.config import GROQ_API_KEY


class QueryUnderstandingService:

    LEGAL_ACRONYMS = {
        "RHP": "Red Herring Prospectus",
        "DRHP": "Draft Red Herring Prospectus",
        "AGM": "Annual General Meeting",
        "EGM": "Extraordinary General Meeting",
        "ROC": "Registrar of Companies",
        "DIN": "Director Identification Number",
        "NCLT": "National Company Law Tribunal",
        "SEBI": "Securities and Exchange Board of India",
        "LODR": "Listing Obligations and Disclosure Requirements",
        "PAS": "Prospectus and Allotment of Securities",
    }

    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)

    def _clean_json_response(self, content: str) -> str:
        if not content:
            return ""

        content = content.strip()

        if content.startswith("```"):
            content = content.replace("```json", "", 1)
            content = content.replace("```", "", 1)
            content = content.strip()

        return content

    def _get_last_user_query(self, history: str) -> str:
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
        """
        Understand the user's current request using the conversation.

        The model decides whether the user is:

        1. Asking a new question
        2. Asking a follow-up question
        3. Asking to reformat/shorten/expand the previous answer

        No hardcoded phrase matching is used.
        """

        previous_user_query = self._get_last_user_query(history)

        prompt = f"""
You are the query-understanding component of an Indian CA academic
question-answering chatbot.

Your job is NOT to answer the user.

Your job is to understand exactly what the user wants and return
structured JSON so another part of the system can answer correctly.

The chatbot uses ICAI study material as its knowledge source.

==================================================
CONVERSATION HISTORY
==================================================

{history if history else "No previous conversation."}

==================================================
CURRENT USER REQUEST
==================================================

{query}

==================================================
YOUR TASK
==================================================

Determine the user's actual request.

There are three main request types:

1. "new_question"

The user is asking a new factual/academic question.

Example:
"What is depreciation under section 32?"

2. "question_follow_up"

The user is asking a new factual question that depends on the
previous conversation.

Example:

Previous:
USER: What is depreciation under section 32?
ASSISTANT: ...

Current:
"What is the rate?"

The current request should be converted into a complete standalone
search query.

3. "format_follow_up"

The user is NOT asking for new information.

Instead, the user wants the previous answer changed in some way.

This can include ANY wording, such as:

"give me in 5 points"
"make this shorter"
"explain this simply"
"write this as a paragraph"
"give me 250 words"
"make it exam friendly"
"explain in detail"
"remove unnecessary information"
"make it easier to understand"
"give me the key points"
"convert this into a table"
"write this in simple language"
"make this concise"
"expand this"
"compare these"
"put this in a better format"

Do NOT depend on exact phrases.

Understand the meaning of the request from the conversation.

==================================================
IMPORTANT DISTINCTION
==================================================

If the user is asking for NEW INFORMATION, classify it as:

"new_question" or "question_follow_up"

If the user is asking to CHANGE the previous answer without
requesting new factual information, classify it as:

"format_follow_up"

For example:

Previous question:
"What are the provisions for depreciation of intangible assets?"

Current:
"give me in 5 points"

=> format_follow_up

Current:
"give me in paragraph in 250 words"

=> format_follow_up

Current:
"explain this in simple language"

=> format_follow_up

Current:
"What is the rate for intangible assets?"

=> question_follow_up

Current:
"What is additional depreciation?"

=> new_question

==================================================
FORMAT INSTRUCTIONS
==================================================

If request_type is "format_follow_up", identify the user's
requested transformation.

Use "format" for the general format.

Possible values include:

"points"
"paragraph"
"short"
"summary"
"detailed"
"simple"
"table"
"comparison"
"exam"
"other"

If the request does not fit one of these, use "other".

Extract a number of points if requested.

Examples:

"give me in 5 points"
point_count = 5

"make it 3 bullet points"
point_count = 3

If no number is requested:
point_count = null

Extract a word limit if requested.

Examples:

"give me in 250 words"
word_count = 250

"write it in around 100 words"
word_count = 100

If no word count is requested:
word_count = null

Also create "format_instruction".

This must describe exactly what the user wants the answer
formatter to do.

Example:

User:
"give me in paragraph in 250 words"

format_instruction:
"Rewrite the previous answer as one clear paragraph of about
250 words. Preserve the important facts, conditions and
qualifications."

Another example:

User:
"make this simple"

format_instruction:
"Rewrite the previous answer in simple, easy-to-understand
language without changing the meaning or adding new facts."

Another:

User:
"give me in 5 points"

format_instruction:
"Rewrite the previous answer into exactly 5 clear points.
Preserve the important facts, conditions and qualifications."

==================================================
SEARCH QUERY
==================================================

For "new_question":

expanded_query should normally be the current user question.

For "question_follow_up":

Use the conversation history to resolve references such as:

this
that
it
the rate
the limit
the section
the provision
the above
then
what about this
and similar references.

Create a complete standalone search query.

For "format_follow_up":

expanded_query should be the previous substantive user question
when available.

Do NOT turn a formatting request itself into a knowledge search
query.



        ==================================================
        SCENARIO / APPLICATION QUESTIONS
        ==================================================

        Some users do not ask a simple factual question.

        They may provide a hypothetical case, situation, facts,
        dates, amounts, conditions, transactions, actions, or
        decisions and then ask whether a legal requirement was
        complied with or what legal rule applies.

        These are SCENARIO / APPLICATION questions.

        Examples include:

        "A company filed the prospectus two days before the
        subscription opened. Was this valid?"

        "A company appointed a director without giving the required
        notice. Is the appointment compliant?"

        "A taxpayer sold an asset after holding it for 18 months.
        How should the transaction be treated?"

        "Company A borrowed Rs. 50 lakh and the applicable limit
        is based on paid-up capital. Does the transaction comply?"

        A scenario question may contain:

        - Names of people or companies
        - Dates
        - Amounts
        - Time periods
        - Percentages
        - Transactions
        - Actions already taken
        - Conditions
        - Multiple facts
        - A legal provision or section
        - A question asking whether something is compliant,
          valid, permitted, prohibited, or liable to a consequence

        IMPORTANT:

        Separate the user's FACTS from the LEGAL RULE.

        The user's facts are NOT the legal rule.

        The legal rule must be identified from the user's question
        and legal context, without inventing any provision.

        --------------------------------------------------
        SCENARIO FIELDS
        --------------------------------------------------

        "is_scenario":

        Return true when the user provides facts or a hypothetical
        situation and asks you to APPLY a legal/accounting/tax rule
        to those facts.

        Return false for a normal direct factual question.

        --------------------------------------------------

        "scenario_facts":

        Extract the important facts supplied by the user.

        Preserve dates, numbers, amounts, names, periods,
        conditions and actions.

        Do NOT invent facts.

        Do NOT convert facts into legal conclusions.

        Example:

        User:

        "Zenith Ltd. files the RHP on Tuesday 9th and the
        subscription list opens on Friday 12th."

        scenario_facts:

        [
            "Zenith Ltd. files the RHP on Tuesday, 9th.",
            "The subscription list opens on Friday, 12th."
        ]

        --------------------------------------------------

        "legal_issue":

        Identify the exact legal issue that must be answered.

        Do NOT answer the issue.

        Example:

        "Whether the Red Herring Prospectus was filed with the
        Registrar within the required period before the opening
        of the subscription list and public offer."

        --------------------------------------------------

        "legal_retrieval_query":

        Create a concise search query containing ONLY the legal
        concepts needed to find the applicable rule in the ICAI
        knowledge base.

        Do NOT include scenario-specific names.

        Do NOT include irrelevant facts.

        Do NOT include the conclusion.

        Do NOT invent a section number.

        Include important legal terminology, provisions, concepts,
        requirements, limits, periods or conditions when they are
        actually present in the user's question.

        Example:

        User scenario:

        "Zenith Ltd. files the RHP on Tuesday 9th and the
        subscription list opens on Friday 12th. Did it comply?"

        Good legal_retrieval_query:

        "Red Herring Prospectus filing with Registrar minimum
        period before opening of subscription list and public offer"

        Bad legal_retrieval_query:

        "Zenith Ltd filed on Tuesday 9th and opened Friday 12th,
        therefore it complied"

        The first query searches for the LEGAL RULE.

        The second query incorrectly searches using the user's
        FACTS as if they were legal terminology.

        --------------------------------------------------

        For a normal non-scenario question:

        "is_scenario" = false

        "scenario_facts" = []

        "legal_issue" = ""

        "legal_retrieval_query" should normally contain the
        legal/academic search query.

        --------------------------------------------------

        For a scenario question:

        "is_scenario" = true

        "scenario_facts" = important facts from the user

        "legal_issue" = the legal question that must be resolved

        "legal_retrieval_query" = legal concepts/rule needed
        to answer the question

        "expanded_query" should still represent the complete
        standalone user question.

        Do NOT remove the scenario facts from expanded_query.

        ==================================================



==================================================
DO NOT INVENT INFORMATION
==================================================






Do not invent:

- sections
- rates
- limits
- legal provisions
- topics
- facts
- user intentions

Only use the conversation to resolve context.

==================================================
RETURN ONLY JSON
==================================================

Return exactly this structure:

         {{
            "request_type": "",
            "format": null,
            "point_count": null,
            "word_count": null,
            "format_instruction": "",
            "legal_domain": "",
            "section": "",
            "topic": "",
            "entities": [],
            "keywords": [],
            "jurisdiction": "India",
            "intent": "",
            "is_scenario": false,
            "scenario_facts": [],
            "legal_issue": "",
            "legal_retrieval_query": "",
            "expanded_query": ""
        }}

No Markdown.
No explanation.
No code fences.

==================================================
EXAMPLES
==================================================

Example 1

Current:
"What is depreciation under section 32?"

Return:

{{
    "request_type": "new_question",
    "format": null,
    "point_count": null,
    "word_count": null,
    "format_instruction": "",
    "legal_domain": "Income Tax",
    "section": "32",
    "topic": "Depreciation",
    "entities": [],
    "keywords": ["depreciation", "section 32"],
    "jurisdiction": "India",
    "intent": "explanation",
    "expanded_query": "What is depreciation under section 32?"
}}

Example 2

Previous question:
"What is depreciation under section 32?"

Current:
"What is the rate?"

Return:

{{
    "request_type": "question_follow_up",
    "format": null,
    "point_count": null,
    "word_count": null,
    "format_instruction": "",
    "legal_domain": "Income Tax",
    "section": "32",
    "topic": "Depreciation",
    "entities": [],
    "keywords": ["depreciation", "rate", "section 32"],
    "jurisdiction": "India",
    "intent": "factual",
    "expanded_query": "What is the depreciation rate under section 32?"
}}

Example 3

Previous question:
"What are the provisions for depreciation of intangible assets?"

Current:
"give me in 5 points"

Return:

{{
    "request_type": "format_follow_up",
    "format": "points",
    "point_count": 5,
    "word_count": null,
    "format_instruction": "Rewrite the previous answer into exactly 5 clear points. Preserve the important facts, conditions and qualifications.",
    "legal_domain": "",
    "section": "",
    "topic": "",
    "entities": [],
    "keywords": [],
    "jurisdiction": "India",
    "intent": "format_previous_answer",
    "expanded_query": "What are the provisions for depreciation of intangible assets?"
}}

Example 4

Previous question:
"What are the provisions for depreciation of intangible assets?"

Current:
"give me in paragraph in 250 words"

Return:

{{
    "request_type": "format_follow_up",
    "format": "paragraph",
    "point_count": null,
    "word_count": 250,
    "format_instruction": "Rewrite the previous answer as one clear paragraph of about 250 words. Preserve the important facts, conditions and qualifications.",
    "legal_domain": "",
    "section": "",
    "topic": "",
    "entities": [],
    "keywords": [],
    "jurisdiction": "India",
    "intent": "format_previous_answer",
    "expanded_query": "What are the provisions for depreciation of intangible assets?"
}}

Example 5

Previous question:
"What is depreciation?"

Current:
"explain this in simple language"

Return:

{{
    "request_type": "format_follow_up",
    "format": "simple",
    "point_count": null,
    "word_count": null,
    "format_instruction": "Rewrite the previous answer in simple, easy-to-understand language while preserving the original meaning and important qualifications.",
    "legal_domain": "",
    "section": "",
    "topic": "",
    "entities": [],
    "keywords": [],
    "jurisdiction": "India",
    "intent": "format_previous_answer",
    "expanded_query": "What is depreciation?"
}}


        Example 6

        Current:

        "Zenith Ltd. decides to issue a Red Herring Prospectus.
        The subscription list and public offer open on Friday,
        12th of the month. Zenith files the RHP with the Registrar
        on Tuesday, 9th. Did Zenith comply with the filing
        requirement?"

        Return:

        {{
            "request_type": "new_question",
            "format": null,
            "point_count": null,
            "word_count": null,
            "format_instruction": "",
            "legal_domain": "Corporate and Other Laws",
            "section": "32",
            "topic": "Red Herring Prospectus",
            "entities": ["Zenith Ltd."],
            "keywords": [
                "Red Herring Prospectus",
                "RHP",
                "Registrar",
                "subscription list",
                "public offer",
                "filing"
            ],
            "jurisdiction": "India",
            "intent": "application",

            "is_scenario": true,

            "scenario_facts": [
                "Zenith Ltd. decides to issue a Red Herring Prospectus.",
                "The subscription list and public offer open on Friday, 12th.",
                "Zenith Ltd. files the RHP with the Registrar on Tuesday, 9th."
            ],

            "legal_issue": "Whether the Red Herring Prospectus was filed with the Registrar within the required period before the opening of the subscription list and public offer.",

            "legal_retrieval_query": "Red Herring Prospectus filing with Registrar minimum period before opening of subscription list and public offer",

            "expanded_query": "Zenith Ltd. decides to issue a Red Herring Prospectus. The subscription list and public offer open on Friday, 12th of the month. Zenith Ltd. files the RHP with the Registrar on Tuesday, 9th. Did Zenith comply with the filing requirement?"
        }}


==================================================
CONVERSATION
==================================================

{history if history else "No previous conversation."}

==================================================
CURRENT REQUEST
==================================================

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
                        "You are a precise query-understanding "
                        "assistant for a CA academic chatbot. "
                        "Understand the user's intent from context. "
                        "Return only valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=800
        )

        print("\n========== QUERY UNDERSTANDING DEBUG ==========")
        print("\nCURRENT QUERY:")
        print(query)
        print("\nHISTORY:")
        print(history)
        print("\nFINISH REASON:")
        print(response.choices[0].finish_reason)
        print("\nRAW RESPONSE:")
        print(repr(response.choices[0].message.content))
        print("===============================================")

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise ValueError(
                "Groq returned an empty query-understanding response. "
                f"Finish reason: {response.choices[0].finish_reason}"
            )

        content = self._clean_json_response(content)

        try:
            analysis = json.loads(content)
        except json.JSONDecodeError as e:
            print("\n========== INVALID JSON ==========")
            print(content)
            print("==================================")
            raise ValueError(
                "Groq returned invalid JSON for query understanding."
            ) from e

        if not isinstance(analysis, dict):
            raise ValueError(
                "Query understanding response must be a JSON object."
            )

        # ============================================================
        # SAFE DEFAULTS FOR SCENARIO FIELDS
        # ============================================================

        analysis.setdefault("is_scenario", False)
        analysis.setdefault("scenario_facts", [])
        analysis.setdefault("legal_issue", "")
        analysis.setdefault("legal_retrieval_query", "")

        required_fields = [
            "request_type",
            "format",
            "point_count",
            "word_count",
            "format_instruction",
            "legal_domain",
            "section",
            "topic",
            "entities",
            "keywords",
            "jurisdiction",
            "intent",
            "is_scenario",
            "scenario_facts",
            "legal_issue",
            "legal_retrieval_query",
            "expanded_query"
        ]
        for field in required_fields:
            if field not in analysis:
                raise ValueError(
                    f"Query understanding JSON is missing field: {field}"
                )

        valid_request_types = {
            "new_question",
            "question_follow_up",
            "format_follow_up"
        }

        if analysis["request_type"] not in valid_request_types:
            raise ValueError(
                f"Invalid request_type: {analysis['request_type']}"
            )

        if not isinstance(
            analysis["expanded_query"],
            str
        ) or not analysis["expanded_query"].strip():
            raise ValueError(
                "Query understanding returned an empty expanded_query."
            )
        # ============================================================
        # SCENARIO FIELD VALIDATION
        # ============================================================

        if not isinstance(
            analysis["is_scenario"],
            bool
        ):
            raise ValueError(
                "Query understanding 'is_scenario' must be a boolean."
            )

        if not isinstance(
            analysis["scenario_facts"],
            list
        ):
            raise ValueError(
                "Query understanding 'scenario_facts' must be a list."
            )

        if not isinstance(
            analysis["legal_issue"],
            str
        ):
            raise ValueError(
                "Query understanding 'legal_issue' must be a string."
            )

        if not isinstance(
            analysis["legal_retrieval_query"],
            str
        ):
            raise ValueError(
                "Query understanding 'legal_retrieval_query' must be a string."
            )

        # Scenario questions must have a legal retrieval query.
        if analysis["is_scenario"]:

            if not analysis["scenario_facts"]:
                raise ValueError(
                    "Scenario question must contain scenario_facts."
                )

            if not analysis["legal_issue"].strip():
                raise ValueError(
                    "Scenario question must contain legal_issue."
                )

            if not analysis["legal_retrieval_query"].strip():
                raise ValueError(
                    "Scenario question must contain legal_retrieval_query."
                )

        print("\n========== FINAL QUERY ANALYSIS ==========")
        print(json.dumps(
            analysis,
            indent=2,
            ensure_ascii=False
        ))
        print("===========================================\n")

        # ============================================================
        # DETERMINISTIC CA LEGAL TERM NORMALIZATION
        # ============================================================

        # 1. EXPAND LEGAL ACRONYMS
        expanded_query = analysis.get("expanded_query") or query

        for acronym, full_form in self.LEGAL_ACRONYMS.items():
            expanded_query = re.sub(
                rf"\ban\s+{re.escape(acronym)}\b",
                f"a {full_form} ({acronym})",
                expanded_query,
                flags=re.IGNORECASE
            )
            expanded_query = re.sub(
                rf"\ba\s+{re.escape(acronym)}\b",
                f"a {full_form} ({acronym})",
                expanded_query,
                flags=re.IGNORECASE
            )
            if not re.search(
                rf"{re.escape(full_form)}\s*\({re.escape(acronym)}\)",
                expanded_query,
                flags=re.IGNORECASE
            ):
                expanded_query = re.sub(
                    rf"\b{re.escape(acronym)}\b",
                    f"{full_form} ({acronym})",
                    expanded_query,
                    flags=re.IGNORECASE
                )

        analysis["expanded_query"] = expanded_query

        # 2. DETERMINISTIC LEGAL DOMAIN DETECTION
        query_lower = query.lower()

        corporate_law_terms = [
            "rhp",
            "red herring prospectus",
            "drhp",
            "prospectus",
            "private placement",
            "rights issue",
            "bonus issue",
            "share capital",
            "shares",
            "debentures",
            "director",
            "directors",
            "company",
            "companies act",
            "incorporation",
            "memorandum of association",
            "articles of association",
            "agm",
            "annual general meeting",
            "egm",
            "extraordinary general meeting",
            "roc",
            "registrar of companies",
            "nclt",
            "board meeting",
            "securities",
            "allotment",
            "subscription list",
        ]

        if any(term in query_lower for term in corporate_law_terms):
            analysis["legal_domain"] = "Corporate and Other Laws"

        # 3. DETERMINISTIC KEYWORD NORMALIZATION
        keywords = analysis.get("keywords") or []

        for acronym, full_form in self.LEGAL_ACRONYMS.items():
            if acronym.lower() in query_lower:
                if full_form.lower() not in [str(k).lower() for k in keywords]:
                    keywords.append(full_form)
                if acronym.lower() not in [str(k).lower() for k in keywords]:
                    keywords.append(acronym)

        if "rhp" in query_lower or "red herring prospectus" in query_lower:
            required_keywords = [
                "red herring prospectus",
                "RHP",
                "subscription list",
                "filing",
            ]
            for keyword in required_keywords:
                if keyword.lower() not in [str(k).lower() for k in keywords]:
                    keywords.append(keyword)

        analysis["keywords"] = keywords

        # 4. TOPIC NORMALIZATION
        if "rhp" in query_lower or "red herring prospectus" in query_lower:
            analysis["topic"] = "Red Herring Prospectus subscription list"

        print("\n========== FINAL NORMALIZED QUERY ANALYSIS ==========")
        print(json.dumps(analysis, indent=2, ensure_ascii=False))
        print("=====================================================\n")

        return analysis