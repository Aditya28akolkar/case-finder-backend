import os
import re

from dotenv import load_dotenv
from groq import Groq


# ==================================================
# Environment
# ==================================================

load_dotenv()


# ==================================================
# Groq Client
# ==================================================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL = "openai/gpt-oss-20b"


# ==================================================
# Generate CA Answer
# ==================================================

def generate_answer(
    context: str,
    question: str,
    history: str = ""
):

    #debug_llm_context(context)
    """
    Generate a natural CA academic answer using only
    the supplied ICAI study material.

    Goals:
    - ICAI material controls factual content
    - Conversation history controls follow-up meaning
    - Answer only what the user asks
    - Avoid dumping retrieved chunks
    - Give concise, natural ChatGPT-style answers
    """

    # ==================================================
    # 1. Limit conversation history
    # ==================================================

    if history:
        history = history[-1000:]
    else:
        history = "No previous conversation."

    # ==================================================
    # 2. Build prompt
    # ==================================================
    print("\n================ LLM CONTEXT DEBUG ================")
    print(context)
    print("====================================================")
    with open("llm_context_debug.txt", "w", encoding="utf-8") as f:
        f.write(context)


    prompt = f"""You are a precise academic assistant.

STRICT ANSWERING RULES:
- Answer the user's question directly and concisely.
- Use only relevant facts and rules from the supplied context.
- Preserve dates, deadlines, amounts, and conditions accurately.
- For scenario questions, apply the relevant rule to the facts.
- Never invent facts, legal rules, penalties, or consequences.
- Never mention ICAI.
- Do not provide unnecessary explanations or headings.

MIXED LEGAL-CONSEQUENCE QUESTIONS:
- If the question asks for a rule, deadline, or requirement AND also asks about its legal consequence, answer ONLY the rule, deadline, or requirement.
- Completely omit the legal-consequence part.
- Never explain that a consequence is missing, unavailable, unspecified, or not mentioned.
- Do not state that any part of the question was ignored.
- Keep the answer as short as possible without losing the relevant rule or deadline.

CONTEXT:
{context}

CONVERSATION HISTORY:
{history}

QUESTION:
{question}

Return only the final answer."""

    # ==================================================
    # 3. Groq request
    # ==================================================

    print("\n========== TOKEN DEBUG ==========")
    print("History characters:", len(history))
    print("Context characters:", len(context))
    print("Question characters:", len(question))
    print("Prompt characters:", len(prompt))
    print("=================================")

    response = client.chat.completions.create(
        model=MODEL,
        reasoning_effort="low",
        include_reasoning=False,

        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise academic assistant. "
                    "Answer concisely using the supplied context. "
                    "Never mention ICAI. "
                    "If a question asks for a rule, deadline, or requirement "
                    "together with its legal consequence, answer only the "
                    "rule, deadline, or requirement. "
                    "Do not discuss missing or unspecified consequences. "
                    "Never invent facts, rules, or penalties."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],

        temperature=0.0,
        max_tokens=1000
    )

    # ==================================================
    # 4. Get response
    # ==================================================

    answer = response.choices[0].message.content or ""
    answer = answer.strip()

    asks_consequence = bool(
        re.search(
            r"\b(consequence|consequences|penalty|penalties|"
            r"liable|liability|punishment|punishable|fine)\b",
            question,
            re.IGNORECASE,
        )
    )

    asks_rule_or_deadline = bool(
        re.search(
            r"\b(deadline|time limit|timeline|"
            r"requirement|rule|file|filing|"
            r"how many days|within \d+ days)\b",
            question,
            re.IGNORECASE,
        )
    )

    if asks_consequence and asks_rule_or_deadline:
        answer = re.sub(
            r"(?:^|\n)\s*(?:legal consequence|consequence|"
            r"penalty)\s*:\s*.*",
            "",
            answer,
            flags=re.IGNORECASE | re.DOTALL,
        )
        answer = re.sub(
            r"\s*(?:The supplied|The provided|The available|"
            r"The material|The context|The documents|"
            r"The source).{0,250}"
            r"(?:does not specify|doesn't specify|"
            r"does not state|not specified|not mentioned|"
            r"does not contain|not provided).{0,150}"
            r"(?:consequence|penalty|liability|fine|"
            r"punishment|legal effect|information)?"
            r"[^.!?\n]*[.!?]?",
            "",
            answer,
            flags=re.IGNORECASE,
        ).strip()

    answer = enforce_legal_consequence_guard(
        answer=answer,
        question=question,
        context=context,
    )

    # Remove unwanted markdown / HTML formatting.
    answer = re.sub(r"\*\*(.*?)\*\*", r"\1", answer)
    answer = re.sub(r"(?<!\*)\*(?!\*)(.*?)\*(?!\*)", r"\1", answer)
    
    answer = re.sub(
        r'<br\s*/?>',
        '\n',
        answer,
        flags=re.IGNORECASE
    )
    answer = re.sub(r'<[^>]+>', '', answer)

    finish_reason = response.choices[0].finish_reason

    # ==================================================
    # 5. Debug information
    # ==================================================

    print("\n========== GENERATED ANSWER ==========")
    print(repr(answer))
    print("FINISH REASON:", finish_reason)
    print("======================================")

    # ==================================================
    # 6. Empty response protection
    # ==================================================

    if not answer.strip():
        print("\nWARNING: Groq returned an empty answer.")
        print("FINISH REASON:", finish_reason)

        return (
            "I couldn't generate a response at the moment. "
            "Please try asking the question again."
        )

    # ==================================================
    # 7. Return answer
    # ==================================================

    return answer.strip()


