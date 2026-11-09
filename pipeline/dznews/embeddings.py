"""Local multilingual sentence embeddings (CPU, no API, no GPU).

paraphrase-multilingual-mpnet-base-v2 runs through ONNX Runtime (fastembed): no PyTorch
install, ~100 ms per article on a 2014 desktop CPU. It maps French, Arabic and English
text into the same 768-dimensional space, so a French and an Arabic headline about the
same event land close together.
"""

import os
import threading

import numpy as np

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
DIMENSIONS = 768

_lock = threading.Lock()
_model = None


def _get_model():
    global _model
    with _lock:
        if _model is None:
            from fastembed import TextEmbedding  # imported lazily: heavy and optional for tests

            _model = TextEmbedding(
                MODEL_NAME,
                cache_dir=os.getenv("FASTEMBED_CACHE_PATH"),
                threads=int(os.getenv("EMBEDDING_THREADS", "0")) or None,
            )
        return _model


def embed(texts: list[str], batch_size: int = 16) -> np.ndarray:
    """Return an (n, 768) float32 array of L2-normalised embeddings (cosine = dot product)."""
    if not texts:
        return np.zeros((0, DIMENSIONS), dtype=np.float32)
    if "e5" in MODEL_NAME.lower():
        # E5 models were trained with a task prefix; "query:" is the one for symmetric
        # similarity between two texts of the same kind.
        texts = [f"query: {t}" for t in texts]
    vectors = np.array(list(_get_model().embed(texts, batch_size=batch_size)), dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def to_pgvector(vector: np.ndarray) -> str:
    """Text form accepted by the PostgreSQL `vector` type."""
    return "[" + ",".join(f"{x:.6f}" for x in vector) + "]"


def from_pgvector(text: str) -> np.ndarray:
    return np.array(text.strip("[]").split(","), dtype=np.float32)
