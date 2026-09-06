"""Agentic memory: a SQLite store of every finding, remediation and outcome, with Ollama
embeddings for similarity recall and promotion of repeated successful fixes into 'patterns'.

Self-contained: no external vector DB. Cosine similarity in numpy over the table is fine for the
tens-of-thousands of rows this accumulates. If it ever outgrows that, swap recall() for a call to
a real vector store — nothing else changes."""
from __future__ import annotations

import json
import logging
import sqlite3
import struct
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

log = logging.getLogger("ai-operator.memory")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            REAL NOT NULL,
    kind          TEXT NOT NULL,          -- finding | remediation | outcome | learning
    scope         TEXT NOT NULL,          -- e.g. "Deployment/foo/bar" or a git path
    pattern       TEXT DEFAULT '',        -- stable id once recognised, e.g. "missing-liveness-probe"
    text          TEXT NOT NULL,          -- the human-readable content that gets embedded
    meta          TEXT DEFAULT '{}',      -- JSON blob
    outcome       TEXT DEFAULT '',        -- success | failure | partial | ''
    confidence    REAL DEFAULT 0.0,
    embedding     BLOB                    -- float32[] packed
);
CREATE INDEX IF NOT EXISTS idx_memory_pattern ON memory(pattern);
CREATE INDEX IF NOT EXISTS idx_memory_kind ON memory(kind);
"""


def _pack(vec: list[float]) -> bytes:
    return struct.pack(f"<{len(vec)}f", *vec)


def _unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype="<f4")


@dataclass
class Recall:
    id: int
    kind: str
    scope: str
    pattern: str
    text: str
    outcome: str
    confidence: float
    score: float          # cosine similarity to the query


class Memory:
    def __init__(self, db_path: str) -> None:
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.executescript(_SCHEMA)
        self._db.commit()

    # -- write ------------------------------------------------------------------------------------
    def store(
        self,
        kind: str,
        scope: str,
        text: str,
        embedding: list[float] | None,
        *,
        pattern: str = "",
        meta: dict[str, Any] | None = None,
        outcome: str = "",
        confidence: float = 0.0,
    ) -> int:
        cur = self._db.execute(
            "INSERT INTO memory (ts, kind, scope, pattern, text, meta, outcome, confidence, embedding)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (time.time(), kind, scope, pattern, text, json.dumps(meta or {}), outcome,
             confidence, _pack(embedding) if embedding else None),
        )
        self._db.commit()
        return int(cur.lastrowid)

    def record_outcome(self, mem_id: int, outcome: str, confidence: float = 0.0) -> None:
        self._db.execute(
            "UPDATE memory SET outcome=?, confidence=? WHERE id=?", (outcome, confidence, mem_id)
        )
        self._db.commit()

    # -- read -------------------------------------------------------------------------------------
    def recall(self, query_embedding: list[float] | None, *, k: int = 5,
               kinds: tuple[str, ...] = ("outcome", "learning")) -> list[Recall]:
        """Top-k most similar past entries. If no embedding is available, fall back to most-recent."""
        rows = self._db.execute(
            f"SELECT id, kind, scope, pattern, text, outcome, confidence, embedding FROM memory"
            f" WHERE kind IN ({','.join('?' * len(kinds))}) AND embedding IS NOT NULL",
            kinds,
        ).fetchall()
        if not rows:
            return []
        if query_embedding is None:
            recent = sorted(rows, key=lambda r: r[0], reverse=True)[:k]
            return [Recall(r[0], r[1], r[2], r[3], r[4], r[5], r[6], 0.0) for r in recent]

        q = np.asarray(query_embedding, dtype="f4")
        q /= np.linalg.norm(q) + 1e-9
        scored: list[Recall] = []
        for r in rows:
            v = _unpack(r[7])
            v = v / (np.linalg.norm(v) + 1e-9)
            score = float(np.dot(q, v))
            scored.append(Recall(r[0], r[1], r[2], r[3], r[4], r[5], r[6], score))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:k]

    def patterns(self, *, min_successes: int = 3) -> list[dict[str, Any]]:
        """Patterns with a clean track record — the coordinator may apply these without an LLM call."""
        rows = self._db.execute(
            "SELECT pattern,"
            "  SUM(CASE WHEN outcome='success' THEN 1 ELSE 0 END) AS ok,"
            "  SUM(CASE WHEN outcome='failure' THEN 1 ELSE 0 END) AS bad,"
            "  COUNT(*) AS n"
            " FROM memory WHERE pattern != '' AND kind IN ('outcome','learning')"
            " GROUP BY pattern",
        ).fetchall()
        out = []
        for pattern, ok, bad, n in rows:
            if ok >= min_successes and bad == 0:
                out.append({"pattern": pattern, "successes": ok, "uses": n})
        return sorted(out, key=lambda p: p["successes"], reverse=True)

    def digest(self, *, limit: int = 20) -> dict[str, Any]:
        """Human-readable summary for the agent-memory-digest ConfigMap."""
        total = self._db.execute("SELECT COUNT(*) FROM memory").fetchone()[0]
        by_kind = dict(self._db.execute(
            "SELECT kind, COUNT(*) FROM memory GROUP BY kind").fetchall())
        recent = self._db.execute(
            "SELECT ts, kind, scope, outcome, text FROM memory"
            " WHERE kind IN ('outcome','learning') ORDER BY id DESC LIMIT ?", (limit,),
        ).fetchall()
        return {
            "totalRows": total,
            "byKind": by_kind,
            "patterns": self.patterns(),
            "recent": [
                {"when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r[0])),
                 "kind": r[1], "scope": r[2], "outcome": r[3], "text": r[4][:400]}
                for r in recent
            ],
        }

    def close(self) -> None:
        self._db.close()
