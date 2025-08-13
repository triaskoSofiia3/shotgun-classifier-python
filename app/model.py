from transformers import pipeline
from typing import List, Dict

classifier = pipeline(
    task="zero-shot-classification",
    model="MoritzLaurer/deberta-v3-base-zeroshot-v1",
    device=-1  # CPU only
)

def classify_text(text: str, labels: List[str]) -> Dict[str, float]:
    result = classifier(text, labels)
    return {
        "category": result["labels"][0],
        "confidence": round(result["scores"][0], 4),
    }
