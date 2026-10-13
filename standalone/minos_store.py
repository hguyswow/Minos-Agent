# -*- coding: utf-8 -*-
"""
Minos SQLite Storage Engine (Enterprise v5.0).
Provides process-safe, WAL-mode SQLite storage for Minos memory, pins, projects,
knowledge graph, and episodic memory with FTS5 trigram + Korean Bi-gram search.
"""
from __future__ import annotations

import os
import re
import json
import time
import sqlite3
import threading
import logging
from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from rank_bm25 import BM25Plus
except ImportError:
    BM25Plus = None

logger = logging.getLogger(__name__)


def tokenize_korean_bigram(text: str) -> List[str]:
    """Korean Subword Bi-gram tokenizer (exact match with Minos specification)."""
    if not text:
        return []
    tokens = []
    for w in text.split():
        w_lower = w.lower()
        tokens.append(w_lower)
        clean_word = re.sub(r"[^\w가-힣]", "", w_lower)
        n = len(clean_word)
        if n >= 2:
            tokens.extend(clean_word[i:i + 2] for i in range(n - 1))
        if n >= 3:
            tokens.extend(clean_word[i:i + 3] for i in range(n - 2))
    return tokens


_SCHEMA_STATEMENTS = [
    "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS pins (id INTEGER PRIMARY KEY AUTOINCREMENT, fact TEXT NOT NULL UNIQUE, created_at REAL)",
    "CREATE TABLE IF NOT EXISTS projects (name TEXT PRIMARY KEY, status TEXT, details TEXT, updated_at TEXT)",
    "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, value TEXT)",
    "CREATE TABLE IF NOT EXISTS nodes (name TEXT PRIMARY KEY, type TEXT, attributes TEXT)",
    ("CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, relation TEXT, target TEXT, "
     "UNIQUE(source, relation, target))"),
    ("CREATE TABLE IF NOT EXISTS episodes (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, role TEXT, content TEXT, "
     "session_id TEXT, author_id TEXT, trusted INTEGER DEFAULT 1)"),
    ("CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(content, content='episodes', content_rowid='id', tokenize='trigram')"),
    ("CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN "
     "INSERT INTO episodes_fts(rowid, content) VALUES (new.id, new.content); END"),
    ("CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN "
     "INSERT INTO episodes_fts(episodes_fts, rowid, content) VALUES ('delete', old.id, old.content); END"),
    ("CREATE TRIGGER IF NOT EXISTS episodes_au AFTER UPDATE ON episodes BEGIN "
     "INSERT INTO episodes_fts(episodes_fts, rowid, content) VALUES ('delete', old.id, old.content); "
     "INSERT INTO episodes_fts(rowid, content) VALUES (new.id, new.content); END"),
    "INSERT OR IGNORE INTO meta (key, value) VALUES ('schema_version', '1')",
]


# Secret redaction shared by every Minos engine (Hermes plugin, standalone, legacy)
_SECRET_PATTERNS = [
    re.compile(r"\b\d{8,10}:AA[A-Za-z0-9_-]{30,}"),                    # Telegram bot token
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{16,}"),                    # OpenAI / Anthropic style keys
    re.compile(r"\bAIza[0-9A-Za-z_-]{35}"),                             # Google API key
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                                # AWS access key id
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),                      # Slack token
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),  # JWT
]
_KEYWORD_SECRET = re.compile(
    r"(?i)((?:password|passwd|pwd|passcode|api[_ -]?key|secret|token|비밀번호|비번|암호)\s*[:=]\s*)([^\s,;]+)")
_NUMERIC_PIN = re.compile(r"(?i)((?:\bPIN|핀\s?번호|비밀번호|비번|암호)\s*(?:은|는|:|=)?\s*)(\d{4,8})\b")
_APP_PASSWORD = re.compile(r"\b[a-z]{4} [a-z]{4} [a-z]{4} [a-z]{4}\b")
_APP_PASSWORD_HINT = re.compile(r"(?i)(app\s?password|앱\s?비밀번호|비밀번호|password)")


def redact_secrets(text: str) -> str:
    """Mask credentials before anything is stored or re-injected into a prompt."""
    if not text:
        return text
    out = text
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub("[REDACTED]", out)
    out = _KEYWORD_SECRET.sub(lambda m: m.group(1) + "[REDACTED]", out)
    out = _NUMERIC_PIN.sub(lambda m: m.group(1) + "[REDACTED]", out)
    lines = []
    for line in out.split("\n"):
        # an app password sent on its own line ("abcd efgh ijkl mnop") or next to a password hint
        if _APP_PASSWORD_HINT.search(line) or _APP_PASSWORD.fullmatch(line.strip()):
            line = _APP_PASSWORD.sub("[REDACTED]", line)
        lines.append(line)
    return "\n".join(lines)


