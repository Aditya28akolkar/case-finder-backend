from sentence_transformers import CrossEncoder

from sqlalchemy.orm import Session

from app.models.knowledge_document_model import KnowledgeDocument
from app.embeddings.embedding_service import generate_embedding


# ============================================================
# MODELS
# ============================================================

RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


print("Loading reranker...")

reranker = CrossEncoder(
    RERANKER_MODEL,
    device="cpu"
)

# ============================================================
# SEARCH KNOWLEDGE
# ============================================================

def search_knowledge(
    db: Session,
    question: str,
    query_analysis: dict = None,
    top_k: int = 3
):

    print("\n========================================")
    print("KNOWLEDGE SEARCH")
    print("========================================")

    print("QUESTION:", question)


    # ========================================================
    # 1. QUERY UNDERSTANDING INFORMATION
    # ========================================================

    section = None
    topic = None

    if query_analysis:

        section = query_analysis.get("section")
        topic = query_analysis.get("topic")


    print("\n========== QUERY FILTER INFORMATION ==========")
    print("SECTION:", section)
    print("TOPIC:", topic)
    print("==============================================")


    # ========================================================
    # 2. GENERATE QUERY EMBEDDING
    # ========================================================

    print("\n========== QUERY EMBEDDING ==========")

    question_embedding = generate_embedding(question)

    # ========================================================
    # 3. PGVECTOR SEMANTIC SEARCH
    # ========================================================

    print("\n========== PGVECTOR SEARCH ==========")

    # Only retrieve the closest 25 documents from PostgreSQL.
    #
    # IMPORTANT:
    # We are NOT loading all 10,452 documents anymore.
    #
    # PostgreSQL + pgvector calculates the similarity
    # directly inside the database.

    semantic_limit = 20

    query = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.embedding.isnot(None)
        )
        .order_by(
            KnowledgeDocument.embedding.cosine_distance(
                question_embedding
            )
        )
        .limit(semantic_limit)
    )

    documents = query.all()


    print(
        "Semantic candidates:",
        len(documents)
    )


    if not documents:
        print("No documents found.")
        return []


    # ========================================================
    # 4. BUILD RESULTS
    # ========================================================

    results = []


    for document in documents:

        results.append({

            "id": document.id,

            "file_name": document.file_name,

            "subject": document.subject,

            "module": document.module,

            "chapter": document.chapter,

            "page_number": document.page_number,

            "content": document.content,

            "source": document.source

        })


    # ========================================================
    # 5. CROSS ENCODER RERANKING
    # ========================================================

    print("\n========== RERANKING ==========")

    pairs = [

        [
            question,
            candidate["content"]
        ]

        for candidate in results
    ]


    rerank_scores = reranker.predict(
        pairs,
        show_progress_bar=False
    )


    for candidate, score in zip(
        results,
        rerank_scores
    ):

        candidate["rerank_score"] = float(score)


    # ========================================================
    # 6. SORT BY RERANK SCORE
    # ========================================================

    results.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    # ========================================================
    # 7. SORT RESULTS
    # ========================================================

    results.sort(
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    # ========================================================
    # 8. REMOVE DUPLICATES
    # ========================================================

    unique_results = []

    seen_content = set()


    for result in results:

        content = result["content"].strip()


        if content in seen_content:

            continue


        seen_content.add(content)

        unique_results.append(result)


    # ========================================================
    # 9. TOP RESULTS
    # ========================================================

    top_results = unique_results[:top_k]


    # ========================================================
    # 10. DEBUG
    # ========================================================

    print("\n========== TOP RERANKED CHUNKS ==========")


    for i, result in enumerate(
        top_results,
        start=1
    ):

        print(
            f"\nRESULT {i}"
        )

        print(
            "ID:",
            result["id"]
        )

        print(
            "SUBJECT:",
            result["subject"]
        )

        print(
            "MODULE:",
            result["module"]
        )

        print(
            "CHAPTER:",
            result["chapter"]
        )

        print(
            "PAGE:",
            result["page_number"]
        )

        print(
            "RERANK SCORE:",
            result["rerank_score"]
        )

        

       

        print(
            "\nCONTENT:"
        )

        print(
            result["content"][:1000]
        )

        print(
            "-------------------------------------------"
        )


    print(
        "============================================\n"
    )


    return top_results