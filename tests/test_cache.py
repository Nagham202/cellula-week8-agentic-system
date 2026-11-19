import config
from src import cache, chat_graph

HISTORY = [{"role": "user", "content": "What does error E31 mean?"},
           {"role": "assistant", "content": "E31 means the lidar sensor is blocked."}]


def count_calls(monkeypatch, reply):
    calls = []

    class FakeGraph:
        def invoke(self, state):
            calls.append(state["question"])
            return {"answer": reply["answer"], "sources": reply["sources"], "analysis": "some analysis"}

    monkeypatch.setattr(chat_graph, "chat_graph", FakeGraph())
    return calls


def test_same_question_is_answered_from_the_cache(monkeypatch):
    calls = count_calls(monkeypatch, {"answer": "Clean the sensor.", "sources": ["kito_manual.pdf, page 3"]})
    first = chat_graph.ask("What does error E31 mean?")
    second = chat_graph.ask("  what does ERROR e31 mean ")
    assert len(calls) == 1
    assert first["from_cache"] is False
    assert second == {"answer": "Clean the sensor.", "sources": ["kito_manual.pdf, page 3"],
                      "analysis": "some analysis", "from_cache": True}


def test_follow_up_in_a_conversation_is_not_cached(monkeypatch):
    calls = count_calls(monkeypatch, {"answer": "Clean the sensor.", "sources": ["kito_manual.pdf, page 3"]})
    chat_graph.ask("How do I fix it?", HISTORY)
    chat_graph.ask("How do I fix it?", HISTORY)
    assert len(calls) == 2


def test_clear_question_in_a_conversation_uses_the_cache(monkeypatch):
    calls = count_calls(monkeypatch, {"answer": "90 minutes.", "sources": ["kito_manual.pdf, page 1"]})
    chat_graph.ask("How long does the Kito robot take to charge?")
    reply = chat_graph.ask("How long does the Kito robot take to charge?", HISTORY)
    assert len(calls) == 1
    assert reply["from_cache"] is True


def test_answers_without_sources_are_not_cached(monkeypatch):
    calls = count_calls(monkeypatch, {"answer": "I could not find this in the documents.", "sources": []})
    chat_graph.ask("Who is the CEO of Mars?")
    chat_graph.ask("Who is the CEO of Mars?")
    assert len(calls) == 2


def test_cache_is_cleared_when_documents_change(tmp_path, monkeypatch):
    from src.pipeline import store
    monkeypatch.setattr(config, "QDRANT_PATH", str(tmp_path / "qdrant"))
    monkeypatch.setattr(store, "client", None)

    cache.save_answer(cache.answer_cache_key("What is E31?"), {"answer": "x", "sources": ["a.txt"]})
    assert cache.count() == 1
    store.add_chunks([{"source": "a.txt", "type": "txt", "page": None, "section": None, "chapter": None,
                       "chunk_id": "a.txt_c1", "text": "Error E31: lidar blocked."}])
    assert cache.count() == 0

    cache.save_answer(cache.answer_cache_key("What is E31?"), {"answer": "x", "sources": ["a.txt"]})
    store.delete_source("a.txt")
    assert cache.count() == 0


def test_changing_a_setting_misses_the_old_answer(monkeypatch):
    key = cache.answer_cache_key("What is E31?")
    cache.save_answer(key, {"answer": "x", "sources": ["a.txt"]})
    monkeypatch.setattr(config, "LLM_PROVIDER", "openrouter")
    assert cache.get_answer(cache.answer_cache_key("What is E31?")) is None


def test_old_answers_expire(monkeypatch):
    key = cache.answer_cache_key("What is E31?")
    cache.save_answer(key, {"answer": "x", "sources": ["a.txt"]})
    monkeypatch.setattr(config, "CACHE_TTL_SECONDS", -1)
    assert cache.get_answer(key) is None
