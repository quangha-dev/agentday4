from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from app.core.config import get_settings

VECTOR_SIZE = 384


class Embedder:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model = None
        if self.settings.enable_transformer_embedding:
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(self.settings.embedding_model)
            except Exception:
                self.model = None

    @property
    def model_name(self) -> str:
        return self.settings.embedding_model if self.model else "local-vietnamese-hashing-v1"

    @property
    def vector_size(self) -> int:
        if self.model:
            return int(self.model.get_sentence_embedding_dimension())
        return VECTOR_SIZE

    def encode(self, texts: list[str]) -> list[list[float]]:
        if self.model:
            vectors = self.model.encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]
        return [self._hash_vector(text) for text in texts]

    @staticmethod
    def _hash_vector(text: str) -> list[float]:
        vector = [0.0] * VECTOR_SIZE
        normalized = re.sub(r"\s+", " ", text.casefold()).strip()
        tokens = re.findall(r"\w+", normalized, re.UNICODE)
        features = tokens + [normalized[index : index + 3] for index in range(max(0, len(normalized) - 2))]
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            slot = int.from_bytes(digest[:4], "little") % VECTOR_SIZE
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[slot] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()

