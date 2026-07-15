from app.services.chunk_service import ChunkService

text = """
This is a long legal case document.
The plaintiff entered into a contract.
The defendant breached the contract.
The court awarded compensation.
""" * 50

chunk_service = ChunkService()

chunks = chunk_service.split_text(text)

print(f"Total Chunks: {len(chunks)}")

for i, chunk in enumerate(chunks, start=1):
    print(f"\nChunk {i}")
    print(chunk[:200])