
import os

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
    """
    Generate an answer using ONLY the supplied ICAI material.

    Important:
    - No outside knowledge
    - No guessing
    - No unsupported conclusions
    - Preserve qualifications and exceptions
    - Answer only what the user asks
    """

    # ==================================================
    # 1. Limit conversation history
    # ==================================================

    if history:
        history_lines = history.splitlines()

        # Keep only the latest 6 lines
        history = "\n".join(history_lines[-4:])
    else:
        history = "No previous conversation."


    # ==================================================
    # 2. Build strict prompt
    # ==================================================

    prompt = f"""
You are a CA academic assistant.

Answer the user's question using ONLY the ICAI study material provided below.

Your job is to explain the material clearly and naturally, like a good ChatGPT answer.

Rules:
- Answer exactly what the user asked.
- Use only information present in the ICAI material.
- Do not add outside knowledge.
- Do not invent facts.
- Include important conditions, exceptions and qualifications when they are relevant.
- For a simple question, give a concise answer.
- If the user asks for more detail, explain the same topic in more depth.
- Organize the answer naturally using short headings and numbered points when useful.
- Do not use Markdown.
- Do not use asterisks.
- Do not use Markdown tables.
- Do not use HTML.
- Do not repeat the same information.
- Do not mention the ICAI source or internal RAG system unless necessary.
- If the supplied material is insufficient, say:
"I couldn't find sufficient information in the available ICAI study material."

ICAI STUDY MATERIAL:
{context}

USER QUESTION:
{question}

Return only the final answer.
"""
    # ==================================================
    # 3. Groq request
    # ==================================================

    response = client.chat.completions.create(
        model=MODEL,
        reasoning_effort="low",
        include_reasoning=False,


        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise CA academic assistant. "
                    "Answer the user's question using ONLY the supplied ICAI study material. "
                    "Do not use outside knowledge or unsupported assumptions. "
                    "Preserve qualifications and exceptions. "
                    "Answer exactly what is asked."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0,
        max_tokens=1500
    )


    # ==================================================
    # 4. Get response
    # ==================================================

    answer = response.choices[0].message.content

    import re

    answer = re.sub(r'\*\*', '', answer)
    answer = re.sub(r'(?<!\w)\*(?!\w)', '', answer)
    answer = re.sub(r'<br\s*/?>', '\n', answer, flags=re.IGNORECASE)
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

    if not answer or not answer.strip():

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

