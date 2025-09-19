# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  
from pydantic import BaseModel
import os

from app.services.rag import retrieve_answer
from app.services.weaviate_setup import client  

app = FastAPI()

# Serve /static (expects server/weaviate_rag/static/...)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://132.195.142.65:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    answer = retrieve_answer(req.question)
    return {"answer": answer}

# Close Weaviate cleanly to avoid warnings on reload/shutdown
@app.on_event("shutdown")
def shutdown_event():
    try:
        client.close()
    except Exception:
        pass
