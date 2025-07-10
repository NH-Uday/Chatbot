import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.weaviate_setup import client

load_dotenv()
openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CLASS_NAME = "LectureChunk"
TOP_K = 5
CONFIDENCE_THRESHOLD = 0.75

SYSTEM_PROMPT = """
You are an inspiring AI tutor.
When answering a question, structure your response in 3 clearly titled parts:

🧠 Clarity
Give a straightforward, understandable explanation.

⚖️ Contrast (if applicable)
Compare with related or traditional concepts to enhance understanding.

🚀 Motivational Close
End with an encouraging message. Include 3–5 related subtopics or follow-up study suggestions that the user can explore next. Format as a bullet list.
"""

def retrieve_answer(question: str) -> str:
    # Embed the user's question
    query_embedding = openai.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    ).data[0].embedding

    # Query Weaviate for relevant chunks with certainty
    result = (
        client.query.get(CLASS_NAME, ["text", "source"])
        .with_near_vector({"vector": query_embedding})
        .with_limit(TOP_K)
        .with_additional(["certainty"])
        .do()
    )

    chunks = result.get("data", {}).get("Get", {}).get(CLASS_NAME, [])
    top_certainty = chunks[0]["_additional"].get("certainty", 0) if chunks else 0

    if not chunks or top_certainty < CONFIDENCE_THRESHOLD:
        # Fallback to general answer without context
        fallback_response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            temperature=0.7,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
        )
        return fallback_response.choices[0].message.content.strip()

    # Otherwise, use lecture context
    context = "\n\n".join([c["text"] for c in chunks])

    completion = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0.7,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ]
    )

    return completion.choices[0].message.content.strip()
