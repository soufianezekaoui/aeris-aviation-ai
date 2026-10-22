from __future__ import annotations

from aeris.evaluation import EvalItem, evaluate, find_unanswerable, load_items
from aeris.rag.embeddings import HashingEmbeddings
from aeris.rag.store import open_store, replace_document

from .test_rag import chunks_for, make_settings


def build(tmp_path):
    st = open_store(make_settings(tmp_path), HashingEmbeddings())
    replace_document(st, "alpha", chunks_for("alpha", "Alpha report"))
    replace_document(st, "beta", chunks_for("beta", "Beta report"))
    return st


def test_metrics_and_refusal(tmp_path):
    st = build(tmp_path)
    items = [
        EvalItem("Why did the takeoff warning system not sound?", "alpha", ("relay",)),
        EvalItem("Which cargo caught fire and produced smoke?", "beta", ("lithium", "pallet")),
        EvalItem("What is the capital of France?", should_refuse=True),
    ]
    (r,) = evaluate(st, items, k=4, thresholds=[0.2])
    assert (r.doc_hit, r.evidence_hit) == (1.0, 1.0)
    assert r.mrr == 1.0 and r.refused == 1.0 and r.unanswerable == []


def test_high_threshold_loses_hits_but_still_refuses(tmp_path):
    st = build(tmp_path)
    items = [EvalItem("Why did the takeoff warning system not sound?", "alpha", ("relay",))]
    low, high = evaluate(st, items, k=4, thresholds=[0.2, 0.99])
    assert low.evidence_hit == 1.0 and high.evidence_hit == 0.0


def test_unanswerable_items_are_flagged_as_broken_tests(tmp_path):
    st = build(tmp_path)
    bad = EvalItem("Question about volcanoes", "alpha", ("volcano",))
    assert find_unanswerable(st, [bad]) == ["Question about volcanoes"]


def test_shipped_question_file_is_well_formed():
    from pathlib import Path

    items = load_items(Path(__file__).parents[1] / "eval" / "questions.jsonl")
    assert len(items) >= 15
    assert sum(i.should_refuse for i in items) >= 3
    assert all(i.expected_doc and i.expected_keywords for i in items if not i.should_refuse)
