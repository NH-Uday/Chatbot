import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.weaviate_setup import client

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
WEAVIATE_COLLECTION = "LectureChunk"

oa = OpenAI(api_key=OPENAI_API_KEY)

# --- system prompt for the assistant ---
SYSTEM_PROMPT = """
You are a helpful and inspiring study assistant for engineering/science topics.
Use ONLY the provided context. If the answer is not in the context, say "This question is out of my knowledge domain."

Format every answer with exactly these three sections:

1. **Explain** – Explain the topic or equation clearly and precisely using the context. Any equation that can be added please add it.
2. **Compare** – Imagine you are a youtuber having a very popular channel communicating complex science to layman on the street.
Compare the asked topic to something very similar in our world that makes sense. for example... flow of electricity 
can be compared to the flow of water.
3. **Motivate** – Imagine you are a search engine and motivational speaker.
identify further more detailed topics that the asker may want to know more about. Give some quote, motivating the asker to dig deeper in
example: asker asks about german cars, you give some quotes and motivate him to search for Volkswagen, BMW etc.
Be scientifically precise. but not boring.
"""

def _retrieve_chunks(query: str, k: int = 6):
    embedded_query = oa.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    ).data[0].embedding

    coll = client.collections.get(WEAVIATE_COLLECTION)

    res = coll.query.hybrid(
        query=query,
        vector=embedded_query,
        limit=k,
        alpha=0.5
    )

    # ✅ Now returning full metadata
    return [
        {
            "text": obj.properties.get("text", "").strip(),
            "source": obj.properties.get("source", "unknown"),
            "page": obj.properties.get("page", "?")
        }
        for obj in res.objects
    ]


def retrieve_answer(question: str) -> str:
    retrieved_chunks = _retrieve_chunks(question)
    chunks = [c["text"] for c in retrieved_chunks if c["text"]]

    if not chunks:
        return (
            "1. **Explain** – I don't know based on the provided materials.\n\n"
            "2. **Compare** – I don't know based on the provided materials.\n\n"
            "3. **Motivate** – I don't know based on the provided materials."
        )

    context = "\n\n---\n\n".join(chunks)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Question: {question}\n\nContext:\n{context}"}
    ]

    resp = oa.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        temperature=0
    )

    answer = resp.choices[0].message.content

    sources = "\n".join(
        f"- From **{c['source']}**, page {c['page']}" for c in retrieved_chunks
    )

    return f"{answer}\n\n---\n**Sources:**\n{sources}"

