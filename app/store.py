import json
import sqlite3
from pathlib import Path
from uuid import uuid4

class Store:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP);
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                text TEXT NOT NULL, locator TEXT NOT NULL, embedding TEXT NOT NULL, model TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS owner_index ON documents(owner);
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    def add(self, owner, name, chunks, embeddings, model):
        document = str(uuid4())
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT COUNT(*) FROM chunks c JOIN documents d ON c.document_id=d.id WHERE d.owner=?', (owner,)).fetchone()[0]
            if total + len(chunks) > 2000:
                raise ValueError('User quota: at most 2000 chunks; delete older documents')
            db.execute('INSERT INTO documents(id,owner,name) VALUES (?,?,?)', (document,owner,name))
            db.executemany('INSERT INTO chunks VALUES (?,?,?,?,?,?)', [
                (str(uuid4()),document,c['text'],c['locator'],json.dumps(v.tolist()),model)
                for c,v in zip(chunks,embeddings)])
        return document

    def chunks(self, owner):
        with self.connect() as db:
            rows = db.execute('SELECT c.*,d.name FROM chunks c JOIN documents d ON c.document_id=d.id WHERE d.owner=?', (owner,)).fetchall()
        return [dict(row) for row in rows]

    def documents(self, owner):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT id,name,created_at FROM documents WHERE owner=? ORDER BY created_at DESC', (owner,))]

    def delete(self, owner, document):
        with self.connect() as db:
            return db.execute('DELETE FROM documents WHERE id=? AND owner=?', (document,owner)).rowcount > 0
