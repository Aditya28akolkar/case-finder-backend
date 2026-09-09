import chromadb

client = chromadb.PersistentClient(path="./chroma_db")

print("\n========== CHROMA COLLECTIONS ==========\n")

collections = client.list_collections()

for collection in collections:
    print("NAME:", collection.name)
    print("COUNT:", collection.count())
    print("-" * 50)