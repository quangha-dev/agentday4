from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.core.config import get_settings
from app.services.embedding import get_embedder


class VectorStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedder = get_embedder()
        self.client = (
            QdrantClient(url=self.settings.qdrant_url)
            if self.settings.qdrant_url
            else QdrantClient(path=str(self.settings.qdrant_path))
        )

    def ensure_collection(self) -> None:
        existing = {item.name for item in self.client.get_collections().collections}
        if self.settings.qdrant_collection in existing:
            info = self.client.get_collection(self.settings.qdrant_collection)
            vectors = info.config.params.vectors
            size = getattr(vectors, "size", None)
            if size is not None and int(size) != self.embedder.vector_size:
                raise RuntimeError(
                    "Qdrant collection vector size không khớp embedding ver2. "
                    "Hãy dùng collection mới hoặc reindex dữ liệu."
                )
        else:
            self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=models.VectorParams(
                    size=self.embedder.vector_size, distance=models.Distance.COSINE
                ),
            )

    def upsert(self, items: list[dict]) -> None:
        if not items:
            return
        self.ensure_collection()
        vectors = self.embedder.encode([item["text"] for item in items])
        points = [
            models.PointStruct(id=item["point_id"], vector=vector, payload=item["payload"])
            for item, vector in zip(items, vectors, strict=True)
        ]
        self.client.upsert(collection_name=self.settings.qdrant_collection, points=points, wait=True)

    def delete(self, point_ids: list[str]) -> None:
        if not point_ids:
            return
        self.ensure_collection()
        self.client.delete(
            collection_name=self.settings.qdrant_collection,
            points_selector=models.PointIdsList(points=point_ids),
            wait=True,
        )

    def search(self, query: str, limit: int, document_id: str | None = None) -> list[dict]:
        self.ensure_collection()
        conditions = [
            models.FieldCondition(
                key="contract_version",
                match=models.MatchValue(value=self.settings.contract_version),
            )
        ]
        if document_id:
            conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            )
        query_filter = models.Filter(must=conditions)
        response = self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            query=self.embedder.encode([query])[0],
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [{"score": point.score, **(point.payload or {})} for point in response.points]


@lru_cache
def get_vector_store() -> VectorStore:
    return VectorStore()
