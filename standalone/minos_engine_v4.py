# -*- coding: utf-8 -*-
"""
Minos Memory & Knowledge Operating Engine v4.2 (Standalone Portable Edition).

Designed for seamless porting to any AI Agent framework (LangChain, AutoGPT, LlamaIndex, custom bots).
Provides:
1. Knowledge Graph Subsystem (Entity-Relationship graph)
2. Pinned Permanent Facts (Zero time-decay)
3. Korean Subword Bi-gram BM25Plus RAG (Particle/Josa immune)
4. ChromaDB Vector Episodic Store with Time-Decay Re-ranking
5. Active Project Dashboard
6. Windows PC Hardware & Health Diagnostics
7. Audiobook ID3v2 & Album Art Auto-Tagger
8. Safe PC System Controller (Volume, Mute, Lock, App Launcher)
"""
from __future__ import annotations
import os
import json
import time
import requests
import re
import math
import shutil
import threading
import logging
import uuid
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MinosEngine")

# Optional dependencies check
try:
    from rank_bm25 import BM25Plus, BM25Okapi
    BM25_CLASS = BM25Plus
except ImportError:
    try:
        from rank_bm25 import BM25Okapi
        BM25_CLASS = BM25Okapi
    except ImportError:
        BM25_CLASS = None

try:
    import chromadb
except ImportError:
    chromadb = None


# Tuning Constants
EMBEDDING_HTTP_TIMEOUT = 1.2       # Max latency for query-time embeddings (user is waiting)
EMBEDDING_INDEX_TIMEOUT = 15.0     # Background indexing may wait for a cold model load
MIN_INDEX_CHAR_LEN = 8             # Minimum characters for vector indexing
BM25_MAX_SLIDING_WINDOW = 2500     # Maximum entries for sliding-window BM25
BM25_MIN_TOKEN_OVERLAP = 0.3       # Share of query tokens a doc must contain to count as relevant
VECTOR_MIN_COSINE = 0.45           # Vector hits below this cosine similarity are treated as noise
RRF_K = 60                         # Reciprocal Rank Fusion constant
MAX_MEMORY_SNIPPET_CHARS = 500     # Long past answers are clipped before prompt injection
RECENCY_HALFLIFE_DAYS = 14.0       # Exponential time-decay half-life
COLLECTION_NAME = "minos_episodic"
LEGACY_COLLECTION_NAME = "episodic"


def clean_cot_and_tags(text: str) -> str:
    """Clean reasoning/thought tags and prompt leakages from LLM text."""
    if not text:
        return ""
    cleaned = text
    cleaned = re.sub(r"<\|channel\>thought[\s\S]*?<channel\|>", "", cleaned)
    cleaned = re.sub(r"<\|channel\>thought[\s\S]*$", "", cleaned)
    cleaned = re.sub(r"^[\s\S]*?<channel\|>", "", cleaned)
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned)
    cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned)
    cleaned = re.sub(r"^[\s\S]*?</think>", "", cleaned)

    valid_lines = []
    for raw_line in cleaned.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(lower.startswith(prefix) for prefix in (
            "* format:", "* input:", "* task:", "* constraint:",
            "* role:", "* focus:", "* fact 1:", "* fact 2:", "* fact 3:",
            "* 3 lines", "* bullet", "* no intro", "* core facts",
            "3 lines or less?", "bullet points?", "no intro/outro?",
            "core facts/context?"
        )):
            continue
        valid_lines.append(line)
    return "\n".join(valid_lines).strip()


def tokenize_korean_bigram(text: str) -> List[str]:
    """Tokenize Korean/multilingual text into words and 2/3-character n-grams.
    
    Immune to Korean grammatical particles (~을/를/에서/으로/했던).
    """
    if not text:
        return []
    tokens: List[str] = []
    words = text.split()
    for w in words:
        w_lower = w.lower()
        tokens.append(w_lower)
        clean_word = re.sub(r"[^\w가-힣]", "", w_lower)
        word_len = len(clean_word)
        if word_len >= 2:
            for i in range(word_len - 1):
                tokens.append(clean_word[i:i+2])
        if word_len >= 3:
            for i in range(word_len - 2):
                tokens.append(clean_word[i:i+3])
    return tokens


