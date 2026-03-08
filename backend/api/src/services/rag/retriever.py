from __future__ import annotations

import importlib
import json
import logging
import math
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("services.rag.retriever")

_RAG_SYSTEM_PROMPT = (
    "You answer questions about the HPTP project using only the provided context. "
    "Be concise and factual. If the context is insufficient, say so. "
    "Cite sources by path when possible."
)


def _load_faiss() -> Any:
    return importlib.import_module("faiss")


def _load_mistral_sdk() -> tuple[Any, Any, Any]:
    mistral_module = importlib.import_module("mistralai")
    mistral_utils = importlib.import_module("mistralai.utils")
    return (
        mistral_module.Mistral,
        mistral_utils.BackoffStrategy,
        mistral_utils.RetryConfig,
    )


def _compute_backoff_max_elapsed_seconds(
    *,
    initial_interval_seconds: float,
    max_interval_seconds: float,
    max_retries: int,
    exponent: float,
) -> int:
    if max_retries <= 0:
        return 1

    interval = max(1.0, initial_interval_seconds)
    max_interval = max(interval, max_interval_seconds)
    elapsed = 0.0
    for _ in range(max_retries):
        elapsed += min(interval, max_interval)
        interval = min(max_interval, interval * exponent)
    return max(1, int(math.ceil(elapsed)))


