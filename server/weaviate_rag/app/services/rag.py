import os
from dotenv import load_dotenv
from openai import OpenAI
from .weaviate_setup import client

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
WEAVIATE_COLLECTION = "LectureChunk"


STATIC_FIG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "static", "figures")
)

STATIC_BASE_URL = os.getenv("STATIC_BASE_URL", "http://localhost:8000")

oa = OpenAI(api_key=OPENAI_API_KEY)

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

    # Return all metadata; convert page to 0-based for your UI
    return [
        {
            "text": (obj.properties.get("text", "") or "").strip(),
            "source": obj.properties.get("source", "unknown"),
            "page": (obj.properties.get("page", 1) - 1),
            "imagePath": obj.properties.get("imagePath"),  
        }
        for obj in res.objects
    ]

def _build_fallback_image_paths(retrieved):
    web_paths = []
    seen = set()
    for c in retrieved:
        src = c.get("source")
        page0 = c.get("page")
        if not src or page0 is None:
            continue
        base = os.path.splitext(src)[0]
        page1 = page0 + 1  
        candidate_name = f"{base}_p{page1}.png"
        fs_path = os.path.join(STATIC_FIG_DIR, candidate_name)
        if os.path.exists(fs_path):
            web_path = f"/static/figures/{candidate_name}"
            if web_path not in seen:
                web_paths.append(web_path)
                seen.add(web_path)
    return web_paths

def retrieve_answer(question: str) -> str:
    retrieved = _retrieve_chunks(question)

    # Build text-only context for the LLM
    text_chunks = [c["text"] for c in retrieved if c.get("text")]
    context = "\n\n---\n\n".join(text_chunks)

    # Collect any image paths returned directly from Weaviate
    figure_paths = [c["imagePath"] for c in retrieved if c.get("imagePath")]

    # If we didn't get any imagePath rows, try file-name fallback
    if not figure_paths:
        figure_paths = _build_fallback_image_paths(retrieved)

    # If there is neither text nor figures, bail out
    if not text_chunks and not figure_paths:
        return (
            "1. **Explain** – I don't know based on the provided materials.\n\n"
            "2. **Compare** – I don't know based on the provided materials.\n\n"
            "3. **Motivate** – I don't know based on the provided materials."
        )

    # Ask the model with text context (if any)
    if text_chunks:
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
    else:
        # No text available but figures exist
        answer = (
            "1. **Explain** – The relevant information appears primarily in the figures for this topic.\n\n"
            "2. **Compare** – Think of the flow as a loop: predict velocities, correct pressure, and re-predict until consistent.\n\n"
            "3. **Motivate** – Explore SIMPLE/SIMPLER and how they compare to PISO."
        )

    # Sources block (0-based page shown, as you have it)
    sources = "\n".join(
        f"- From **{c['source']}**, page {c['page']}" for c in retrieved
    )

    def _abs(url: str) -> str:
        # stored paths look like "/static/figures/CFD_p8.png"
        return url if url.startswith("http") else f"{STATIC_BASE_URL}{url}"

    images_html = ""
    if figure_paths:
        # dedupe while preserving order
        seen = set()
        uniq = [p for p in figure_paths if not (p in seen or seen.add(p))]
        imgs = "\n".join(
            f'<div style="margin:8px 0"><img src="{_abs(p)}" alt="figure" '
            f'style="max-width:100%;border-radius:8px"/></div>'
            for p in uniq
        )
        images_html = f"\n\n<hr/>\n<h3>Figures</h3>\n{imgs}\n"


    return f"{answer}{images_html}\n\n---\n**Sources:**\n{sources}"
