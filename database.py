import sqlite3
import os
from flask import g

DB_PATH = os.path.join(os.path.dirname(__file__), 'shopify_agent.db')

def get_db():
    if 'db' not in g:
        conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    schema_file = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_file, 'r') as f:
        db.executescript(f.read())
    # Ensure conversations.title column exists
    cols = [row['name'] for row in db.execute("PRAGMA table_info(conversations)").fetchall()]
    if 'title' not in cols:
        db.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
        db.commit()