def enforce_legal_consequence_guard(
    answer: str,
    question: str,
    context: str,
) -> str:
    """
    Avoid incorrectly declaring a legal consequence unavailable
    when the supplied context contains relevant consequence evidence.

    This guard does not create or infer legal consequences.
    """

    asks_consequence = bool(
        re.search(
            r"\b(consequence|consequences|penalty|penalties|"
            r"liable|liability|punishment|punishable|fine|"
            r"legal effect|what happens|non-compliance|"
            r"non compliance|failure to comply)\b",
            question,
            re.IGNORECASE,
        )
    )

    if not asks_consequence:
        return answer

    if not context or not context.strip():
        return answer

    consequence_terms = re.compile(
        r"\b(penalt(?:y|ies)|liable|liability|"
        r"punish(?:ed|ment|able)?|fines?|imprisonment|"
        r"void|invalid|compensation|prosecution|"
        r"adjudication|offen[cs]e|default|"
        r"shall be liable|shall be punishable)\b",
        re.IGNORECASE,
    )

    # Normalize whitespace and inspect paragraphs independently.
    normalized_context = context.replace("\r\n", "\n")
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", normalized_context)
        if paragraph.strip()
    ]

    # Extract section references from the question, including
    # subsection references such as Section 32(2).
    target_sections = set(
        re.findall(
            r"\bsections?\s+(\d+[A-Za-z]?(?:\s*\(\s*\d+\s*\))?)",
            question,
            re.IGNORECASE,
        )
    )

    target_sections = {
        re.sub(r"\s+", "", section).lower()
        for section in target_sections
    }

    # Explicit language indicating that a provision may rely on
    # a related or general penalty provision.
    cross_reference_terms = re.compile(
        r"\b(general penalty|"
        r"where no penalty is provided|"
        r"where no specific penalty|"
        r"contravention of any provision|"
        r"not otherwise provided|"
        r"not specifically provided|"
        r"subject to the provisions of section|"
        r"under section \d+|"
        r"under sections \d+)\b",
        re.IGNORECASE,
    )

    for paragraph in paragraphs:
        # A consequence must be explicitly present in the source.
        if not consequence_terms.search(paragraph):
            continue

        # Evidence in the same paragraph as the queried provision
        # is relevant enough to prevent a premature fallback.
        normalized_paragraph = re.sub(
            r"\s+", "", paragraph.lower()
        )

        for section in target_sections:
            if section in normalized_paragraph:
                return answer

        # A separately numbered provision may be relevant if the
        # source explicitly identifies a general or cross-referenced
        # penalty rule. This does not establish applicability by itself.
        if cross_reference_terms.search(paragraph):
            return answer

    # Keep the model's answer unchanged.
    # The prompt already instructs the model not to invent
    # legal consequences or repeat fallback statements.
    return answer