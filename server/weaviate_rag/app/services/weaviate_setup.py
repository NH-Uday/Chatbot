# weaviate_rag/app/services/weaviate_setup.py
import weaviate
import os
from dotenv import load_dotenv

load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")

client = weaviate.Client(
    url=WEAVIATE_URL,
    additional_headers={"X-OpenAI-Api-Key": os.getenv("OPENAI_API_KEY")}
)

def init_schema():
    class_name = "LectureChunk"

    if client.schema.exists(class_name):
        return

    schema = {
        "class": class_name,
        "description": "A chunk of a lecture or technical PDF",
        "vectorizer": "none",
        "properties": [
            {
                "name": "text",
                "dataType": ["text"],
            },
            {
                "name": "source",
                "dataType": ["text"],
            },
        ],
    }

    client.schema.create_class(schema)
    print(f"✅ Created schema for '{class_name}'")