def should_index_content(text: str) -> bool:
    if not text:
        return False
    clean = text.strip()
    if len(clean) < MIN_INDEX_CHAR_LEN:
        return False
    lower = clean.lower()
    noise = {
        "응", "어", "네", "아니", "오키", "알겠어", "고마워", "감사", "감사합니다",
        "그래", "좋아", "안녕", "안녕하세요", "하이", "ㅋㅋ", "ㅎㅎ", "ㅋㅋㅋ", "ㅎㅎㅎ",
        "ok", "okay", "yes", "no", "thanks", "thx", "sure", "cool"
    }
    return lower not in noise


def compute_recency_score(timestamp: float, halflife_days: float = RECENCY_HALFLIFE_DAYS) -> float:
    if not timestamp or timestamp <= 0:
        return 0.5
    age_seconds = max(0.0, time.time() - timestamp)
    age_days = age_seconds / 86400.0
    return math.pow(0.5, age_days / halflife_days)


def clip_snippet(text: str, limit: int = MAX_MEMORY_SNIPPET_CHARS) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit].rstrip() + " …(생략)"


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


class InterProcessLock:
    """Exclusive lock on a sidecar file, shared by every process using the same storage dir.

    threading.Lock only protects one process; WebUI, Telegram bot and Hermes plugin each
    run in their own process against the same files, so writes must also hold this lock.
    """

    def __init__(self, path: str):
        self._path = path
        self._fh = None

    def __enter__(self):
        self._fh = open(self._path, "a+b")
        if os.name == "nt":
            import msvcrt
            while True:
                try:
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_LOCK, 1)
                    break
                except OSError:
                    # LK_LOCK gives up after ~10s; keep waiting
                    continue
        else:
            import fcntl
            fcntl.flock(self._fh.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        try:
            if os.name == "nt":
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None


def atomic_write_json(path: str, data: Any):
    """Write to a temp file then os.replace, so readers never see a half-written file."""
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(5):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            # Windows: another process may briefly hold the target open
            if attempt == 4:
                raise
            time.sleep(0.05 * (attempt + 1))


def fuse_rankings(ranked_lists: List[List[str]], timestamps: Dict[str, float], top_k: int) -> List[str]:
    """Reciprocal Rank Fusion of BM25 and vector rankings, then recency re-weighting.

    Ranks are comparable across retrievers even though raw BM25 scores and vector
    distances are not, so neither retriever can drown out the other.
    """
    fused: Dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked):
            fused[doc] = fused.get(doc, 0.0) + 1.0 / (RRF_K + rank + 1)
    scored = [
        (score * (0.7 + 0.3 * compute_recency_score(timestamps.get(doc, 0.0))), doc)
        for doc, score in fused.items()
    ]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


