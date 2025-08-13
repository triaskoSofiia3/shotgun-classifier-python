from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
from app.model import classify_text

app = FastAPI()

class ClassifyRequest(BaseModel):
    text: str
    candidate_labels: List[str]

class ClassifyResponse(BaseModel):
    category: str
    confidence: float

@app.post("/classify", response_model=ClassifyResponse)
def classify(req: ClassifyRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text is empty")

    if not req.candidate_labels:
        raise HTTPException(status_code=400, detail="No candidate labels provided")

    result = classify_text(req.text, req.candidate_labels)
    return result
