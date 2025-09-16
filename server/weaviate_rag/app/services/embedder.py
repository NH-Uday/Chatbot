import os
import io
import time
import random
import base64
from typing import List, Iterable, Tuple

import pdfplumber
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI, APIError, RateLimitError
from PIL import Image

from app.services.weaviate_setup import init_schema, client
from app.services.format_math_equation import format_equations_for_mathjax


try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except Exception:
    HAS_PYMUPDF = False

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

openai = OpenAI(api_key=OPENAI_API_KEY)

# ----------------- Configuration -----------------
PDF_FOLDER = os.getenv("PDF_FOLDER", "docs")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))       # words
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Static folder for written images
# embedder.py is at: app/services/embedder.py 
STATIC_FIG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "static", "figures")
)
os.makedirs(STATIC_FIG_DIR, exist_ok=True)

# Image captioning (optional) — default OFF to avoid 429s
ENABLE_IMAGE_CAPTIONS = os.getenv("ENABLE_IMAGE_CAPTIONS", "false").lower() in {"1", "true", "yes"}
VISION_MODEL = os.getenv("VISION_MODEL", "gpt-4o-mini")
# Reduce density to avoid bursts; increase later if stable
MAX_CAPTIONS_PER_PAGE = int(os.getenv("MAX_CAPTIONS_PER_PAGE", "1"))
# Small delay between caption requests to smooth bursts
CAPTION_REQUEST_DELAY_SEC = float(os.getenv("CAPTION_REQUEST_DELAY_SEC", "0.35"))
# Retry settings for 429s / transient errors
MAX_RETRIES = int(os.getenv("CAPTION_MAX_RETRIES", "6"))
BACKOFF_BASE = float(os.getenv("CAPTION_BACKOFF_BASE", "0.6"))  # seconds

# ----------------- Helpers -----------------
def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))

def chunk_text(text: str) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    if not words:
        return chunks

    start = 0
    step = max(1, CHUNK_SIZE - CHUNK_OVERLAP)
    while start < len(words):
        chunk = words[start:start + CHUNK_SIZE]
        chunks.append(" ".join(chunk))
        start += step
    return chunks

def _embed_and_insert(collection, text: str, source: str, page_number: int):
    if not text.strip():
        return
    emb = openai.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    ).data[0].embedding

    collection.data.insert(
        properties={
            "text": text,
            "source": source,
            "page": page_number,  # stored 1-based
        },
        vector=emb,
    )

def _insert_metadata_only(collection, props: dict):
    """
    Insert an object without a vector (for pure metadata like images without captions).
    """
    collection.data.insert(
        properties=props,
        vector=None,
    )

# ----------------- Captioning with retries -----------------
def _describe_image_with_gpt4o(image_b64_png: str) -> str:
    """
    Caption an image with retries & exponential backoff to handle 429.
    """
    attempt = 0
    while True:
        try:
            resp = openai.chat.completions.create(
                model=VISION_MODEL,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text":
                            "Describe this figure/diagram for search in 1–3 sentences. "
                            "Mention axes, labels, units, variables, and what it demonstrates. "
                            "Be specific and concise."
                         },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64_png}"}}
                    ]
                }],
                temperature=0
            )
            return (resp.choices[0].message.content or "").strip()

        except RateLimitError as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                raise
            # Respect Retry-After if present; otherwise exponential backoff with jitter
            retry_after = getattr(e, "response", None)
            delay = None
            if retry_after and hasattr(retry_after, "headers"):
                ra = retry_after.headers.get("Retry-After")
                if ra:
                    try:
                        delay = float(ra)
                    except Exception:
                        delay = None
            if delay is None:
                delay = BACKOFF_BASE * (2 ** (attempt - 1)) * (1 + random.random() * 0.25)
            time.sleep(delay)

        except APIError:
            # transient server errors: retry a few times
            attempt += 1
            if attempt > MAX_RETRIES:
                raise
            delay = BACKOFF_BASE * (2 ** (attempt - 1)) * (1 + random.random() * 0.25)
            time.sleep(delay)

