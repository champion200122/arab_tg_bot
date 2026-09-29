import os
import sqlite3
import threading

DB_PATH = os.environ.get("DB_PATH", "data.db")
_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.execute(
        """CREATE TABLE IF NOT EXISTS progress(
            user_id INTEGER NOT NULL,
            word_key TEXT NOT NULL,
            correct INTEGER DEFAULT 0,
            wrong INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, word_key))"""
    )
    return c


def record(user_id: int, word_key: str, ok: int):
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT correct, wrong FROM progress WHERE user_id=? AND word_key=?",
            (user_id, word_key),
        ).fetchone()
        if row:
            cr, wr = row
            c.execute(
                "UPDATE progress SET correct=?, wrong=? WHERE user_id=? AND word_key=?",
                (cr + ok, wr + (1 - ok), user_id, word_key),
            )
        else:
            c.execute(
                "INSERT INTO progress(user_id, word_key, correct, wrong) VALUES(?,?,?,?)",
                (user_id, word_key, ok, 1 - ok),
            )


def stats(user_id: int):
    with _lock, _conn() as c:
        return c.execute(
            "SELECT word_key, correct, wrong FROM progress WHERE user_id=?",
            (user_id,),
        ).fetchall()
