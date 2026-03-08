from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.rag.indexer import RagIndexer
from services.rag.retriever import RagRetriever


@pytest.fixture
def mock_rag_embeddings(monkeypatch):
    calls = {"embed_batches": 0, "texts": 0}

    def fake_vectors(texts: list[str]) -> list[list[float]]:
        calls["embed_batches"] += 1
        calls["texts"] += len(texts)
        vectors: list[list[float]] = []
        for text in texts:
            t = text.lower()
            vectors.append(
                [
                    float("worker" in t),
                    float("process" in t or "pool" in t),
                    float("route" in t or "/api/" in t),
                    float(len(t) % 17) / 17.0 + 0.01,
                ]
            )
        return vectors

    def fake_embed_indexer(self: RagIndexer, texts: list[str]) -> list[list[float]]:
        return fake_vectors(texts)

    def fake_embed_retriever(self: RagRetriever, texts: list[str]) -> list[list[float]]:
        return fake_vectors(texts)

    def fake_generate(self: RagRetriever, *, question: str, context: str) -> str:
        assert question
        assert context
        return "Mocked answer grounded in retrieved chunks."

    monkeypatch.setattr(RagIndexer, "_embed_texts_mistral", fake_embed_indexer)
    monkeypatch.setattr(RagRetriever, "_embed_texts_mistral", fake_embed_retriever)
    monkeypatch.setattr(RagRetriever, "_generate_with_mistral", fake_generate)
    return calls


def test_rag_indexer_and_retriever_query(tmp_path: Path, mock_rag_embeddings):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    workers_doc = docs_dir / "workers.md"
    workers_doc.write_text(
        "# Workers\n\n## Thread Worker\nThe thread worker manages async jobs and progress.\n\n"
        "## Process Pool\nThe process pool parallelizes Monte Carlo runs.\n",
        encoding="utf-8",
    )
    routes_doc = docs_dir / "routes.md"
    routes_doc.write_text(
        "# Routes\n\n## Monte Carlo Async Status\nUse GET /api/v1/monte-carlo/async/{job_id}\n",
        encoding="utf-8",
    )

    index_path = tmp_path / ".rag" / "index.json"
    indexer = RagIndexer(
        index_path=str(index_path),
        repo_root=tmp_path,
        chunk_target_chars=500,
        api_key="test-key",
    )
    payload = indexer.build_index_payload_from_files([workers_doc, routes_doc])
    indexer.save_index(payload)

    retriever = RagRetriever(index_path=str(index_path), api_key="test-key")
    result = retriever.query(
        query="difference between thread worker and process pool",
        top_k=2,
        include_chunks=True,
    )
    assert result["mode"] == "generate"
    assert result["answer"]
    assert any(src["path"].endswith("workers.md") for src in result["sources"])
    assert result["retrieved_chunks"] is not None


def test_rag_index_file_format_is_json(tmp_path: Path, mock_rag_embeddings):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "context.md").write_text("# Context\n\nProject purpose.\n", encoding="utf-8")

    index_path = tmp_path / ".rag" / "index.json"
    indexer = RagIndexer(index_path=str(index_path), repo_root=tmp_path, api_key="test-key")
    payload = indexer.build_index_payload_from_files([docs_dir / "context.md"])
    indexer.save_index(payload)

    loaded = json.loads(index_path.read_text(encoding="utf-8"))
    assert loaded["chunk_count"] >= 1
    assert "chunks" in loaded
    assert "embedding" in loaded["chunks"][0]
    assert "content_sha256" in loaded["chunks"][0]


def test_rag_indexer_reuses_embeddings_for_unchanged_chunks(
    tmp_path: Path, mock_rag_embeddings
):
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    workers_doc = docs_dir / "workers.md"
    workers_doc.write_text("# Workers\n\n## A\nhello worker\n", encoding="utf-8")

    index_path = tmp_path / ".rag" / "index.json"
    indexer = RagIndexer(index_path=str(index_path), repo_root=tmp_path, api_key="test-key")

    payload1 = indexer.build_index_payload_from_files([workers_doc])
    indexer.save_index(payload1)
    first_calls = mock_rag_embeddings["texts"]
    assert first_calls > 0

    payload2 = indexer.build_index_payload_from_files([workers_doc])
    indexer.save_index(payload2)
    assert mock_rag_embeddings["texts"] == first_calls
    assert payload2["chunks"][0]["content_sha256"] == payload1["chunks"][0]["content_sha256"]