class MinosEngine:
    """Portable, Thread- and Process-Safe Minos Memory & Knowledge Operating Engine v4.2."""

    def __init__(self, storage_dir: Optional[str] = None, lms_url: str = "http://127.0.0.1:1234"):
        raw_dir = storage_dir or os.environ.get("MINOS_STORAGE_DIR") or "./minos_storage"
        self.storage_dir = os.path.abspath(os.path.expanduser(os.path.expandvars(raw_dir)))
        self.lms_url = lms_url.rstrip("/")
        os.makedirs(self.storage_dir, exist_ok=True)

        self._db_path = self._resolve_vector_db_path()
        self._memory_file = os.path.join(self.storage_dir, "minos_memory.json")
        self._episodic_file = os.path.join(self.storage_dir, "minos_episodic.jsonl")
        self._graph_file = os.path.join(self.storage_dir, "minos_graph.json")
        self._lock_file = os.path.join(self.storage_dir, ".minos.lock")

        self._io_lock = threading.Lock()

        # State containers (cached copy of the files; refreshed when another process writes)
        self._semantic_memory = ""
        self._working_memory: List[Dict[str, str]] = []
        self._pinned_memories: List[str] = []
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._graph_nodes: Dict[str, Dict[str, Any]] = {}
        self._graph_edges: List[Dict[str, str]] = []
        self._memory_mtime = None
        self._graph_mtime = None

        # Vector Client
        self._chroma_client = None
        self._chroma_collection = None
        if chromadb:
            try:
                self._chroma_client = chromadb.PersistentClient(path=self._db_path)
                self._chroma_collection = self._open_collection()
            except Exception as e:
                logger.warning(f"ChromaDB init failed: {e}")

        # Embedding endpoint that last answered; tried first so indexing and querying
        # keep using the same embedding space whenever possible.
        self._embed_pref = 0

        # BM25 Cache: parallel lists of documents, timestamps and token sets
        self._bm25_model = None
        self._bm25_corpus: List[str] = []
        self._bm25_timestamps: List[float] = []
        self._bm25_token_sets: List[set] = []
        self._bm25_last_mtime = 0.0

        with self._shared_state():
            pass

    @contextmanager
    def _shared_state(self):
        """Hold the thread lock and the cross-process file lock, with state freshly loaded.

        Every mutation happens inside this block and saves before leaving it, so a write
        from one process can no longer overwrite what another process saved in between.
        """
        with self._io_lock, InterProcessLock(self._lock_file):
            self._refresh_unlocked()
            yield

    # --- 1. Pinned Facts (Never-decay) ---
    def pin_fact(self, fact: str) -> str:
        clean = (fact or "").strip()
        if not clean:
            return "오류: 팩트 내용이 비어있습니다."
        with self._shared_state():
            if clean not in self._pinned_memories:
                self._pinned_memories.append(clean)
                self._save_memory_unlocked()
        return f"성공: 중요 핀 등록 완료 -> '{clean}'"

    def get_pinned_facts(self) -> List[str]:
        with self._shared_state():
            return list(self._pinned_memories)

    # --- 2. Project Status Dashboard ---
    def update_project(self, project_name: str, status: str, details: str) -> str:
        name = (project_name or "").strip()
        st = (status or "in_progress").strip()
        det = (details or "").strip()
        if not name:
            return "오류: 프로젝트 이름이 비어있습니다."
        with self._shared_state():
            self._projects[name] = {
                "status": st,
                "details": det,
                "updated_at": time.strftime("%Y-%m-%d %H:%M")
            }
            self._save_memory_unlocked()
        return f"성공: 프로젝트 상태 갱신 -> [{st.upper()}] {name}: {det}"

    def get_projects(self) -> Dict[str, Dict[str, Any]]:
        with self._shared_state():
            return dict(self._projects)

    # --- 3. Knowledge Graph Subsystem ---
    def add_relation(self, source: str, relation: str, target: str, details: Optional[str] = None) -> str:
        src = (source or "").strip()
        rel = (relation or "").strip()
        tgt = (target or "").strip()
        if not (src and rel and tgt):
            return "오류: source, relation, target이 모두 필요합니다."
        with self._shared_state():
            if src not in self._graph_nodes:
                self._graph_nodes[src] = {"type": "auto", "attributes": {}}
            if tgt not in self._graph_nodes:
                self._graph_nodes[tgt] = {"type": "auto", "attributes": {}}
            if details:
                self._graph_nodes[src]["attributes"]["details"] = details

            exists = any(e.get("source") == src and e.get("relation") == rel and e.get("target") == tgt for e in self._graph_edges)
            if not exists:
                self._graph_edges.append({"source": src, "relation": rel, "target": tgt})
            self._save_graph_unlocked()
        return f"성공: 지식 관계 등록 -> '{src}' ──[{rel}]──> '{tgt}'"

    def query_graph(self, entity: str) -> str:
        ent = (entity or "").strip()
        if not ent:
            return "조회할 엔티티를 입력하세요."
        with self._shared_state():
            matched_edges = [
                f"🔗 {e['source']} ──[{e['relation']}]──> {e['target']}"
                for e in self._graph_edges
                if ent.lower() in e.get("source", "").lower() or ent.lower() in e.get("target", "").lower()
            ]
            node_info = self._graph_nodes.get(ent)

        res = []
        if node_info:
            res.append(f"📌 엔티티: {ent} (타입: {node_info.get('type')})")
            for k, v in node_info.get("attributes", {}).items():
                res.append(f"  - {k}: {v}")
        if matched_edges:
            res.append("📌 연결 관계망:")
            res.extend(matched_edges)
        if not res:
            return f"지식 그래프에서 '{ent}' 정보를 찾을 수 없습니다."
        return "\n".join(res)

    # --- 4. Episodic Memory & RAG Retrieval ---
    def record_interaction(self, user_content: str, assistant_content: str):
        now = time.time()
        try:
            with self._io_lock, InterProcessLock(self._lock_file):
                with open(self._episodic_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps({"timestamp": now, "role": "user", "content": user_content}, ensure_ascii=False) + "\n")
                    f.write(json.dumps({"timestamp": now, "role": "assistant", "content": assistant_content}, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to record interaction: {e}")

        if self._chroma_collection:
            def bg_embed():
                try:
                    if should_index_content(user_content):
                        emb = self._get_embedding(user_content, timeout=EMBEDDING_INDEX_TIMEOUT)
                        if emb:
                            self._chroma_collection.add(
                                embeddings=[emb],
                                documents=[user_content],
                                metadatas=[{"role": "user", "timestamp": now}],
                                ids=[f"u_{uuid.uuid4().hex}"]
                            )
                        else:
                            logger.warning("Vector indexing skipped: no embedding endpoint answered")
                except Exception as ex:
                    logger.warning(f"Async vectorization failed: {ex}")
            threading.Thread(target=bg_embed, daemon=True).start()

    def search(self, query: str, top_k: int = 3) -> List[str]:
        clean_q = (query or "").strip()
        if not clean_q:
            return []

        timestamps: Dict[str, float] = {}

        bm25_ranked = []
        for doc, ts in self._query_bm25(clean_q, n=top_k * 2):
            bm25_ranked.append(doc)
            timestamps[doc] = max(ts, timestamps.get(doc, 0.0))

        vector_ranked = []
        if self._chroma_collection:
            q_emb = self._get_embedding(clean_q, timeout=EMBEDDING_HTTP_TIMEOUT)
            if q_emb:
                try:
                    res = self._chroma_collection.query(
                        query_embeddings=[q_emb],
                        n_results=top_k * 2,
                        include=["documents", "metadatas", "embeddings"],
                    )
                    docs = res["documents"][0] if res.get("documents") else []
                    metas = res["metadatas"][0] if res.get("metadatas") else [None] * len(docs)
                    embs = res["embeddings"][0] if res.get("embeddings") is not None else [None] * len(docs)
                    for d, meta, emb in zip(docs, metas, embs):
                        # Chroma always returns n_results hits, related or not; drop the unrelated ones
                        if emb is None or cosine_similarity(q_emb, emb) < VECTOR_MIN_COSINE:
                            continue
                        vector_ranked.append(d)
                        ts = meta.get("timestamp", 0.0) if meta else 0.0
                        timestamps[d] = max(ts, timestamps.get(d, 0.0))
                except Exception as ex:
                    logger.debug(f"Chroma query skipped: {ex}")

        return fuse_rankings([bm25_ranked, vector_ranked], timestamps, top_k)

    # --- 5. Unified System Prompt Generator ---
    def get_context_block(self, query: str = "") -> str:
        """Generate a complete XML/Markdown context block to inject into LLM system prompt."""
        with self._shared_state():
            pinned = list(self._pinned_memories)
            projects = dict(self._projects)
            nodes = dict(self._graph_nodes)
            edges = list(self._graph_edges)
            semantic = self._semantic_memory

        sections = []

        if pinned:
            p_lines = "\n".join([f"📌 {p}" if not p.startswith("📌") else p for p in pinned])
            sections.append(f"## Pinned Long-Term Facts (Never Expire)\n{p_lines}")

        clean_semantic = clean_cot_and_tags(semantic)
        if clean_semantic:
            sections.append(f"## User Profile (Persistent)\n{clean_semantic}")

        if edges:
            kg_lines = []
            for src, data in list(nodes.items())[:5]:
                connected = [f"🔗 {e['source']} ──[{e['relation']}]──> {e['target']}" for e in edges if e['source'] == src][:3]
                if connected:
                    kg_lines.append(f"🕸️ [{src}] -> " + ", ".join(connected))
            if kg_lines:
                sections.append("## Knowledge Graph Context\n" + "\n".join(kg_lines))

        if projects:
            proj_lines = []
            for name, pdata in list(projects.items())[-5:]:
                st = pdata.get("status", "active")
                mark = "✅" if st in ["completed", "done"] else "🔄"
                proj_lines.append(f"- {mark} [{st.upper()}] **{name}**: {pdata.get('details', '')}")
            if proj_lines:
                sections.append("## Active Project Dashboard\n" + "\n".join(proj_lines))

        if query:
            memories = self.search(query, top_k=3)
            if memories:
                mem_lines = "\n".join([f"- {m}" for m in memories])
                sections.append(f"## Relevant Episodic Memories\n{mem_lines}")

        if not sections:
            return ""

        return "<minos-memory-context>\n" + "\n\n".join(sections) + "\n</minos-memory-context>"

    def get_memory_stats(self) -> Dict[str, Any]:
        with self._shared_state():
            stats = {
                "storage_dir": self.storage_dir,
                "vector_db": self._db_path,
                "pins": len(self._pinned_memories),
                "projects": len(self._projects),
                "nodes": len(self._graph_nodes),
                "edges": len(self._graph_edges),
                "semantic_chars": len(self._semantic_memory),
            }
        episodic = 0
        if os.path.exists(self._episodic_file):
            with open(self._episodic_file, "r", encoding="utf-8") as f:
                episodic = sum(1 for line in f if line.strip())
        stats["episodic"] = episodic
        try:
            stats["vectors"] = self._chroma_collection.count() if self._chroma_collection else 0
        except Exception:
            stats["vectors"] = None
        return stats

    # --- 6. Hardware & System Tools ---
    def get_system_status(self) -> str:
        try:
            total, used, free = shutil.disk_usage(os.path.splitdrive(self.storage_dir)[0] or "C:\\")
            lms_ok = False
            lms_models = []
            try:
                r = requests.get(f"{self.lms_url}/v1/models", timeout=1.0)
                if r.status_code == 200:
                    lms_ok = True
                    lms_models = [m.get("id") for m in r.json().get("data", [])][:3]
            except Exception:
                pass

            lines = [
                "🖥️ [시스템 상태 실측 결과]",
                f"- 디스크 여유 공간: {free / (1024**3):.1f} GB / {total / (1024**3):.1f} GB ({(free/total)*100:.1f}% 여유)",
                f"- 로컬 LLM 서버: {'🟢 온라인' if lms_ok else '🔴 오프라인'} ({self.lms_url})",
                f"- 벡터 DB: {'🟢 연결됨' if self._chroma_collection else '🔴 미연결'}",
                f"- 등록된 영구 핀: {len(self._pinned_memories)}개",
                f"- 지식 그래프 엔티티: {len(self._graph_nodes)}개 (관계: {len(self._graph_edges)}개)"
            ]
            if lms_models:
                lines.append(f"- 로드 모델: {', '.join(lms_models)}")
            return "\n".join(lines)
        except Exception as ex:
            return f"시스템 진단 실패: {ex}"

    def control_pc(self, action: str, value: Optional[Any] = None) -> str:
        act = (action or "").lower().strip()
        try:
            import ctypes
            import subprocess

            if act == "get_volume":
                try:
                    import pycaw.pycaw as pc
                    dev = pc.AudioUtilities.GetSpeakers()
                    vol = dev.EndpointVolume
                    scalar = vol.GetMasterVolumeLevelScalar()
                    mute = vol.GetMute()
                    return f"🔊 현재 마스터 볼륨: {round(scalar * 100)}% (음소거: {'🔇' if mute else '🔈'})"
                except Exception as ex:
                    return f"볼륨 조회 실패: {ex}"

            elif act == "set_volume":
                try:
                    target_pct = max(0, min(100, int(value if value is not None else 50)))
                    import pycaw.pycaw as pc
                    dev = pc.AudioUtilities.GetSpeakers()
                    vol = dev.EndpointVolume
                    vol.SetMasterVolumeLevelScalar(target_pct / 100.0, None)
                    if vol.GetMute():
                        vol.SetMute(0, None)
                    return f"🔊 볼륨을 {target_pct}%로 설정했습니다."
                except Exception as ex:
                    return f"볼륨 설정 실패: {ex}"

            elif act == "mute":
                try:
                    import pycaw.pycaw as pc
                    dev = pc.AudioUtilities.GetSpeakers()
                    dev.EndpointVolume.SetMute(1, None)
                    return "🔇 음소거되었습니다."
                except Exception as ex:
                    return f"음소거 실패: {ex}"

            elif act == "unmute":
                try:
                    import pycaw.pycaw as pc
                    dev = pc.AudioUtilities.GetSpeakers()
                    dev.EndpointVolume.SetMute(0, None)
                    return "🔈 음소거가 해제되었습니다."
                except Exception as ex:
                    return f"음소거 해제 실패: {ex}"

            elif act == "lock_screen":
                ctypes.windll.user32.LockWorkStation()
                return "🔒 화면을 잠갔습니다."

            elif act == "open_app":
                app_name = str(value or "").lower().strip()
                allowed = {
                    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    "notepad": "notepad.exe",
                    "calc": "calc.exe",
                    "calculator": "calc.exe",
                    "explorer": "explorer.exe"
                }
                if app_name not in allowed:
                    return f"허용되지 않은 앱입니다. (허용: {', '.join(allowed.keys())})"
                subprocess.Popen([allowed[app_name]], shell=False)
                return f"🚀 앱 실행: '{app_name}'"

            return f"알 수 없는 액션: {act}"
        except Exception as e:
            return f"PC 제어 오류: {e}"

    def tag_audiobook(self, file_path: str, title: str, artist: str = "형님", album: str = "오디오북", track_num: str = "1", cover_path: Optional[str] = None) -> str:
        if not file_path or not os.path.exists(file_path):
            return f"오류: 파일을 찾을 수 없습니다 -> {file_path}"
        try:
            from mutagen.mp3 import MP3
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TCON, APIC, ID3NoHeaderError

            try:
                audio = MP3(file_path, ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(file_path)
                audio.add_tags()

            if audio.tags is None:
                audio.add_tags()

            audio.tags["TIT2"] = TIT2(encoding=3, text=title or os.path.basename(file_path))
            audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
            audio.tags["TALB"] = TALB(encoding=3, text=album)
            audio.tags["TRCK"] = TRCK(encoding=3, text=str(track_num))
            audio.tags["TCON"] = TCON(encoding=3, text="Audiobook")

            if cover_path and os.path.exists(cover_path):
                mime = "image/jpeg" if cover_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
                with open(cover_path, "rb") as img:
                    audio.tags["APIC"] = APIC(encoding=3, mime=mime, type=3, desc="Cover", data=img.read())

            audio.save(v2_version=3)

            # Link in knowledge graph
            self.add_relation(album, "음원파일", os.path.basename(file_path), details=file_path)
            return f"성공: ID3 태깅 완료 -> [{album}] {title} (트랙: {track_num})"
        except Exception as e:
            return f"태깅 실패: {e}"

    # --- Internal Persistence Helpers ---
    def _resolve_vector_db_path(self) -> str:
        official = os.path.join(self.storage_dir, "minos_vector_db")
        legacy = os.path.join(self.storage_dir, "vector_db")
        if not os.path.exists(official) and os.path.exists(legacy):
            return legacy
        return official

    def _open_collection(self):
        try:
            names = [getattr(c, "name", c) for c in self._chroma_client.list_collections()]
        except Exception:
            names = []
        if COLLECTION_NAME not in names and LEGACY_COLLECTION_NAME in names:
            return self._chroma_client.get_collection(name=LEGACY_COLLECTION_NAME)
        return self._chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    @staticmethod
    def _mtime(path: str):
        try:
            return os.stat(path).st_mtime_ns
        except OSError:
            return None

    def _refresh_unlocked(self):
        """Reload files that another process changed since we last read or wrote them."""
        mtime = self._mtime(self._memory_file)
        if mtime != self._memory_mtime:
            self._load_memory_unlocked()
            self._memory_mtime = mtime
        mtime = self._mtime(self._graph_file)
        if mtime != self._graph_mtime:
            self._load_graph_unlocked()
            self._graph_mtime = mtime

    def _load_memory_unlocked(self):
        self._semantic_memory = ""
        self._working_memory = []
        self._pinned_memories = []
        self._projects = {}
        if os.path.exists(self._memory_file):
            try:
                with open(self._memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._semantic_memory = data.get("semantic_memory", "")
                    self._working_memory = list(data.get("working_memory", []))
                    self._pinned_memories = list(data.get("pinned_memories", []))
                    self._projects = dict(data.get("projects", {}))
            except Exception as e:
                logger.error(f"Failed to load memory file: {e}")

    def _save_memory_unlocked(self):
        try:
            atomic_write_json(self._memory_file, {
                "semantic_memory": self._semantic_memory,
                "working_memory": self._working_memory,
                "pinned_memories": self._pinned_memories,
                "projects": self._projects
            })
            self._memory_mtime = self._mtime(self._memory_file)
        except Exception as e:
            logger.error(f"Failed to save memory file: {e}")

    def _load_graph_unlocked(self):
        self._graph_nodes = {}
        self._graph_edges = []
        if os.path.exists(self._graph_file):
            try:
                with open(self._graph_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._graph_nodes = dict(data.get("nodes", {}))
                    self._graph_edges = list(data.get("edges", []))
            except Exception as e:
                logger.error(f"Failed to load graph file: {e}")

    def _save_graph_unlocked(self):
        try:
            atomic_write_json(self._graph_file, {
                "nodes": self._graph_nodes,
                "edges": self._graph_edges
            })
            self._graph_mtime = self._mtime(self._graph_file)
        except Exception as e:
            logger.error(f"Failed to save graph file: {e}")

    def _get_embedding(self, content: str, timeout: float = EMBEDDING_HTTP_TIMEOUT) -> Optional[List[float]]:
        clean = content.strip()
        if not clean:
            return None
        endpoints = [
            (f"{self.lms_url}/v1/embeddings", {"input": clean, "model": "nomic-embed-text"}),
            ("http://127.0.0.1:11434/api/embeddings", {"prompt": clean, "model": "nomic-embed-text"}),
        ]
        order = [self._embed_pref] + [i for i in range(len(endpoints)) if i != self._embed_pref]
        for idx in order:
            url, payload = endpoints[idx]
            try:
                res = requests.post(url, json=payload, timeout=timeout)
                if res.status_code == 200:
                    data = res.json()
                    emb = None
                    if "data" in data and len(data["data"]) > 0:
                        emb = data["data"][0].get("embedding")
                    elif "embedding" in data:
                        emb = data["embedding"]
                    if emb:
                        self._embed_pref = idx
                        return emb
            except Exception:
                pass
        return None

    def _query_bm25(self, query: str, n: int = 3) -> List[Tuple[str, float]]:
        """Return up to n (document, timestamp) pairs that actually share tokens with the query."""
        if not os.path.exists(self._episodic_file) or not BM25_CLASS:
            return []
        try:
            mtime = os.path.getmtime(self._episodic_file)
            if self._bm25_model is None or mtime > self._bm25_last_mtime:
                window = deque(maxlen=BM25_MAX_SLIDING_WINDOW)
                with open(self._episodic_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            d = json.loads(line)
                            c = d.get("content", "").strip()
                            if len(c) >= 5:
                                window.append((c, float(d.get("timestamp") or 0.0)))
                        except Exception:
                            continue
                # Keep only the newest copy of repeated messages
                latest: Dict[str, float] = {}
                for c, ts in window:
                    latest[c] = max(ts, latest.get(c, 0.0))
                self._bm25_corpus = list(latest.keys())
                self._bm25_timestamps = [latest[c] for c in self._bm25_corpus]
                tokenized = [tokenize_korean_bigram(doc) for doc in self._bm25_corpus]
                self._bm25_token_sets = [set(t) for t in tokenized]
                self._bm25_model = BM25_CLASS(tokenized) if tokenized else None
                self._bm25_last_mtime = mtime

            if not self._bm25_model or not self._bm25_corpus:
                return []

            tokens = tokenize_korean_bigram(query)
            q_set = set(tokens)
            if not q_set:
                return []
            scores = self._bm25_model.get_scores(tokens)
            ranked = []
            for i, score in enumerate(scores):
                # BM25Plus gives every doc a positive floor score once any query token
                # exists in the corpus, so score > 0 alone does not mean "relevant".
                overlap = len(q_set & self._bm25_token_sets[i]) / len(q_set)
                if overlap >= BM25_MIN_TOKEN_OVERLAP:
                    ranked.append((score, i))
            ranked.sort(key=lambda x: x[0], reverse=True)
            return [(self._bm25_corpus[i], self._bm25_timestamps[i]) for _, i in ranked[:n]]
        except Exception as e:
            logger.debug(f"BM25 search failed: {e}")
            return []


# --- Standalone Verification Entry Point ---
if __name__ == "__main__":
    import sys
    if sys.stdout and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print("=== Minos Engine v4.2 Standalone Verification ===")
    engine = MinosEngine(storage_dir="./test_minos_data")
    print(engine.pin_fact("사용자 호칭: 형님"))
    print(engine.add_relation("형님", "관심종목", "TIGER 반도체TOP10"))
    print(engine.update_project("오디오북 프로젝트", "completed", "국화와 칼 10부작 완성"))
    print("\n[지식 그래프 질의]:")
    print(engine.query_graph("형님"))
    print("\n[컨텍스트 프롬프트 블록 생성]:")
    print(engine.get_context_block(query="반도체"))
    print("\n[시스템 상태 진단]:")
    print(engine.get_system_status())
    print("\nVerification Completed Successfully!")