# ----------------- Image extraction & saving -----------------
def _save_image_png(im: Image.Image, out_name: str) -> str:
    """
    Save PIL image to STATIC_FIG_DIR as PNG and return the relative web path (/static/figures/filename.png)
    """
    out_path = os.path.join(STATIC_FIG_DIR, out_name)
    im.save(out_path, format="PNG")
    # web path your FastAPI will serve
    return f"/static/figures/{out_name}"

def _extract_images_with_pymupdf(pdf_path: str) -> Iterable[Tuple[int, Image.Image]]:
    """
    Yields (page_number_1_based, PIL_Image). Skips if PyMuPDF unavailable.
    """
    if not HAS_PYMUPDF:
        return

    doc = fitz.open(pdf_path)
    try:
        for pno, page in enumerate(doc, start=1):
            imgs = page.get_images(full=True)
            if not imgs:
                continue

            emitted = 0
            for img in imgs:
                if emitted >= MAX_CAPTIONS_PER_PAGE:
                    break
                xref = img[0]
                try:
                    img_dict = doc.extract_image(xref)
                    raw = img_dict.get("image")
                    if not raw:
                        continue

                    im = Image.open(io.BytesIO(raw)).convert("RGB")

                    # Optional downscale to keep files smaller and vision tokens lower
                    if max(im.size) > 1600:
                        scale = 1600 / float(max(im.size))
                        new_size = (int(im.size[0] * scale), int(im.size[1] * scale))
                        im = im.resize(new_size)

                    yield (pno, im)
                    emitted += 1
                except Exception:
                    continue
    finally:
        doc.close()

# ----------------- Main API -----------------
def embed_and_store(pdf_path: str):
    filename = os.path.basename(pdf_path)
    collection = client.collections.get("LectureChunk")

    # ---- Text pages
    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            page_text = page.extract_text() or ""
            # Optional light math normalization for nicer display/retrieval
            page_text = format_equations_for_mathjax(page_text)

            for chunk in chunk_text(page_text):
                _embed_and_insert(collection, chunk, filename, page_number)

    # ---- Images: save + (optional) caption + index
    if HAS_PYMUPDF:
        for page_number, pil_img in _extract_images_with_pymupdf(pdf_path):
            try:
                # Save PNG to /static/figures and get a web path we can render in the UI
                base = os.path.splitext(filename)[0]
                out_name = f"{base}_p{page_number}.png"
                image_web_path = _save_image_png(pil_img, out_name)

                if ENABLE_IMAGE_CAPTIONS:
                    # Smooth out bursts
                    time.sleep(CAPTION_REQUEST_DELAY_SEC)

                    # Make a small input image for vision captioning
                    buf = io.BytesIO()
                    pil_img.save(buf, format="PNG")
                    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

                    caption = _describe_image_with_gpt4o(image_b64) or "Figure/diagram"
                    # Store as a normal embedded record (so retrieval can find it semantically)
                    _embed_and_insert(
                        collection=collection,
                        text=f"[Figure] {caption}",
                        source=filename,
                        page_number=page_number
                    )
                    # Also attach a metadata-only row so you can render the image directly
                    _insert_metadata_only(collection, {
                        "text": "[Figure] image",
                        "source": filename,
                        "page": page_number,
                        "imagePath": image_web_path,
                    })
                else:
                    # No caption → insert metadata-only object that still points to the image file
                    _insert_metadata_only(collection, {
                        "text": "[Figure]",
                        "source": filename,
                        "page": page_number,
                        "imagePath": image_web_path,
                    })

            except RateLimitError as e:
                print(f"⚠️  Skipped an image on page {page_number}: {e}")
            except Exception as e:
                print(f"⚠️  Skipped an image on page {page_number}: {e}")

    print(f"✅ Finished indexing: {filename}")

def load_all_pdfs():
    if not os.path.exists(PDF_FOLDER):
        print(f"❌ Folder not found: {PDF_FOLDER}")
        return

    init_schema()

    for file in os.listdir(PDF_FOLDER):
        if file.lower().endswith(".pdf"):
            pdf_path = os.path.join(PDF_FOLDER, file)
            embed_and_store(pdf_path)

    client.close()
