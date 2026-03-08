from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from core.config import get_settings  # noqa: E402
from services.rag import RagIndexer, RagRetriever  # noqa: E402


def _make_indexer(args: argparse.Namespace) -> RagIndexer:
    settings = get_settings()
    return RagIndexer(
        index_path=args.output or settings.rag_index_path,
        chunk_target_chars=args.chunk_target_chars or settings.rag_chunk_target_chars,
        api_key=settings.rag_api_key,
        embedding_model=settings.rag_embedding_model,
        request_timeout_seconds=settings.rag_request_timeout_seconds,
    )


def _make_retriever(args: argparse.Namespace) -> RagRetriever:
    settings = get_settings()
    return RagRetriever(
        index_path=args.output or settings.rag_index_path,
        api_key=settings.rag_api_key,
        embedding_model=settings.rag_embedding_model,
        generation_model=settings.rag_model,
        request_timeout_seconds=settings.rag_request_timeout_seconds,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="RAG CLI (build/query) for local docs corpus."
    )
    parser.add_argument("--output", default=None, help="Override RAG index path.")
    parser.add_argument(
        "--chunk-target-chars", type=int, default=None, help="Override chunk size."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build or update the local RAG index.")
    build.add_argument(
        "--json",
        action="store_true",
        help="Print JSON summary (default prints readable summary).",
    )

    query = subparsers.add_parser(
        "query", help="Query the local RAG index using Mistral."
    )
    query.add_argument("question", help="Question to ask the RAG tool.")
    query.add_argument("--top-k", type=int, default=None, help="Retrieval top-k.")
    query.add_argument(
        "--topic", action="append", dest="topics", default=[], help="Filter topics."
    )
    query.add_argument(
        "--include-chunks",
        action="store_true",
        help="Include retrieved chunk text in JSON output.",
    )
    query.add_argument(
        "--json",
        action="store_true",
        help="Print full JSON response (default prints only the answer text).",
    )
    return parser


def _cmd_build(args: argparse.Namespace) -> int:
    indexer = _make_indexer(args)
    payload = indexer.build_and_save_index()
    summary = {
        "index_path": str(indexer.index_path),
        "chunk_count": payload.get("chunk_count", 0),
        "files_indexed": payload.get("files_indexed", []),
        "generated_at": payload.get("generated_at"),
        "provider": payload.get("provider"),
        "embedding_model": payload.get("embedding_model"),
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("RAG index rebuild complete")
        print(f"Index: {summary['index_path']}")
        print(f"Chunks: {summary['chunk_count']}")
        print(f"Files: {len(summary['files_indexed'])}")
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    settings = get_settings()
    retriever = _make_retriever(args)
    top_k = args.top_k or settings.rag_top_k_default
    if top_k < 1 or top_k > settings.rag_top_k_max:
        raise SystemExit(f"--top-k must be between 1 and {settings.rag_top_k_max}")

    result = retriever.query(
        query=args.question,
        top_k=top_k,
        topics=args.topics or None,
        include_chunks=args.include_chunks,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print((result.get("answer") or "").strip())
    return 0


def _main(args: argparse.Namespace) -> int:
    if args.command == "build":
        return _cmd_build(args)
    if args.command == "query":
        return _cmd_query(args)
    raise SystemExit(f"Unknown command: {args.command}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return _main(args)


if __name__ == "__main__":
    raise SystemExit(main())
