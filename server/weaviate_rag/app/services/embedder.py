# weaviate_rag/app/services/embedder.py
import os
import pdfplumber
import tiktoken
from openai import OpenAI
from dotenv import load_dotenv
from app.services.weaviate_setup import client

load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunk = words[start:start + CHUNK_SIZE]
        chunks.append(" ".join(chunk))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks

def embed_and_store(pdf_path: str):
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    chunks = chunk_text(text)
    print(f"📄 {os.path.basename(pdf_path)} split into {len(chunks)} chunks")

    for chunk in chunks:
        if not chunk.strip():
            continue

        embedding = openai.embeddings.create(
            input=chunk,
            model="text-embedding-3-small"
        ).data[0].embedding

        client.data_object.create(
            {
                "text": chunk,
                "source": os.path.basename(pdf_path),
            },
            class_name="LectureChunk",
            vector=embedding,
        )

    print(f"✅ Finished indexing: {os.path.basename(pdf_path)}")