class MinosStore:
    """SQLite-backed persistent store for Minos memory engine."""

    def __init__(self, db_path: str):
        self._db_path = os.path.abspath(db_path)
        parent_dir = os.path.dirname(self._db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        self._lock = threading.RLock()
        self._in_tx = False

        self._conn = sqlite3.connect(
            self._db_path,
            timeout=10,
            isolation_level=None,
            check_same_thread=False
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=10000")
        self._conn.execute("PRAGMA synchronous=NORMAL")

        self._init_schema()

    def _init_schema(self) -> None:
        for stmt in _SCHEMA_STATEMENTS:
            self._conn.execute(stmt)

    @contextmanager
    def _transaction(self):
        """Execute operations inside an explicit BEGIN IMMEDIATE transaction with retry."""
        if self._in_tx:
            yield
            return
        self._in_tx = True
        max_retries = 50
        for attempt in range(max_retries):
            try:
                self._conn.execute("BEGIN IMMEDIATE")
                break
            except sqlite3.OperationalError as e:
                err_msg = str(e).lower()
                if "locked" in err_msg or "busy" in err_msg:
                    if attempt == max_retries - 1:
                        self._in_tx = False
                        raise
                    time.sleep(0.01 * (1 + attempt * 0.2))
                else:
                    self._in_tx = False
                    raise
        try:
            yield
            self._conn.execute("COMMIT")
        except Exception:
            try:
                self._conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            self._in_tx = False

    def schema_version(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT value FROM meta WHERE key = 'schema_version'")
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else 1

    def journal_mode(self) -> str:
        with self._lock:
            cur = self._conn.execute("PRAGMA journal_mode")
            row = cur.fetchone()
            return str(row[0]) if row else ""

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except Exception:
                pass

    # --- Pins API ---

    def list_pins(self) -> List[str]:
        with self._lock:
            rows = self._conn.execute("SELECT fact FROM pins ORDER BY id ASC").fetchall()
            return [r[0] for r in rows]

    def add_pin(self, fact: str) -> bool:
        with self._lock:
            try:
                with self._transaction():
                    self._conn.execute(
                        "INSERT INTO pins (fact, created_at) VALUES (?, ?)",
                        (fact, time.time())
                    )
                return True
            except sqlite3.IntegrityError:
                return False

    def remove_pin(self, fact: str) -> bool:
        with self._lock:
            with self._transaction():
                cur = self._conn.execute("DELETE FROM pins WHERE fact = ?", (fact,))
                return cur.rowcount > 0

    def replace_pin(self, old: str, new: str) -> bool:
        with self._lock:
            try:
                with self._transaction():
                    cur = self._conn.execute(
                        "UPDATE pins SET fact = ? WHERE fact = ?",
                        (new, old)
                    )
                    return cur.rowcount > 0
            except sqlite3.IntegrityError:
                return False

    # --- Projects API ---

    def upsert_project(self, name: str, status: str, details: str) -> None:
        with self._lock:
            with self._transaction():
                updated_at = time.strftime("%Y-%m-%d %H:%M")
                self._conn.execute(
                    "INSERT INTO projects (name, status, details, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(name) DO UPDATE SET status=excluded.status, details=excluded.details, updated_at=excluded.updated_at",
                    (name, status, details, updated_at)
                )

    def set_project_raw(self, name: str, status: str, details: str, updated_at: str) -> None:
        with self._lock:
            with self._transaction():
                self._conn.execute(
                    "INSERT INTO projects (name, status, details, updated_at) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(name) DO UPDATE SET status=excluded.status, details=excluded.details, updated_at=excluded.updated_at",
                    (name, status, details, updated_at)
                )

    def list_projects(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT name, status, details, updated_at FROM projects"
            ).fetchall()
            return {
                r[0]: {"status": r[1], "details": r[2], "updated_at": r[3]}
                for r in rows
            }

    # --- KV API ---

    def get_semantic(self) -> str:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE key = 'semantic_memory'"
            ).fetchone()
            return str(row[0]) if row and row[0] is not None else ""

    def set_semantic(self, text: str) -> None:
        with self._lock:
            with self._transaction():
                self._conn.execute(
                    "INSERT INTO kv (key, value) VALUES ('semantic_memory', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (text,)
                )

    def get_working(self) -> list:
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM kv WHERE key = 'working_memory'"
            ).fetchone()
            if row and row[0]:
                try:
                    return json.loads(row[0])
                except Exception:
                    return []
            return []

    def set_working(self, messages: list) -> None:
        with self._lock:
            with self._transaction():
                val = json.dumps(messages, ensure_ascii=False)
                self._conn.execute(
                    "INSERT INTO kv (key, value) VALUES ('working_memory', ?) "
                    "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (val,)
                )

    # --- Graph API ---

    def add_edge(self, source: str, relation: str, target: str) -> bool:
        with self._lock:
            with self._transaction():
                self._conn.execute(
                    "INSERT OR IGNORE INTO nodes (name, type, attributes) VALUES (?, 'auto', '{}')",
                    (source,)
                )
                self._conn.execute(
                    "INSERT OR IGNORE INTO nodes (name, type, attributes) VALUES (?, 'auto', '{}')",
                    (target,)
                )
                cur = self._conn.execute(
                    "INSERT OR IGNORE INTO edges (source, relation, target) VALUES (?, ?, ?)",
                    (source, relation, target)
                )
                return cur.rowcount > 0

    def set_node_attribute(self, name: str, key: str, value: Any) -> None:
        with self._lock:
            with self._transaction():
                row = self._conn.execute(
                    "SELECT attributes FROM nodes WHERE name = ?",
                    (name,)
                ).fetchone()
                if row:
                    try:
                        attrs = json.loads(row[0]) if row[0] else {}
                    except Exception:
                        attrs = {}
                    attrs[key] = value
                    self._conn.execute(
                        "UPDATE nodes SET attributes = ? WHERE name = ?",
                        (json.dumps(attrs, ensure_ascii=False), name)
                    )
                else:
                    attrs = {key: value}
                    self._conn.execute(
                        "INSERT INTO nodes (name, type, attributes) VALUES (?, 'auto', ?)",
                        (name, json.dumps(attrs, ensure_ascii=False))
                    )

    def ensure_node(self, name: str, type: str = "auto", attributes: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            with self._transaction():
                attrs_json = json.dumps(attributes or {}, ensure_ascii=False)
                self._conn.execute(
                    "INSERT OR IGNORE INTO nodes (name, type, attributes) VALUES (?, ?, ?)",
                    (name, type, attrs_json)
                )

    def get_graph(self) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
        with self._lock:
            node_rows = self._conn.execute(
                "SELECT name, type, attributes FROM nodes"
            ).fetchall()
            nodes = {}
            for name, ntype, attrs_str in node_rows:
                try:
                    attrs = json.loads(attrs_str) if attrs_str else {}
                except Exception:
                    attrs = {}
                nodes[name] = {"type": ntype, "attributes": attrs}

            edge_rows = self._conn.execute(
                "SELECT source, relation, target FROM edges ORDER BY id ASC"
            ).fetchall()
            edges = [
                {"source": r[0], "relation": r[1], "target": r[2]}
                for r in edge_rows
            ]
            return nodes, edges

    # --- Episodes API ---

    def add_episode(
        self,
        ts: float,
        role: str,
        content: str,
        *,
        session_id: str = "",
        author_id: str = "",
        trusted: bool = True
    ) -> None:
        with self._lock:
            with self._transaction():
                self._conn.execute(
                    "INSERT INTO episodes (ts, role, content, session_id, author_id, trusted) VALUES (?, ?, ?, ?, ?, ?)",
                    (float(ts), str(role), str(content), str(session_id), str(author_id), 1 if trusted else 0)
                )

    def count_episodes(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
            return int(row[0]) if row else 0

    def delete_episodes_containing(self, text: str) -> int:
        with self._lock:
            with self._transaction():
                cur = self._conn.execute(
                    "DELETE FROM episodes WHERE instr(content, ?) > 0",
                    (text,)
                )
                return cur.rowcount

    def rewrite_episodes(self, fn: Callable[[str], str]) -> int:
        with self._lock:
            with self._transaction():
                rows = self._conn.execute("SELECT id, content FROM episodes").fetchall()
                changed = 0
                for row_id, content in rows:
                    new_content = fn(content)
                    if new_content != content:
                        self._conn.execute(
                            "UPDATE episodes SET content = ? WHERE id = ?",
                            (new_content, row_id)
                        )
                        changed += 1
                return changed

    # --- Search API ---

    def search(self, query: str, limit: int = 3) -> List[Tuple[str, float]]:
        if not (query or "").strip():
            return []

        q_tokens = tokenize_korean_bigram(query)
        q = set(q_tokens)
        if not q:
            return []

        with self._lock:
            words = [re.sub(r"[^\w가-힣]", "", w.lower()) for w in query.split()]
            words = [w for w in words if w]

            candidates: Dict[int, Tuple[str, float]] = {}

            # Len >= 3: FTS phrase query
            fts_phrases: List[str] = []
            for w in words:
                if len(w) >= 3:
                    for i in range(len(w) - 2):
                        sub = w[i:i + 3]
                        escaped = sub.replace('"', '""')
                        fts_phrases.append(f'"{escaped}"')

            if fts_phrases:
                fts_query = " OR ".join(fts_phrases)
                try:
                    cur = self._conn.execute(
                        "SELECT e.id, e.content, e.ts FROM episodes_fts f JOIN episodes e ON e.id = f.rowid "
                        "WHERE episodes_fts MATCH ? AND e.trusted = 1 ORDER BY f.rank LIMIT 500",
                        (fts_query,)
                    )
                    for row in cur.fetchall():
                        candidates[row[0]] = (row[1], float(row[2]))
                except sqlite3.OperationalError as e:
                    logger.debug(f"[MinosStore] FTS search query error: {e}")

            # Len == 2: exact substring match via instr
            two_letter_words = set(w for w in words if len(w) == 2)
            for w in two_letter_words:
                cur = self._conn.execute(
                    "SELECT id, content, ts FROM episodes WHERE trusted = 1 AND instr(lower(content), ?) > 0 "
                    "ORDER BY id DESC LIMIT 200",
                    (w,)
                )
                for row in cur.fetchall():
                    candidates[row[0]] = (row[1], float(row[2]))

            if not candidates:
                return []

            # Collapse identical contents, keeping the newest ts
            collapsed: Dict[str, float] = {}
            for content, ts in candidates.values():
                if content not in collapsed or ts > collapsed[content]:
                    collapsed[content] = ts

            # Rank by query overlap and BM25Plus
            len_q = len(q)
            kept: List[Tuple[str, float, List[str], float]] = []
            for content, ts in collapsed.items():
                c_tokens = tokenize_korean_bigram(content)
                overlap = len(q & set(c_tokens)) / len_q
                if overlap >= 0.3:
                    kept.append((content, ts, c_tokens, overlap))

            if not kept:
                return []

            if BM25Plus is not None:
                try:
                    corpus = [item[2] for item in kept]
                    bm25 = BM25Plus(corpus)
                    scores = bm25.get_scores(q_tokens)
                except Exception:
                    scores = [item[3] for item in kept]
            else:
                scores = [item[3] for item in kept]

            ranked = []
            for i, item in enumerate(kept):
                content, ts, _, overlap = item
                score = scores[i] if i < len(scores) else overlap
                ranked.append((score, ts, content))

            ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
            return [(c, ts) for _, ts, c in ranked[:limit]]

    # --- Migration API ---

    def migrate_from_v4(self, directory: str) -> Dict[str, int]:
        with self._lock:
            row = self._conn.execute("SELECT value FROM meta WHERE key = 'migrated_v4'").fetchone()
            if row:
                return {}

            mem_file = os.path.join(directory, "minos_memory.json")
            graph_file = os.path.join(directory, "minos_graph.json")
            epi_file = os.path.join(directory, "minos_episodic.jsonl")

            pins_data: List[str] = []
            projects_data: Dict[str, Dict[str, Any]] = {}
            semantic_data = ""
            working_data = None
            if os.path.exists(mem_file):
                try:
                    with open(mem_file, "r", encoding="utf-8") as f:
                        m_data = json.load(f)
                        pins_data = list(m_data.get("pinned_memories", []))
                        projects_data = dict(m_data.get("projects", {}))
                        semantic_data = str(m_data.get("semantic_memory", ""))
                        working_data = list(m_data.get("working_memory", []))
                except Exception as e:
                    logger.warning(f"[MinosStore] Failed to read {mem_file}: {e}")

            nodes_data: Dict[str, Dict[str, Any]] = {}
            edges_data: List[Dict[str, str]] = []
            if os.path.exists(graph_file):
                try:
                    with open(graph_file, "r", encoding="utf-8") as f:
                        g_data = json.load(f)
                        nodes_data = dict(g_data.get("nodes", {}))
                        edges_data = list(g_data.get("edges", []))
                except Exception as e:
                    logger.warning(f"[MinosStore] Failed to read {graph_file}: {e}")

            episodes_data: List[Dict[str, Any]] = []
            if os.path.exists(epi_file):
                try:
                    with open(epi_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line_s = line.strip()
                            if not line_s:
                                continue
                            try:
                                d = json.loads(line_s)
                                episodes_data.append({
                                    "ts": float(d.get("timestamp") or 0.0),
                                    "role": str(d.get("role") or ""),
                                    "content": str(d.get("content") or ""),
                                    "session_id": str(d.get("session_id") or ""),
                                    "author_id": str(d.get("author_id") or ""),
                                    "trusted": 1 if d.get("trusted", True) else 0,
                                })
                            except Exception:
                                continue
                except Exception as e:
                    logger.warning(f"[MinosStore] Failed to read {epi_file}: {e}")

            with self._transaction():
                pins_count = 0
                for pin in pins_data:
                    cur = self._conn.execute(
                        "INSERT OR IGNORE INTO pins (fact, created_at) VALUES (?, ?)",
                        (pin, time.time())
                    )
                    if cur.rowcount > 0:
                        pins_count += 1

                proj_count = 0
                for pname, pinfo in projects_data.items():
                    pstatus = pinfo.get("status", "")
                    pdetails = pinfo.get("details", "")
                    pupdated = pinfo.get("updated_at") or time.strftime("%Y-%m-%d %H:%M")
                    self._conn.execute(
                        "INSERT INTO projects (name, status, details, updated_at) VALUES (?, ?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET status=excluded.status, details=excluded.details, updated_at=excluded.updated_at",
                        (pname, pstatus, pdetails, pupdated)
                    )
                    proj_count += 1

                if semantic_data:
                    self._conn.execute(
                        "INSERT INTO kv (key, value) VALUES ('semantic_memory', ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (semantic_data,)
                    )

                if working_data is not None:
                    self._conn.execute(
                        "INSERT INTO kv (key, value) VALUES ('working_memory', ?) "
                        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (json.dumps(working_data, ensure_ascii=False),)
                    )

                nodes_count = 0
                for nname, ninfo in nodes_data.items():
                    ntype = ninfo.get("type", "auto")
                    nattrs = ninfo.get("attributes") or {}
                    self._conn.execute(
                        "INSERT INTO nodes (name, type, attributes) VALUES (?, ?, ?) "
                        "ON CONFLICT(name) DO UPDATE SET type=excluded.type, attributes=excluded.attributes",
                        (nname, ntype, json.dumps(nattrs, ensure_ascii=False))
                    )
                    nodes_count += 1

                edges_count = 0
                for edge in edges_data:
                    src = edge.get("source", "")
                    rel = edge.get("relation", "")
                    tgt = edge.get("target", "")
                    self._conn.execute(
                        "INSERT OR IGNORE INTO nodes (name, type, attributes) VALUES (?, 'auto', '{}')",
                        (src,)
                    )
                    self._conn.execute(
                        "INSERT OR IGNORE INTO nodes (name, type, attributes) VALUES (?, 'auto', '{}')",
                        (tgt,)
                    )
                    cur = self._conn.execute(
                        "INSERT OR IGNORE INTO edges (source, relation, target) VALUES (?, ?, ?)",
                        (src, rel, tgt)
                    )
                    if cur.rowcount > 0:
                        edges_count += 1

                episodes_count = 0
                for ep in episodes_data:
                    self._conn.execute(
                        "INSERT INTO episodes (ts, role, content, session_id, author_id, trusted) VALUES (?, ?, ?, ?, ?, ?)",
                        (ep["ts"], ep["role"], ep["content"], ep["session_id"], ep["author_id"], ep["trusted"])
                    )
                    episodes_count += 1

                self._conn.execute(
                    "INSERT OR REPLACE INTO meta (key, value) VALUES ('migrated_v4', ?)",
                    (str(time.time()),)
                )

            # After commit, rename each source file that existed to <name>.v4_backup
            for src_file in [mem_file, graph_file, epi_file]:
                if os.path.exists(src_file):
                    os.replace(src_file, src_file + ".v4_backup")

            return {
                "pins": pins_count,
                "projects": proj_count,
                "episodes": episodes_count,
                "nodes": nodes_count,
                "edges": edges_count,
            }
