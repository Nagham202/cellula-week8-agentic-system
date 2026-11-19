import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

import config

FOLLOW_UP_WORDS = {"it", "its", "they", "them", "their", "this", "that", "these", "those",
                   "he", "she", "his", "her", "him", "one", "ones", "same", "other", "above", "previous"}
FOLLOW_UP_STARTS = ("and ", "also ", "what about ", "how about ", "then ")


def connect():
    path = Path(config.CACHE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE IF NOT EXISTS answers "
                       "(key TEXT PRIMARY KEY, reply TEXT NOT NULL, created REAL NOT NULL)")
    return connection


def normalize_question(question):
    text = " ".join(question.lower().split())
    return text.rstrip("?!. ")


def is_follow_up(question):
    text = normalize_question(question)
    words = re.findall(r"[a-z']+", text)
    return text.startswith(FOLLOW_UP_STARTS) or any(word in FOLLOW_UP_WORDS for word in words)


# if any of these change, old answers shouldn't be reused
def answer_settings():
    return [config.CACHE_VERSION, config.LLM_PROVIDER, config.GROQ_MODELS, config.OPENROUTER_MODELS,
            config.OLLAMA_MODEL, config.TOP_K, config.USE_RERANKER, config.USE_QUERY_REWRITER,
            config.MAX_EVIDENCE, config.DENSE_MODEL, config.CHUNK_SIZE, config.CHUNK_OVERLAP]


def answer_cache_key(question, chat_history=None):
    # follow-ups depend on the earlier messages, so they're not cached
    if chat_history and is_follow_up(question):
        return None
    text = json.dumps([normalize_question(question), answer_settings()], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_answer(key):
    if not config.USE_CACHE or key is None:
        return None
    try:
        with connect() as connection:
            row = connection.execute("SELECT reply, created FROM answers WHERE key = ?", (key,)).fetchone()
    except sqlite3.Error:
        return None
    if row is None or time.time() - row[1] > config.CACHE_TTL_SECONDS:
        return None
    return json.loads(row[0])


def save_answer(key, reply):
    if not config.USE_CACHE or key is None:
        return
    try:
        with connect() as connection:
            connection.execute("INSERT OR REPLACE INTO answers VALUES (?, ?, ?)",
                               (key, json.dumps(reply, ensure_ascii=False), time.time()))
    except sqlite3.Error:
        pass


def clear():
    try:
        with connect() as connection:
            connection.execute("DELETE FROM answers")
    except sqlite3.Error:
        pass


def count():
    try:
        with connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM answers").fetchone()[0]
    except sqlite3.Error:
        return 0


# python -m src.cache [clear]
if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["clear"]:
        clear()
        print("Cache cleared")
    print(f"Answers in the cache: {count()}")
