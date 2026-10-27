"""Дерекқор: пайдаланушылар, талдау тарихы, ойын нәтижелері.

DATABASE_URL (немесе POSTGRES_URL) берілсе — тұрақты PostgreSQL (мысалы, Neon) қолданылады.
Әйтпесе жергілікті SQLite файлы. Екеуі үшін де SQL сұраулары бірдей: параметрлер «?» арқылы жазылады."""
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import current_app, g

KZ_TZ = timezone(timedelta(hours=5))  # Қазақстан уақыты (UTC+5)

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    title TEXT NOT NULL,
    verdict TEXT,
    level TEXT,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses (user_id, id);
CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    total INTEGER NOT NULL,
    best_streak INTEGER NOT NULL,
    achievements TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
"""
PG_SCHEMA = SQLITE_SCHEMA.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")


def database_url():
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or ""


def is_postgres():
    return database_url().startswith(("postgres://", "postgresql://"))


def now_str():
    return datetime.now(KZ_TZ).strftime("%Y-%m-%d %H:%M:%S")


class _PgConn:
    """psycopg қосылымын sqlite3 интерфейсіне ұқсатады («?» → «%s», жолдарды кілт арқылы оқу)."""

    def __init__(self, url):
        import psycopg
        from psycopg.rows import dict_row
        self._conn = psycopg.connect(url, row_factory=dict_row, connect_timeout=10, prepare_threshold=None)

    def execute(self, sql, params=()):
        return self._conn.execute(sql.replace("?", "%s"), params)

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _connect():
    if is_postgres():
        return _PgConn(database_url())
    conn = sqlite3.connect(current_app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(sqlite_path):
    if is_postgres():
        import psycopg
        with psycopg.connect(database_url(), connect_timeout=10) as conn:
            for stmt in PG_SCHEMA.split(";"):
                if stmt.strip():
                    conn.execute(stmt)
        return
    with sqlite3.connect(sqlite_path) as conn:
        conn.executescript(SQLITE_SCHEMA)
        conn.execute("PRAGMA journal_mode = WAL")


def insert(sql, params):
    """INSERT орындап, жаңа жолдың id-ін қайтарады."""
    db = get_db()
    if is_postgres():
        row = db.execute(sql + " RETURNING id", params).fetchone()
        db.commit()
        return row["id"]
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def save_analysis(user_id, tool, title, verdict, level, result):
    return insert(
        "INSERT INTO analyses (user_id, tool, title, verdict, level, result_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, tool, title[:160], verdict, level, json.dumps(result, ensure_ascii=False), now_str()),
    )
