import os
import fitz

from sqlalchemy.orm import Session

from app.models.knowledge_document_model import KnowledgeDocument


CHUNK_SIZE = 800
CHUNK_OVERLAP = 100


def extract_pdf_pages(pdf_path):

    document = fitz.open(pdf_path)

    pages = []

    for page_number, page in enumerate(
        document,
        start=1
    ):

        text = page.get_text("text")

        if text:

            pages.append({
                "page_number": page_number,
                "text": text
            })

    document.close()

    return pages


def clean_text(text):

    text = text.replace(
        "\x00",
        " "
    )

    text = " ".join(
        text.split()
    )

    return text.strip()


def create_chunks(text):

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = start + CHUNK_SIZE

        chunk_words = words[start:end]

        chunk = " ".join(
            chunk_words
        )

        if chunk.strip():

            chunks.append(chunk)

        start += (
            CHUNK_SIZE -
            CHUNK_OVERLAP
        )

    return chunks


def process_pdf(
    pdf_path,
    db: Session,
    subject,
    module_name,
    chapter_name
):

    file_name = os.path.basename(
        pdf_path
    )

    print(
        f"\nProcessing: {file_name}"
    )

    # Check whether this PDF has
    # already been ingested
    existing_document = (
        db.query(KnowledgeDocument)
        .filter(
            KnowledgeDocument.file_name == file_name,
            KnowledgeDocument.subject == subject,
            KnowledgeDocument.module == module_name
        )
        .first()
    )

    if existing_document:

        print(
            f"SKIPPED: {file_name} "
            f"already exists in database."
        )

        return

    pages = extract_pdf_pages(
        pdf_path
    )

    chunk_index = 0

    for page in pages:

        page_number = page[
            "page_number"
        ]

        text = clean_text(
            page["text"]
        )

        if not text:
            continue

        chunks = create_chunks(
            text
        )

        for chunk in chunks:

            document = KnowledgeDocument(

                file_name=file_name,

                subject=subject,

                module=module_name,

                chapter=chapter_name,

                page_number=page_number,

                chunk_index=chunk_index,

                content=chunk,

                source="ICAI"

            )

            db.add(document)

            chunk_index += 1

    db.commit()

    print(
        f"Completed: {file_name}"
    )

    print(
        f"Chunks created: {chunk_index}"
    )


def process_all_pdfs(
    base_folder,
    db: Session,
    subject
):

    if not os.path.exists(
        base_folder
    ):

        print(
            f"ERROR: Folder does not exist: "
            f"{base_folder}"
        )

        return

    for module_name in sorted(
        os.listdir(base_folder)
    ):

        module_path = os.path.join(
            base_folder,
            module_name
        )

        if not os.path.isdir(
            module_path
        ):
            continue

        print(
            "\n=============================="
        )

        print(
            f"PROCESSING {subject}"
        )

        print(
            f"MODULE: {module_name}"
        )

        print(
            "=============================="
        )

        for file_name in sorted(
            os.listdir(module_path)
        ):

            if not file_name.lower().endswith(
                ".pdf"
            ):
                continue

            pdf_path = os.path.join(
                module_path,
                file_name
            )

            chapter_name = os.path.splitext(
                file_name
            )[0]

            process_pdf(
                pdf_path=pdf_path,
                db=db,
                subject=subject,
                module_name=module_name,
                chapter_name=chapter_name
            )