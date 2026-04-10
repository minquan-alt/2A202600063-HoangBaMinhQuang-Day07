from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document
import os
from dotenv import load_dotenv

load_dotenv()


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use qdrantDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        self._use_qdrant = True
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0
        self._client = None

        try:
            from qdrant_client import QdrantClient, models

            self._client = QdrantClient(
                url=os.getenv("QDRANT_BASE_URL"),
                api_key=os.getenv("QDRANT_API_KEY"),
            )
            vector_size = len(self._embedding_fn("test"))
            try:
                self._client.get_collection(self._collection_name)
            except Exception:
                self._client.create_collection(
                    collection_name=self._collection_name,
                    vectors_config=models.VectorParams(
                        size=vector_size,
                        distance=models.Distance.COSINE
                    ),
                )
            self._collection = self._collection_name
            self._use_qdrant = True
        except Exception:
            self._use_qdrant = False
            self._collection = None
            self._client = None

    def _make_record(self, doc: Document) -> dict[str, Any]:
        metadata = dict(doc.metadata or {})
        metadata.setdefault("doc_id", doc.id)

        return {
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
        }

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if top_k <= 0 or not records:
            return []

        query_vec = self._embedding_fn(query)
        scored: list[dict[str, Any]] = []

        for r in records:
            score = _dot(query_vec, r["embedding"])
            scored.append({
                "id": r["id"],
                "content": r["content"],
                "metadata": r["metadata"],
                "score": score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For qdrantDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        if not docs:
            return

        records = [self._make_record(doc) for doc in docs]

        if self._use_qdrant and self._client is not None and self._collection is not None:
            try:
                from qdrant_client import models

                points = []
                for record in records:
                    points.append(
                        models.PointStruct(
                            id=self._next_index,
                            vector=record["embedding"],
                            payload={
                                "doc_id": record["id"],
                                "content": record["content"],
                                "metadata": record["metadata"],
                            },
                        )
                    )
                    self._next_index += 1

                self._client.upsert(collection_name=self._collection, points=points)
            except Exception:
                # Fall back to in-memory if qdrant operation fails.
                self._use_qdrant = False

        self._store.extend(records)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        if top_k <= 0:
            return []

        if self._use_qdrant and self._client is not None and self._collection is not None:
            try:
                query_vec = self._embedding_fn(query)
                points, _ = self._client.query_points(
                    collection_name=self._collection,
                    query=query_vec,
                    limit=top_k,
                    with_payload=True,
                )
                results: list[dict[str, Any]] = []
                for p in points:
                    payload = p.payload or {}
                    results.append(
                        {
                            "id": payload.get("doc_id"),
                            "content": payload.get("content", ""),
                            "metadata": payload.get("metadata", {}),
                            "score": float(p.score or 0.0),
                        }
                    )
                return results
            except Exception:
                self._use_qdrant = False

        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        if self._use_qdrant and self._client is not None and self._collection is not None:
            try:
                return int(self._client.count(collection_name=self._collection).count)
            except Exception:
                self._use_qdrant = False

        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            return self.search(query, top_k=top_k)

        filtered = []
        for r in self._store:
            md = r.get("metadata", {})
            if all(md.get(k) == v for k, v in metadata_filter.items()):
                filtered.append(r)

        return self._search_records(query, filtered, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        before = len(self._store)
        self._store = [r for r in self._store if r.get("metadata", {}).get("doc_id") != doc_id]
        removed = len(self._store) < before

        if removed and self._use_qdrant and self._client is not None and self._collection is not None:
            try:
                from qdrant_client import models

                self._client.delete(
                    collection_name=self._collection,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="doc_id",
                                    match=models.MatchValue(value=doc_id),
                                )
                            ]
                        )
                    ),
                )
            except Exception:
                self._use_qdrant = False

        return removed
