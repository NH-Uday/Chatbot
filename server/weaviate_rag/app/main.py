# weaviate_rag/app/main.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
from app.services.rag import retrieve_answer

app = FastAPI()

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    answer = retrieve_answer(req.question)
    return {"answer": answer}
