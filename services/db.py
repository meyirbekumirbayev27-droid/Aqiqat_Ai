"""SQLite дерекқоры: пайдаланушылар, талдау тарихы, ойын нәтижелері."""
import json
import sqlite3

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tool TEXT NOT NULL,
    title TEXT NOT NULL,
    verdict TEXT,
    level TEXT,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON analyses(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    score INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    total INTEGER NOT NULL,
    best_streak INTEGER NOT NULL,
    achievements TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path):
    with sqlite3.connect(path) as conn:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA journal_mode = WAL")


def save_analysis(user_id, tool, title, verdict, level, result):
    db = get_db()
    cur = db.execute(
        "INSERT INTO analyses (user_id, tool, title, verdict, level, result_json) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, tool, title[:160], verdict, level, json.dumps(result, ensure_ascii=False)),
    )
    db.commit()
    return cur.lastrowid
