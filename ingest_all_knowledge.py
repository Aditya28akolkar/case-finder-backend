from app.db.database import SessionLocal

from app.services.knowledge_ingestion_service import process_all_pdfs


SUBJECTS = {
    "Direct Tax":
        r"data\01_Direct_Tax",

    "Indirect Tax":
        r"data\02_Indirect_Tax",

    "Corporate and Other Laws":
        r"data\03_Corporate_Other_Laws",

    "Auditing, Assurance and Professional Ethics":
        r"data\04_Auditing_Assurance_Professional_Ethics",

    "Financial Reporting":
        r"data\05_Financial_Reporting",

    "Advanced Financial Management":
        r"data\06_Advanced_Financial_Management",

    "Cost and Management Accounting":
        r"data\07_Cost_Management_Accounting",

    "Strategic Management":
        r"data\08_Strategic_Management",
}
def main():

    db = SessionLocal()

    try:

        for subject, folder in SUBJECTS.items():

            print("\n")
            print("=" * 70)
            print(f"SUBJECT: {subject}")
            print(f"FOLDER: {folder}")
            print("=" * 70)

            process_all_pdfs(
                base_folder=folder,
                db=db,
                subject=subject
            )

    finally:

        db.close()


if __name__ == "__main__":
    main()