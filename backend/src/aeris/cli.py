# command-line interface for AERIS: prepare, ingest, ask, eval

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from aeris.config import get_settings
from aeris.evaluation import evaluate, load_items
from aeris.ingestion.manifest import DocumentEntry, load_manifest
from aeris.ingestion.pipeline import prepare_document
from aeris.rag.embeddings import build_embeddings
from aeris.rag.errors import ConfigError, IndexEmptyError, IndexMismatchError
from aeris.rag.llm import build_chat_model
from aeris.rag.service import RagService
from aeris.rag.store import index_stats, open_store, replace_document, reset_store


def _select(entries: list[DocumentEntry], doc_ids: list[str] | None) -> list[DocumentEntry]:
    if not doc_ids:
        return entries
    known = {e.doc_id: e for e in entries}
    missing = [d for d in doc_ids if d not in known]
    if missing:
        raise SystemExit(f"unknown --doc id(s): {missing}. Known: {sorted(known)}")
    return [known[d] for d in doc_ids]


def _cmd_prepare(args: argparse.Namespace) -> int:
    settings = get_settings()
    entries = _select(load_manifest(settings.manifest_path).documents, args.doc)
    for entry in entries:
        chunks, rep = prepare_document(entry, settings)
        print(f"== {entry.doc_id}  ({rep.pdf.name})")
        print(f"   pages: {rep.pages_total}  empty/no-text: {len(rep.pages_empty)}  "
              f"failed: {len(rep.pages_failed)}  with TOC lines removed: {len(rep.pages_toc)}")
        print(f"   running headers/footers removed: {rep.boilerplate_removed or 'none'}")
        print(f"   chunks: {rep.chunks}  avg size: {rep.avg_chunk_chars} chars  "
              f"({rep.seconds}s)  pdf created: {rep.pdf_created}")
        for chunk in chunks[args.skip : args.skip + args.show]:
            m = chunk.metadata
            print(f"\n   --- {chunk.chunk_id}  page {m['page']}  section: {m['section'] or '-'}")
            print("   " + chunk.text[:600].replace("\n", "\n   "))
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    settings = get_settings()
    entries = _select(load_manifest(settings.manifest_path).documents, args.doc)
    if args.reset:
        reset_store(settings)
        print("index reset")
    store = open_store(settings, build_embeddings(settings))
    for entry in entries:
        chunks, rep = prepare_document(entry, settings)
        print(f"{entry.doc_id}: {rep.pages_total} pages -> {rep.chunks} chunks; embedding...")
        replace_document(store, entry.doc_id, chunks)
        print("   indexed")
    stats = index_stats(store)
    print(f"done. index now holds {stats.chunks} chunks: {stats.documents}")
    return 0


def _cmd_stats(_: argparse.Namespace) -> int:
    settings = get_settings()
    stats = index_stats(open_store(settings, build_embeddings(settings)))
    print(f"chunks: {stats.chunks}")
    for doc_id, n in sorted(stats.documents.items()):
        print(f"  {doc_id}: {n}")
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    settings = get_settings()
    store = open_store(settings, build_embeddings(settings))
    result = RagService(store, build_chat_model(settings), settings).ask(
        args.question, args.top_k, args.doc
    )
    print(f"[{result.status}]")
    if result.answer:
        print(result.answer)
    for w in result.warnings:
        print(f"! {w}")
    for s in result.sources:
        mark = "*" if s.cited else " "
        where = f"PDF p.{s.page}" + (f", {s.section}" if s.section else "")
        print(f"\n {mark}[{s.id}] {s.doc_id} ({where})  relevance {s.score}")
        print("    " + s.text[:300].replace("\n", " ") + ("..." if len(s.text) > 300 else ""))
    return 0


def _cmd_eval(args: argparse.Namespace) -> int:
    settings = get_settings()
    store = open_store(settings, build_embeddings(settings))
    items = load_items(args.questions)
    k = args.top_k or settings.retrieval_top_k
    thresholds = [round(t / 100, 2) for t in range(10, 71, 5)] if args.sweep else [
        settings.min_relevance
    ]
    results = evaluate(store, items, k, thresholds)
    print(f"embedding: {settings.embedding_provider}  top_k={k}  "
          f"questions: {results[0].positives} answerable + {results[0].negatives} out-of-corpus")
    for bad in results[0].unanswerable:
        print(f"WARNING unanswerable eval item (evidence not in index): {bad}")
    print(f"{'min_relevance':>13} {'doc_hit@k':>10} {'evidence@k':>11} {'MRR':>6} {'refused':>8}")
    for r in results:
        print(f"{r.threshold:>13} {r.doc_hit:>10.0%} {r.evidence_hit:>11.0%} "
              f"{r.mrr:>6.2f} {r.refused:>8.0%}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aeris", description="AERIS command-line tools")
    sub = parser.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare", help="dry run: extract, clean and chunk (no embeddings)")
    prep.add_argument("--doc", action="append", help="doc_id to process (repeatable)")
    prep.add_argument("--show", type=int, default=0, help="print N sample chunks")
    prep.add_argument("--skip", type=int, default=0, help="skip the first N chunks when showing")
    prep.set_defaults(func=_cmd_prepare)

    ing = sub.add_parser("ingest", help="embed documents and write them to the vector store")
    ing.add_argument("--doc", action="append", help="doc_id to ingest (repeatable)")
    ing.add_argument("--reset", action="store_true", help="wipe the index first")
    ing.set_defaults(func=_cmd_ingest)

    st = sub.add_parser("stats", help="show what is indexed")
    st.set_defaults(func=_cmd_stats)

    ask = sub.add_parser("ask", help="ask a question from the terminal")
    ask.add_argument("question")
    ask.add_argument("--top-k", type=int)
    ask.add_argument("--doc", action="append", help="restrict to a doc_id (repeatable)")
    ask.set_defaults(func=_cmd_ask)

    ev = sub.add_parser("eval", help="retrieval evaluation against eval/questions.jsonl")
    ev.add_argument("--questions", type=Path, default=Path("eval/questions.jsonl"))
    ev.add_argument("--top-k", type=int)
    ev.add_argument("--sweep", action="store_true", help="show metrics across thresholds")
    ev.set_defaults(func=_cmd_eval)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, IndexMismatchError, IndexEmptyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
