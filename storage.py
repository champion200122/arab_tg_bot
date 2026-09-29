import os
import asyncpg

DATABASE_URL = os.environ["DATABASE_URL"]

pool = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    await pool.execute(
        """CREATE TABLE IF NOT EXISTS progress(
            user_id BIGINT NOT NULL,
            word_key TEXT NOT NULL,
            correct INT DEFAULT 0,
            wrong INT DEFAULT 0,
            PRIMARY KEY(user_id, word_key))"""
    )


async def record(user_id: int, word_key: str, ok: int):
    row = await pool.fetchrow(
        "SELECT correct, wrong FROM progress WHERE user_id=$1 AND word_key=$2",
        user_id, word_key
    )
    if row:
        await pool.execute(
            "UPDATE progress SET correct=$1, wrong=$2 WHERE user_id=$3 AND word_key=$4",
            row["correct"] + ok, row["wrong"] + (1 - ok), user_id, word_key
        )
    else:
        await pool.execute(
            "INSERT INTO progress(user_id, word_key, correct, wrong) VALUES($1,$2,$3,$4)",
            user_id, word_key, ok, 1 - ok
        )


async def stats(user_id: int):
    return await pool.fetch(
        "SELECT word_key, correct, wrong FROM progress WHERE user_id=$1",
        user_id
    )
