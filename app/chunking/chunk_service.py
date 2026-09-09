from langchain_text_splitters import RecursiveCharacterTextSplitter


class ChunkService:
    def __init__(self, chunk_size=800, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str):
        """
        Splits a long document into overlapping chunks.
        """

        if not text:
            return []

        chunks = []

        start = 0
        chunk_id = 1
        text_length = len(text)

        while start < text_length:

            end = min(start + self.chunk_size, text_length)

            chunk_text = text[start:end]

            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "start_char": start,
                "end_char": end
            })

            chunk_id += 1

            start += self.chunk_size - self.chunk_overlap

        return chunks