class RagRetriever:
    def __init__(
        self,
        *,
        index_path: str,
        api_key: str = "",
        embedding_model: str = "mistral-embed",
        generation_model: str = "mistral-small-latest",
        request_timeout_seconds: float = 20.0,
        max_retries: int = 3,
        retry_initial_interval_seconds: float = 0.5,
        retry_max_interval_seconds: float = 8.0,
    ) -> None:
        self.index_path = Path(index_path)
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max_retries
        self.retry_initial_interval_seconds = retry_initial_interval_seconds
        self.retry_max_interval_seconds = retry_max_interval_seconds

        self._chunks: list[dict[str, Any]] = []
        self._chunk_embedding_matrix: np.ndarray | None = None
        self._faiss_index: Any | None = None
        self._mistral_client: Any | None = None

    @property
    def _client(self) -> Any:
        if self._mistral_client is None:
            Mistral, BackoffStrategy, RetryConfig = _load_mistral_sdk()
            retry_exponent = 2.0
            max_elapsed_seconds = _compute_backoff_max_elapsed_seconds(
                initial_interval_seconds=self.retry_initial_interval_seconds,
                max_interval_seconds=self.retry_max_interval_seconds,
                max_retries=self.max_retries,
                exponent=retry_exponent,
            )
            retry_config = RetryConfig(
                strategy="backoff",
                backoff=BackoffStrategy(
                    initial_interval=max(1, int(self.retry_initial_interval_seconds)),
                    max_interval=max(1, int(self.retry_max_interval_seconds)),
                    exponent=retry_exponent,
                    max_elapsed_time=max_elapsed_seconds,
                ),
                retry_connection_errors=True,
            )
            timeout_ms = max(1, int(self.request_timeout_seconds * 1000))
            self._mistral_client = Mistral(
                api_key=self.api_key,
                retry_config=retry_config,
                timeout_ms=timeout_ms,
            )
            logger.debug(
                "Initialized Mistral v1 client with timeout_ms=%s max_retries=%s",
                timeout_ms,
                self.max_retries,
            )
        return self._mistral_client

    def load_index(self) -> None:
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        chunks = payload["chunks"]
        if not chunks:
            raise ValueError(f"RAG index is empty: {self.index_path}")

        matrix = np.asarray([chunk["embedding"] for chunk in chunks], dtype=np.float32)
        index: Any | None = None
        try:
            faiss = _load_faiss()
            index = faiss.IndexFlatL2(matrix.shape[1])
            index_any: Any = index
            index_any.add(matrix)
        except ModuleNotFoundError:
            logger.warning("faiss is not installed; falling back to numpy retrieval")

        self._chunks = chunks
        self._chunk_embedding_matrix = matrix
        self._faiss_index = index

    def _ensure_loaded(self) -> None:
        if self._faiss_index is None:
            self.load_index()

    def _embed_texts_mistral(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(
            model=self.embedding_model,
            inputs=texts,
        )
        return [item.embedding for item in response.data if item.embedding is not None]

    def _build_generation_context(self, hits: list[dict[str, Any]]) -> str:
        blocks: list[str] = []
        for hit in hits:
            source = hit["source"]
            blocks.append(
                "\n".join(
                    [
                        f"Source: {source['path']}",
                        f"Section: {source['section_title']}",
                        f"Chunk ID: {source['chunk_id']}",
                        "Content:",
                        hit["content"],
                    ]
                )
            )
        return "\n\n---\n\n".join(blocks)

    def _extract_chat_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        parts = [part.get("text", "") for part in content if part.get("type") == "text"]
        return "".join(parts).strip()

    def _generate_with_mistral(self, *, question: str, context: str) -> str:
        response = self._client.chat.complete(
            model=self.generation_model,
            messages=[
                {"role": "system", "content": _RAG_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        "Use only the context below.\n\n"
                        f"{context}"
                    ),
                },
            ],
            temperature=0.0,
        )
        return self._extract_chat_text(response.choices[0].message.content)

    def _filter_chunk_indices(self, *, topics: list[str] | None) -> list[int]:
        if not topics:
            return list(range(len(self._chunks)))

        normalized_topics = {t.lower() for t in (topics or [])}
        allowed: list[int] = []
        for idx, chunk in enumerate(self._chunks):
            if (
                normalized_topics
                and str(chunk.get("topic", "")).lower() not in normalized_topics
            ):
                continue
            allowed.append(idx)
        return allowed

    def _search_top_k(
        self, query_embedding: list[float], *, top_k: int, allowed: list[int]
    ) -> list[tuple[int, float]]:
        query_vec = np.asarray([query_embedding], dtype=np.float32)

        if len(allowed) == len(self._chunks) and self._faiss_index is not None:
            faiss_index_any: Any = self._faiss_index
            distances, idxs = faiss_index_any.search(
                query_vec, min(top_k, len(self._chunks))
            )
            return [
                (int(idx), float(distance))
                for distance, idx in zip(distances[0], idxs[0], strict=True)
                if idx >= 0
            ]

        assert self._chunk_embedding_matrix is not None
        subset_matrix = self._chunk_embedding_matrix[allowed]
        if self._faiss_index is not None:
            faiss = _load_faiss()
            subset_index = faiss.IndexFlatL2(subset_matrix.shape[1])
            subset_index_any: Any = subset_index
            subset_index_any.add(subset_matrix)
            distances, idxs = subset_index_any.search(
                query_vec, min(top_k, len(allowed))
            )
            return [
                (allowed[int(idx)], float(distance))
                for distance, idx in zip(distances[0], idxs[0], strict=True)
                if idx >= 0
            ]

        distances = np.sum((subset_matrix - query_vec) ** 2, axis=1)
        top_indices = np.argsort(distances)[: min(top_k, len(allowed))]
        return [
            (allowed[int(idx)], float(distances[int(idx)])) for idx in top_indices
        ]

    def _serialize_hit(self, chunk: dict[str, Any], distance: float) -> dict[str, Any]:
        return {
            "source": {
                "path": chunk["path"],
                "section_title": chunk["section_title"],
                "chunk_id": chunk["chunk_id"],
                "topic": chunk.get("topic"),
                "distance": distance,
            },
            "content": chunk["content"],
        }

    def query(
        self,
        *,
        query: str,
        top_k: int,
        topics: list[str] | None = None,
        include_chunks: bool = False,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Mistral API key (RAG_API_KEY or MISTRAL_API_KEY)")

        self._ensure_loaded()

        t0 = time.perf_counter()
        query_embedding = self._embed_texts_mistral([query])[0]
        allowed = self._filter_chunk_indices(topics=topics)
        selected = (
            self._search_top_k(query_embedding, top_k=top_k, allowed=allowed)
            if allowed
            else []
        )
        t1 = time.perf_counter()

        hits: list[dict[str, Any]] = []
        for idx, distance in selected:
            chunk = self._chunks[idx]
            hits.append(self._serialize_hit(chunk, distance))

        context = self._build_generation_context(hits)
        answer = (
            "No matching sources found in the indexed corpus."
            if not hits
            else self._generate_with_mistral(question=query, context=context)
        )
        t2 = time.perf_counter()

        sources = [hit["source"] for hit in hits]
        result: dict[str, Any] = {
            "answer": answer,
            "mode": "generate",
            "sources": sources,
            "timings_ms": {
                "retrieval": round((t1 - t0) * 1000, 1),
                "generation": round((t2 - t1) * 1000, 1),
                "total": round((t2 - t0) * 1000, 1),
            },
        }
        if include_chunks:
            result["retrieved_chunks"] = hits
        return result
