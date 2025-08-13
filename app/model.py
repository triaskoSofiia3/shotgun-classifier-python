from transformers import pipeline
import threading

_lock = threading.Lock()
_classifier = None

def get_classifier():
    global _classifier
    with _lock:
        if _classifier is None:
            _classifier = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/deberta-v3-base-zeroshot-v1",
            )
        return _classifier

def classify_text(text: str, labels: list[str]) -> dict:
    classifier = get_classifier()
    result = classifier(text, labels)
    return {
        "category": result["labels"][0],
        "confidence": round(result["scores"][0], 4),
    }
