from __future__ import annotations

import hashlib
import importlib
import json
import logging
import math
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)


logger = logging.getLogger("services.rag.indexer")


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


class RagIndexer:
    def __init__(
        self,
        *,
        index_path: str,
        repo_root: Path | None = None,
        chunk_target_chars: int = 2048,
        chunk_overlap_chars: int = 200,
        api_key: str = "",
        embedding_model: str = "mistral-embed",
        request_timeout_seconds: float = 20.0,
        max_retries: int = 3,
        retry_initial_interval_seconds: float = 0.5,
        retry_max_interval_seconds: float = 8.0,
    ) -> None:
        self.index_path = Path(index_path)
        self.repo_root = repo_root or Path(__file__).resolve().parents[5]
        self.chunk_target_chars = chunk_target_chars
        self.chunk_overlap_chars = min(chunk_overlap_chars, chunk_target_chars // 2)
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.request_timeout_seconds = request_timeout_seconds
        self.max_retries = max_retries
        self.retry_initial_interval_seconds = retry_initial_interval_seconds
        self.retry_max_interval_seconds = retry_max_interval_seconds
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

    def discover_default_corpus_files(self) -> list[Path]:
        docs_dir = self.repo_root / "docs"
        files = (
            sorted(p for p in docs_dir.glob("*.md") if p.is_file())
            if docs_dir.exists()
            else []
        )
        readme = self.repo_root / "README.md"
        if readme.exists():
            files.append(readme)
        return files

    def _read_markdown_chunks(self, path: Path) -> list[dict[str, Any]]:
        rel_path = path.resolve().relative_to(self.repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        sections = self._split_by_headings(text, default_title=path.stem)
        chunks: list[dict[str, Any]] = []
        for section_idx, (title, section_text) in enumerate(sections):
            for part_idx, part in enumerate(self._split_with_overlap(section_text)):
                chunk_id = f"{rel_path}::{section_idx}:{part_idx}"
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "path": rel_path,
                        "topic": path.stem,
                        "section_title": title,
                        "content": part,
                        "content_sha256": hashlib.sha256(
                            part.encode("utf-8")
                        ).hexdigest(),
                    }
                )
        return chunks

    @staticmethod
    def _split_by_headings(text: str, *, default_title: str) -> list[tuple[str, str]]:
        sections: list[tuple[str, str]] = []
        current_title = default_title
        current_lines: list[str] = []
        for line in text.splitlines():
            match = _HEADING_RE.match(line)
            if match:
                if current_lines:
                    sections.append((current_title, "\n".join(current_lines).strip()))
                current_title = match.group(2).strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            sections.append((current_title, "\n".join(current_lines).strip()))
        return [(t, body) for t, body in sections if body]

    def _split_with_overlap(self, text: str) -> list[str]:
        if len(text) <= self.chunk_target_chars:
            return [text]
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + self.chunk_target_chars)
            if end < len(text):
                newline_pos = text.rfind(
                    "\n", start + self.chunk_target_chars // 2, end
                )
                if newline_pos > 0:
                    end = newline_pos
            piece = text[start:end].strip()
            if piece:
                chunks.append(piece)
            if end >= len(text):
                break
            start = max(end - self.chunk_overlap_chars, start + 1)
        return chunks

    def _embed_texts_mistral(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.embeddings.create(
            model=self.embedding_model,
            inputs=texts,
        )
        return [item.embedding for item in response.data if item.embedding is not None]

    def _load_existing_embedding_map(self) -> dict[tuple[str, str], list[float]]:
        if not self.index_path.exists():
            return {}
        payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        return {
            (chunk["chunk_id"], chunk["content_sha256"]): chunk["embedding"]
            for chunk in payload.get("chunks", [])
        }

    def build_index_payload_from_files(self, files: list[Path]) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Mistral API key (RAG_API_KEY or MISTRAL_API_KEY)")

        paths = [p.resolve() for p in files]
        all_chunks: list[dict[str, Any]] = []
        for path in paths:
            all_chunks.extend(self._read_markdown_chunks(path))

        payload: dict[str, Any] = {
            "version": 1,
            "provider": "mistral",
            "embedding_model": self.embedding_model,
            "generated_at": datetime.now(UTC).isoformat(),
            "files_indexed": [
                p.resolve().relative_to(self.repo_root).as_posix() for p in paths
            ],
        }

        existing_embeddings = self._load_existing_embedding_map()
        missing_indexes: list[int] = []
        texts_to_embed: list[str] = []

        for i, chunk in enumerate(all_chunks):
            existing = existing_embeddings.get(
                (chunk["chunk_id"], chunk["content_sha256"])
            )
            if existing is not None:
                chunk["embedding"] = existing
            else:
                missing_indexes.append(i)
                texts_to_embed.append(chunk["content"])

        if texts_to_embed:
            embedded_vectors: list[list[float]] = []
            batch_size = 50
            for start in range(0, len(texts_to_embed), batch_size):
                batch = texts_to_embed[start : start + batch_size]
                embedded_vectors.extend(self._embed_texts_mistral(batch))
            for chunk_idx, vector in zip(
                missing_indexes, embedded_vectors, strict=True
            ):
                all_chunks[chunk_idx]["embedding"] = vector

        payload["chunk_count"] = len(all_chunks)
        payload["chunks"] = all_chunks
        return payload

    def build_index_payload(self) -> dict[str, Any]:
        return self.build_index_payload_from_files(self.discover_default_corpus_files())

    def save_index(self, payload: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(
            json.dumps(payload, ensure_ascii=True), encoding="utf-8"
        )

    def build_and_save_index(self) -> dict[str, Any]:
        payload = self.build_index_payload()
        self.save_index(payload)
        return payload
