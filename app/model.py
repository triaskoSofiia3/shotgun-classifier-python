from typing import List, Dict
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch

MODEL_ID = "MoritzLaurer/deberta-v3-base-zeroshot-v1"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_ID, torch_dtype=torch.float32)

classifier = pipeline(
    task="zero-shot-classification",
    model=model,
    tokenizer=tokenizer,
    device=-1  # CPU
)

def classify_text(text: str, labels: List[str]) -> Dict[str, float]:
    result = classifier(text, candidate_labels=labels)
    return {
        "category": result["labels"][0],
        "confidence": round(float(result["scores"][0]), 4),
    }
