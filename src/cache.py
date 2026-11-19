import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

import config

# questions with these words usually point back to the conversation ("how do I fix it?")
FOLLOW_UP_WORDS = {"it", "its", "they", "them", "their", "this", "that", "these", "those",
                   "he", "she", "his", "her", "him", "one", "ones", "same", "other", "above", "previous"}
# "and the price?", "what about page 3?" also lean on the question before
FOLLOW_UP_STARTS = ("and ", "also ", "what about ", "how about ", "then ")


def connect():
    path = Path(config.CACHE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE IF NOT EXISTS answers "
                       "(key TEXT PRIMARY KEY, reply TEXT NOT NULL, created REAL NOT NULL)")
    return connection


# "  What does error E31 MEAN? " and "what does error e31 mean" are the same question
def normalize_question(question):
    text = " ".join(question.lower().split())
    return text.rstrip("?!. ")


def is_follow_up(question):
    text = normalize_question(question)
    words = re.findall(r"[a-z']+", text)
    return text.startswith(FOLLOW_UP_STARTS) or any(word in FOLLOW_UP_WORDS for word in words)


# anything that changes how answers are made goes into the key, so a change never returns an old answer
def answer_settings():
    return [config.CACHE_VERSION, config.LLM_PROVIDER, config.GROQ_MODELS, config.OPENROUTER_MODELS,
            config.OLLAMA_MODEL, config.TOP_K, config.USE_RERANKER, config.USE_QUERY_REWRITER,
            config.MAX_EVIDENCE, config.DENSE_MODEL, config.CHUNK_SIZE, config.CHUNK_OVERLAP]


# None means don't use the cache for this question
def answer_cache_key(question, chat_history=None):
    # in a conversation the meaning can depend on earlier messages, so only clear questions are cached
    if chat_history and is_follow_up(question):
        return None
    text = json.dumps([normalize_question(question), answer_settings()], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# the cache only makes things faster, if it fails the app keeps working without it
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


# called whenever documents are added or deleted, old answers may be wrong after that
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


# python -m src.cache          shows how many answers are saved
# python -m src.cache clear    deletes them
if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["clear"]:
        clear()
        print("Cache cleared")
    print(f"Answers in the cache: {count()}")
