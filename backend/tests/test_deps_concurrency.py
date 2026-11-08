from __future__ import annotations

import threading
import time

from aeris.api import deps


def test_concurrent_first_calls_build_the_service_exactly_once(monkeypatch):
    deps.reset_rag_service()
    built = []

    def slow_open_store(settings, embeddings):
        built.append(threading.get_ident())
        time.sleep(0.2)  # widen the race window
        return object()

    monkeypatch.setattr(deps, "open_store", slow_open_store)
    monkeypatch.setattr(deps, "build_embeddings", lambda s: object())
    monkeypatch.setattr(deps, "build_chat_model", lambda s: None)
    monkeypatch.setattr(deps, "RagService", lambda store, llm, settings: object())

    results = []
    barrier = threading.Barrier(8)

    def call():
        barrier.wait()
        results.append(deps.get_rag_service())

    threads = [threading.Thread(target=call) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]

    assert len(built) == 1, f"service was built {len(built)} times"
    assert len({id(r) for r in results}) == 1
    deps.reset_rag_service()


def test_a_failed_build_is_not_cached(monkeypatch):
    deps.reset_rag_service()
    calls = {"n": 0}

    def flaky(settings):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return object()

    monkeypatch.setattr(deps, "build_embeddings", flaky)
    monkeypatch.setattr(deps, "open_store", lambda s, e: object())
    monkeypatch.setattr(deps, "build_chat_model", lambda s: None)
    monkeypatch.setattr(deps, "RagService", lambda store, llm, settings: object())

    try:
        deps.get_rag_service()
    except RuntimeError:
        pass
    assert deps.get_rag_service() is not None  # retried, not stuck on the failure
    deps.reset_rag_service()
