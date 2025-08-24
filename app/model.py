from typing import List, Dict
from sentence_transformers import SentenceTransformer
import numpy as np

# Ініціалізація моделі один раз при старті
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
_model = SentenceTransformer(MODEL_ID)

# Кеш ембедингів для категорій
_label_cache: dict[str, np.ndarray] = {}

def classify_text(text: str, labels: List[str]) -> Dict[str, float]:
    """
    Класифікація документа через sentence embeddings + cosine similarity
    """
    global _label_cache

    # ⚡️ Ріжемо текст до перших 300 слів (швидкість + достатньо для класифікації)
    short_text = " ".join(text.split()[:300])

    # Ембединг документа
    text_emb = _model.encode(short_text, convert_to_numpy=True, normalize_embeddings=True)

    # Ключ для кеша (залежить від списку категорій)
    cache_key = "|".join(labels).lower()

    if cache_key not in _label_cache:
        _label_cache[cache_key] = _model.encode(
            labels,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

    label_embs = _label_cache[cache_key]

    # Cosine similarity (бо нормалізовані → dot product == cosine)
    sims = np.dot(label_embs, text_emb)

    best_idx = int(np.argmax(sims))
    return {
        "category": labels[best_idx],
        "confidence": round(float(sims[best_idx]), 4)
    }
