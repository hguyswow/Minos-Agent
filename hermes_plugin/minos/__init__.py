# -*- coding: utf-8 -*-
"""
Minos Memory & Knowledge Operating Engine for Hermes Agent (Enterprise v4.2).
Implements the MemoryProvider ABC interface with:
1. Knowledge Graph Subsystem (Entity-Relationship graph & tools: add_knowledge_relation, query_knowledge_graph)
2. Pinned Long-Term Facts (Never-decay permanent memory & tool: pin_memory)
3. Project Status Dashboard (Active/completed project tracker & tool: update_project_status)
4. System Hardware & Health Diagnostics (tool: get_system_status)
5. Session Welcome Briefing (Proactive briefing on session start/greeting)
6. Korean Subword Bi-gram BM25Plus (100% particle/josa-immune Korean search)
7. Time-Decay RAG Re-ranking (14-day half-life exponential decay)
8. Thread- and Process-Safe I/O (file lock + reload-before-write + atomic replace)
9. CoT / Thinking Tag Scrubber (Gemma, DeepSeek, Qwen)
10. Fast-Fail Query Embedding Timeout (1.2s), patient background indexing
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

from agent.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)

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


# Performance & Tuning Constants
EMBEDDING_HTTP_TIMEOUT = 1.2       # Fast-fail timeout for query-time embeddings
EMBEDDING_INDEX_TIMEOUT = 15.0     # Background indexing may wait for a cold model load
MIN_INDEX_CHAR_LEN = 8             # Minimum characters required for Vector DB indexing
BM25_MAX_SLIDING_WINDOW = 2500     # Maximum recent episodic entries for in-memory BM25
BM25_MIN_TOKEN_OVERLAP = 0.3       # Share of query tokens a doc must contain to count as relevant
VECTOR_MIN_COSINE = 0.45           # Vector hits below this cosine similarity are treated as noise
RRF_K = 60                         # Reciprocal Rank Fusion constant
MAX_MEMORY_SNIPPET_CHARS = 500     # Long past answers are clipped before prompt injection
RECENCY_HALFLIFE_DAYS = 14.0       # Half-life for memory recency exponential decay


def clean_cot_and_tags(text: str) -> str:
    """Strip reasoning/thought tags and prompt leakages from LLM outputs."""
    if not text:
        return ""

    cleaned = text
    # 1. Gemma channel thought tags
    cleaned = re.sub(r"<\|channel\>thought[\s\S]*?<channel\|>", "", cleaned)
    cleaned = re.sub(r"<\|channel\>thought[\s\S]*$", "", cleaned)
    cleaned = re.sub(r"^[\s\S]*?<channel\|>", "", cleaned)

    # 2. DeepSeek / Qwen think tags
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", cleaned)
    cleaned = re.sub(r"<think>[\s\S]*$", "", cleaned)
    cleaned = re.sub(r"^[\s\S]*?</think>", "", cleaned)

    # 3. Clean prompt meta artifacts or reasoning checklist leaks
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
    """Tokenize Korean/multilingual text into words and character 2-grams (bi-grams).
    
    Immune to Korean grammatical particles (조사/어미: ~을/를/에서/으로/했던).
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
    """Determine whether text contains enough semantic information to index into ChromaDB."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) < MIN_INDEX_CHAR_LEN:
        return False

    lower = clean.lower()
    common_noise = {
        "응", "어", "네", "아니", "오키", "알겠어", "고마워", "감사", "감사합니다",
        "그래", "좋아", "안녕", "안녕하세요", "하이", "ㅋㅋ", "ㅎㅎ", "ㅋㅋㅋ", "ㅎㅎㅎ",
        "ok", "okay", "yes", "no", "thanks", "thx", "sure", "cool"
    }
    if lower in common_noise:
        return False
    return True


def compute_recency_score(timestamp: float, halflife_days: float = RECENCY_HALFLIFE_DAYS) -> float:
    """Calculate an exponential time-decay factor between 0.0 and 1.0."""
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


class MinosMemoryProvider(MemoryProvider):
    def __init__(self):
        self._session_id = ""
        self._hermes_home = ""
        self._db_path = ""
        self._memory_file = ""
        self._episodic_file = ""
        self._graph_file = ""
        self._lock_file = ""
        self._memory_mtime = None
        self._graph_mtime = None
        self._embed_pref = 0
        self._chroma_client = None
        self._chroma_collection = None
        self._semantic_memory = ""
        self._working_memory = []
        self._pinned_memories: List[str] = []
        self._projects: Dict[str, Dict[str, Any]] = {}
        self._graph_nodes: Dict[str, Dict[str, Any]] = {}
        self._graph_edges: List[Dict[str, str]] = []
        self._active = False

        # Thread Safety Lock
        self._io_lock = threading.Lock()

        # In-memory sliding-window BM25 cache with Korean Bi-gram
        self._bm25_model = None
        self._bm25_corpus: List[str] = []
        self._bm25_timestamps: List[float] = []
        self._bm25_token_sets: List[set] = []
        self._bm25_last_mtime = 0.0

    @property
    def name(self) -> str:
        return "minos"

    def is_available(self) -> bool:
        return chromadb is not None

    def initialize(self, session_id: str, **kwargs) -> None:
        self._session_id = session_id

        # Resolve hermes_home
        from hermes_constants import get_hermes_home
        self._hermes_home = kwargs.get("hermes_home") or str(get_hermes_home())

        # Build paths
        # MINOS_STORAGE_DIR lets several Hermes profiles (or other agents) share one Minos memory
        shared_dir = os.environ.get("MINOS_STORAGE_DIR", "").strip()
        if shared_dir:
            mem_dir = os.path.abspath(os.path.expanduser(os.path.expandvars(shared_dir)))
        else:
            mem_dir = os.path.join(self._hermes_home, "memories")
        self._db_path = os.path.join(mem_dir, "minos_vector_db")
        legacy_db = os.path.join(mem_dir, "vector_db")
        if not os.path.exists(self._db_path) and os.path.exists(legacy_db):
            self._db_path = legacy_db
        self._lock_file = os.path.join(mem_dir, ".minos.lock")
        self._memory_file = os.path.join(mem_dir, "minos_memory.json")
        self._episodic_file = os.path.join(mem_dir, "minos_episodic.jsonl")
        self._graph_file = os.path.join(mem_dir, "minos_graph.json")

        # Ensure directories exist
        os.makedirs(mem_dir, exist_ok=True)

        # Initialize ChromaDB Persistent Client
        self._chroma_collection = None
        if chromadb:
            try:
                self._chroma_client = chromadb.PersistentClient(path=self._db_path)
                self._chroma_collection = self._chroma_client.get_or_create_collection(name="minos_episodic")
                self._active = True
                logger.info(f"[MinosMemory] ChromaDB PersistentClient initialized at {self._db_path}")
            except Exception as e:
                logger.error(f"[MinosMemory] ChromaDB initialization failed: {e}", exc_info=True)
                self._active = False
        else:
            self._active = False

        # Load memory state and knowledge graph safely under lock
        self._memory_mtime = None
        self._graph_mtime = None
        with self._shared_state():
            pass

    @contextmanager
    def _shared_state(self):
        """Hold the thread lock and the cross-process file lock, with state freshly loaded.

        WebUI, Telegram bot and other Hermes profiles can share this memory dir from
        separate processes; every mutation happens inside this block and saves before
        leaving it, so one process can no longer overwrite what another just saved.
        """
        with self._io_lock, InterProcessLock(self._lock_file):
            self._refresh_unlocked()
            yield

    def system_prompt_block(self) -> str:
        if not self._active:
            return ""
        return (
            "# Minos Enterprise Memory & Knowledge System v4.2\n"
            "Active. Powered by Knowledge Graph + ChromaDB Vector + Korean Bi-gram BM25 + Pinned Facts + Project Dashboard.\n"
            "Available memory & system tools:\n"
            "- 'pin_memory': Pin permanent user facts/rules\n"
            "- 'update_project_status': Track active task completion\n"
            "- 'add_knowledge_relation': Link entities in the Knowledge Graph\n"
            "- 'query_knowledge_graph': Explore entity relationships\n"
            "- 'get_system_status': Check live CPU/RAM/Disk and local LM Studio health\n"
            "- 'tag_audiobook_mp3': Inject ID3v2 tags and cover art into audiobook MP3s\n"
            "- 'control_pc_system': Safely control PC volume, mute, screen lock, or open whitelisted apps\n"
            "Never output raw memory XML or internal debug tags to the user."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        clean_query = (query or "").strip()

        with self._shared_state():
            pinned = list(self._pinned_memories)
            projects = dict(self._projects)
            current_semantic = self._semantic_memory
            graph_nodes = dict(self._graph_nodes)
            graph_edges = list(self._graph_edges)

        sections = []

        # 1. Pinned Long-Term Facts (Never Expire)
        if pinned:
            pinned_lines = "\n".join([f"📌 {p}" if not p.startswith("📌") else p for p in pinned])
            sections.append(f"## Pinned Long-Term Facts (Never Expire)\n{pinned_lines}")

        # 2. Knowledge Graph Context (Entity Relationships)
        if clean_query and (graph_nodes or graph_edges):
            matched_relations = []
            # Find entities mentioned in query or graph
            for node_name, node_info in graph_nodes.items():
                if node_name.lower() in clean_query.lower():
                    attrs = ", ".join([f"{k}: {v}" for k, v in node_info.get("attributes", {}).items()])
                    matched_relations.append(f"🕸️ [엔티티] **{node_name}** ({node_info.get('type', 'general')}) -> {attrs}")

            for edge in graph_edges:
                src = edge.get("source", "")
                rel = edge.get("relation", "")
                tgt = edge.get("target", "")
                if (src.lower() in clean_query.lower()) or (tgt.lower() in clean_query.lower()):
                    matched_relations.append(f"  └─ 🔗 {src} ──[{rel}]──> {tgt}")

            if matched_relations:
                sections.append("## Knowledge Graph Relationships (Context)\n" + "\n".join(matched_relations[:8]))

        # 3. Project Status Dashboard
        if projects:
            proj_lines = []
            for name, info in projects.items():
                status = info.get("status", "in_progress")
                details = info.get("details", "")
                icon = "✅" if status == "completed" else "🔄" if status == "in_progress" else "⏸️"
                proj_lines.append(f"- {icon} [{status.upper()}] **{name}**: {details}")
            if proj_lines:
                sections.append("## Active Project Dashboard\n" + "\n".join(proj_lines))

        # 4. Persistent Semantic Summary
        clean_semantic = clean_cot_and_tags(current_semantic)
        if clean_semantic.strip():
            sections.append(f"## User Profile (Persistent)\n{clean_semantic.strip()}")

        # 5. Hybrid RAG Search (Vector + Korean Bi-gram BM25, fused by rank)
        past_docs = []
        if clean_query:
            past_docs = self._hybrid_search(clean_query, top_k=3)

            if past_docs:
                clean_docs = []
                for doc in past_docs:
                    cleaned = re.sub(r"\([가-힣\s\d,./?!~^;:\-★☆♥♡💧💦🥺😭🙇✨🙏]*?\)", "", doc)
                    cleaned = clean_cot_and_tags(cleaned).strip()
                    if cleaned:
                        clean_docs.append(f"- {clip_snippet(cleaned)}")
                if clean_docs:
                    sections.append("## Relevant Memories (RAG)\n" + "\n".join(clean_docs))

        # 6. Session Welcome Briefing Guideline
        is_greeting = clean_query.lower() in {"", "안녕", "안녕하세요", "하이", "시작", "hello", "hi", "반가워", "좋은 아침"}
        if is_greeting and (projects or pinned):
            sections.append(
                "## Session Welcome Briefing Instruction\n"
                "[System Note: When responding to this greeting or session start, proactively and warmly brief the user "
                "in 1-2 Korean sentences about the latest project status or completed tasks. E.g. '형님, 어제 국화와 칼 작업 완료해 두었습니다!']"
            )

        if not sections:
            return ""

        body = "\n\n".join(sections)
        return f"<minos-memory-context>\n{body}\n</minos-memory-context>"

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        timestamp = time.time()

        # 1. Log raw turn to episodic.jsonl under lock
        try:
            with self._io_lock, InterProcessLock(self._lock_file):
                with open(self._episodic_file, "a", encoding="utf-8") as f:
                    user_entry = {"timestamp": timestamp, "role": "user", "content": user_content}
                    f.write(json.dumps(user_entry, ensure_ascii=False) + "\n")
                    asst_entry = {"timestamp": timestamp, "role": "assistant", "content": assistant_content}
                    f.write(json.dumps(asst_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"[MinosMemory] Failed to write episodic log: {e}")

        # 2. Vectorize in background thread
        if self._chroma_collection:
            def bg_task():
                try:
                    if should_index_content(user_content):
                        user_embed = self._get_embedding(user_content, timeout=EMBEDDING_INDEX_TIMEOUT)
                        if user_embed:
                            self._chroma_collection.add(
                                embeddings=[user_embed],
                                documents=[user_content],
                                metadatas=[{"role": "user", "timestamp": timestamp}],
                                ids=[f"user_{uuid.uuid4().hex}"]
                            )

                    if should_index_content(assistant_content):
                        asst_for_vector = assistant_content.strip()
                        if len(asst_for_vector) > 300:
                            asst_for_vector = asst_for_vector[:260] + "... (이하 답변 생략)"

                        asst_embed = self._get_embedding(asst_for_vector, timeout=EMBEDDING_INDEX_TIMEOUT)
                        if asst_embed:
                            self._chroma_collection.add(
                                embeddings=[asst_embed],
                                documents=[asst_for_vector],
                                metadatas=[{"role": "assistant", "timestamp": timestamp}],
                                ids=[f"asst_{uuid.uuid4().hex}"]
                            )
                except Exception as ex:
                    logger.warning(f"[MinosMemory] Asynchronous vectorization failed: {ex}")

            threading.Thread(target=bg_task, daemon=True).start()

        # 3. Add to working memory & condense
        with self._shared_state():
            self._working_memory.append({"role": "user", "content": user_content})
            self._working_memory.append({"role": "assistant", "content": assistant_content})

            max_working = 20
            if len(self._working_memory) > max_working:
                keep_count = int(max_working * 0.8)
                condense_count = len(self._working_memory) - keep_count
                old_messages = self._working_memory[:condense_count]
                self._working_memory = self._working_memory[condense_count:]

                self._condense_memory_thread(old_messages)

            self._save_memory_unlocked()

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Expose memory, knowledge graph, and system diagnosis tools to Hermes Agent."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "pin_memory",
                    "description": "사용자의 중요한 선호도, 규칙, 영구 설정, 핵심 팩트를 시간 감쇠 없이 영구 보존하는 중요 핀으로 등록합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "fact": {
                                "type": "string",
                                "description": "영구 보존할 팩트나 규칙 (예: '사용자 호칭은 형님', 'TIGER 반도체TOP10 알림은 매일 오전 10시')"
                            }
                        },
                        "required": ["fact"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_project_status",
                    "description": "사용자가 지시한 프로젝트 또는 작업의 상태(진행중, 완료 등)를 프로젝트 상태판에 기록하거나 갱신합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_name": {
                                "type": "string",
                                "description": "프로젝트 이름 (예: '국화와 칼 오디오북 제작', '오픈코드 연동')"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["in_progress", "completed", "paused", "cancelled"],
                                "description": "프로젝트 상태"
                            },
                            "details": {
                                "type": "string",
                                "description": "진행 내용 요약 또는 완료 결과 (예: '10부작 MP3 텔레그램 전송 완료')"
                            }
                        },
                        "required": ["project_name", "status", "details"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "add_knowledge_relation",
                    "description": "지식 그래프(Knowledge Graph)에 엔티티 간의 관계를 추가합니다. (예: 주어: 형님, 관계: 관심종목, 대상: TIGER 반도체TOP10)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source": {
                                "type": "string",
                                "description": "주어 엔티티 (예: '형님', '국화와 칼', 'LM Studio')"
                            },
                            "relation": {
                                "type": "string",
                                "description": "관계명 (예: '관심종목', '제작완료', '보관위치', '담당모델')"
                            },
                            "target": {
                                "type": "string",
                                "description": "대상 엔티티 또는 속성 (예: 'TIGER 반도체TOP10', '미노스 도서관')"
                            }
                        },
                        "required": ["source", "relation", "target"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_knowledge_graph",
                    "description": "지식 그래프에서 특정 엔티티와 연결된 모든 속성과 관계망을 조회합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity": {
                                "type": "string",
                                "description": "조회할 엔티티 이름 (예: '국화와 칼', '형님', 'TIGER 반도체TOP10')"
                            }
                        },
                        "required": ["entity"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": "현재 Windows 10 로컬 PC의 디스크 용량, 메모리, LM Studio(1234 포트) 및 임베딩 모델의 실시간 구동 상태를 진단합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "tag_audiobook_mp3",
                    "description": "오디오북 MP3 파일에 ID3v2 메타데이터(제목, 아티스트/낭독자, 앨범, 트랙 번호)와 앨범 커버 아트를 자동 주입하고 지식 그래프에 연동합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "메타데이터를 주입할 MP3 파일의 절대 경로 (예: 'D:/down/국화와칼_전체완성.mp3')"
                            },
                            "title": {
                                "type": "string",
                                "description": "오디오북 파트 또는 곡 제목 (미입력 시 파일명 사용)"
                            },
                            "artist": {
                                "type": "string",
                                "description": "작가 또는 낭독자 이름 (기본값: '형님')"
                            },
                            "album": {
                                "type": "string",
                                "description": "작품/앨범 이름 (기본값: '국화와 칼')"
                            },
                            "track_num": {
                                "type": "string",
                                "description": "트랙 번호 (예: '1', '231' 또는 '1/10')"
                            },
                            "cover_path": {
                                "type": "string",
                                "description": "앨범 커버 이미지 경로(jpg/png). 미입력 시 파일 폴더 내 커버 이미지 자동 검색"
                            }
                        },
                        "required": ["file_path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "control_pc_system",
                    "description": "Windows PC 마스터 볼륨 조절(0~100%), 음소거/해제, 화면 잠금, 또는 안전 화이트리스트 앱을 실행합니다.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["get_volume", "set_volume", "mute", "unmute", "lock_screen", "open_app"],
                                "description": "수행할 시스템 제어 동작"
                            },
                            "value": {
                                "type": "string",
                                "description": "볼륨 수치(0~100) 또는 실행할 앱 이름 (chrome, notepad, calc, explorer, lmstudio)"
                            }
                        },
                        "required": ["action"]
                    }
                }
            }
        ]

    def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Handle agent tool calls for memory, knowledge graph, and system diagnosis."""
        if tool_name == "pin_memory":
            fact = (arguments.get("fact") or "").strip()
            if not fact:
                return "❌ 오류: 등록할 팩트 내용이 비어있습니다."
            with self._shared_state():
                if fact not in self._pinned_memories:
                    self._pinned_memories.append(fact)
                    self._save_memory_unlocked()
            logger.info(f"[MinosMemory] Pinned new fact: {fact}")
            return f"✅ 성공: 중요 핀이 영구 기억으로 등록되었습니다 -> '{fact}'"

        elif tool_name == "update_project_status":
            proj_name = (arguments.get("project_name") or "").strip()
            status = (arguments.get("status") or "in_progress").strip()
            details = (arguments.get("details") or "").strip()
            if not proj_name:
                return "❌ 오류: 프로젝트 이름이 비어있습니다."
            with self._shared_state():
                self._projects[proj_name] = {
                    "status": status,
                    "details": details,
                    "updated_at": time.strftime("%Y-%m-%d %H:%M")
                }
                self._save_memory_unlocked()
            logger.info(f"[MinosMemory] Updated project status: {proj_name} [{status}]")
            return f"✅ 성공: 프로젝트 상태판이 갱신되었습니다 -> [{status.upper()}] {proj_name}: {details}"

        elif tool_name == "add_knowledge_relation":
            src = (arguments.get("source") or "").strip()
            rel = (arguments.get("relation") or "").strip()
            tgt = (arguments.get("target") or "").strip()
            if not (src and rel and tgt):
                return "❌ 오류: source, relation, target이 모두 지정되어야 합니다."
            with self._shared_state():
                # Ensure nodes exist
                if src not in self._graph_nodes:
                    self._graph_nodes[src] = {"type": "auto", "attributes": {}}
                if tgt not in self._graph_nodes:
                    self._graph_nodes[tgt] = {"type": "auto", "attributes": {}}
                # Avoid duplicate edge
                exists = any(e.get("source") == src and e.get("relation") == rel and e.get("target") == tgt for e in self._graph_edges)
                if not exists:
                    self._graph_edges.append({"source": src, "relation": rel, "target": tgt})
                    self._save_graph_unlocked()
            logger.info(f"[MinosMemory] Added Knowledge Graph relation: {src} -> [{rel}] -> {tgt}")
            return f"✅ 성공: 지식 그래프에 관계가 등록되었습니다 -> '{src}' ──[{rel}]──> '{tgt}'"

        elif tool_name == "query_knowledge_graph":
            ent = (arguments.get("entity") or "").strip()
            if not ent:
                return "❌ 오류: 조회할 엔티티를 입력하세요."
            with self._shared_state():
                matched_edges = [
                    f"🔗 {e['source']} ──[{e['relation']}]──> {e['target']}"
                    for e in self._graph_edges
                    if ent.lower() in e.get("source", "").lower() or ent.lower() in e.get("target", "").lower()
                ]
                node_info = self._graph_nodes.get(ent)
            res = []
            if node_info:
                res.append(f"📌 엔티티: {ent} (유형: {node_info.get('type')})")
                for k, v in node_info.get("attributes", {}).items():
                    res.append(f"  - {k}: {v}")
            if matched_edges:
                res.append("📌 연결 관계:")
                res.extend(matched_edges)
            if not res:
                return f"ℹ️ 지식 그래프에서 '{ent}' 관련 정보를 찾을 수 없습니다."
            return "\n".join(res)

        elif tool_name == "get_system_status":
            try:
                total, used, free = shutil.disk_usage("C:\\")
                lms_ok = False
                lms_models = []
                try:
                    r = requests.get("http://127.0.0.1:1234/v1/models", timeout=1.0)
                    if r.status_code == 200:
                        lms_ok = True
                        lms_models = [m.get("id") for m in r.json().get("data", [])][:3]
                except Exception:
                    pass

                status_lines = [
                    "🖥️ [시스템 상태 실측 결과]",
                    f"- C: 드라이브 여유 공간: {free / (1024**3):.1f} GB / {total / (1024**3):.1f} GB ({(free/total)*100:.1f}% 여유)",
                    f"- LM Studio (1234 포트): {'🟢 온라인' if lms_ok else '🔴 오프라인'}",
                    f"- Minos 벡터 DB: {'🟢 연결됨' if self._chroma_collection else '🔴 미연결'}",
                    f"- 등록된 영구 핀 수: {len(self._pinned_memories)}개",
                    f"- 지식 그래프 엔티티 수: {len(self._graph_nodes)}개 (관계: {len(self._graph_edges)}개)"
                ]
                if lms_models:
                    status_lines.append(f"- LM Studio 로드 모델: {', '.join(lms_models)}")
                return "\n".join(status_lines)
            except Exception as ex:
                return f"❌ 시스템 상태 진단 실패: {ex}"

        elif tool_name == "tag_audiobook_mp3":
            file_path = (arguments.get("file_path") or "").strip()
            title = (arguments.get("title") or "").strip()
            artist = (arguments.get("artist") or "형님").strip()
            album = (arguments.get("album") or "국화와 칼").strip()
            track_num = str(arguments.get("track_num") or "1").strip()
            cover_path = (arguments.get("cover_path") or "").strip()

            if not file_path or not os.path.exists(file_path):
                return f"❌ 오류: 지정한 MP3 파일을 찾을 수 없습니다 -> '{file_path}'"

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

                if not title:
                    title = os.path.splitext(os.path.basename(file_path))[0]

                audio.tags["TIT2"] = TIT2(encoding=3, text=title)
                audio.tags["TPE1"] = TPE1(encoding=3, text=artist)
                audio.tags["TALB"] = TALB(encoding=3, text=album)
                audio.tags["TRCK"] = TRCK(encoding=3, text=track_num)
                audio.tags["TCON"] = TCON(encoding=3, text="Audiobook")

                cover_applied = False
                if not cover_path:
                    parent_dir = os.path.dirname(file_path)
                    for candidate in ["cover.jpg", "cover.png", "folder.jpg", "front.jpg"]:
                        c_path = os.path.join(parent_dir, candidate)
                        if os.path.exists(c_path):
                            cover_path = c_path
                            break

                if cover_path and os.path.exists(cover_path):
                    mime = "image/jpeg" if cover_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
                    with open(cover_path, "rb") as img_f:
                        audio.tags["APIC"] = APIC(
                            encoding=3,
                            mime=mime,
                            type=3,
                            desc="Front Cover",
                            data=img_f.read()
                        )
                    cover_applied = True

                audio.save(v2_version=3)

                # Minos 지식 그래프 연계
                with self._shared_state():
                    if album not in self._graph_nodes:
                        self._graph_nodes[album] = {"type": "audiobook", "attributes": {}}
                    self._graph_nodes[album]["attributes"]["최근파일"] = file_path
                    self._graph_nodes[album]["attributes"]["최신트랙"] = title
                    edge = {"source": album, "relation": "음원파일", "target": os.path.basename(file_path)}
                    if edge not in self._graph_edges:
                        self._graph_edges.append(edge)
                    self._save_graph_unlocked()

                res_lines = [
                    "✅ 성공: MP3 오디오북 ID3v2 태그 및 메타데이터 주입 완료!",
                    f"  - 대상 파일: {file_path}",
                    f"  - 제목: {title} (트랙: {track_num})",
                    f"  - 작가/낭독: {artist} | 앨범: {album}",
                    f"  - 앨범 커버 아트: {'🖼️ 삽입됨 (' + cover_path + ')' if cover_applied else '⚪ 미적용 (커버 파일 없음)'}",
                    f"  - Minos 지식 그래프에 '{album}' 음원 연동 완료"
                ]
                logger.info(f"[MinosMemory] Tagged audiobook MP3: {file_path} [{title}]")
                return "\n".join(res_lines)
            except Exception as ex:
                logger.error(f"[MinosMemory] Failed to tag MP3: {ex}")
                return f"❌ ID3 태그 주입 실패: {ex}"

        elif tool_name == "control_pc_system":
            action = (arguments.get("action") or "").lower().strip()
            val = arguments.get("value")

            try:
                import ctypes
                import subprocess

                if action == "get_volume":
                    try:
                        import pycaw.pycaw as pc
                        dev = pc.AudioUtilities.GetSpeakers()
                        vol = dev.EndpointVolume
                        scalar = vol.GetMasterVolumeLevelScalar()
                        mute = vol.GetMute()
                        return f"🔊 현재 PC 마스터 볼륨: {round(scalar * 100)}% (음소거 상태: {'🔇 음소거 중' if mute else '🔈 켜짐'})"
                    except Exception as ex:
                        return f"❌ 볼륨 조회 실패: {ex}"

                elif action == "set_volume":
                    try:
                        target_pct = int(val) if val is not None else 50
                        target_pct = max(0, min(100, target_pct))
                        import pycaw.pycaw as pc
                        dev = pc.AudioUtilities.GetSpeakers()
                        vol = dev.EndpointVolume
                        vol.SetMasterVolumeLevelScalar(target_pct / 100.0, None)
                        if vol.GetMute():
                            vol.SetMute(0, None)
                        logger.info(f"[MinosMemory] PC Master Volume set to {target_pct}%")
                        return f"🔊 PC 마스터 볼륨을 {target_pct}%로 조정했습니다."
                    except Exception as ex:
                        return f"❌ 볼륨 설정 실패: {ex}"

                elif action == "mute":
                    try:
                        import pycaw.pycaw as pc
                        dev = pc.AudioUtilities.GetSpeakers()
                        vol = dev.EndpointVolume
                        vol.SetMute(1, None)
                        return "🔇 PC 사운드를 음소거했습니다."
                    except Exception as ex:
                        return f"❌ 음소거 실패: {ex}"

                elif action == "unmute":
                    try:
                        import pycaw.pycaw as pc
                        dev = pc.AudioUtilities.GetSpeakers()
                        vol = dev.EndpointVolume
                        vol.SetMute(0, None)
                        return "🔈 PC 사운드 음소거를 해제했습니다."
                    except Exception as ex:
                        return f"❌ 음소거 해제 실패: {ex}"

                elif action == "lock_screen":
                    try:
                        ctypes.windll.user32.LockWorkStation()
                        logger.info("[MinosMemory] LockWorkStation called successfully.")
                        return "🔒 윈도우 PC 화면을 성공적으로 잠갔습니다 (LockWorkStation)."
                    except Exception as ex:
                        return f"❌ 화면 잠금 실패: {ex}"

                elif action == "open_app":
                    app_name = str(val or "").lower().strip()
                    allowed_apps = {
                        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                        "notepad": "notepad.exe",
                        "calc": "calc.exe",
                        "calculator": "calc.exe",
                        "explorer": "explorer.exe",
                        "lmstudio": os.path.expandvars(r"%LOCALAPPDATA%\Programs\LM Studio\LM Studio.exe")
                    }
                    if app_name not in allowed_apps:
                        return f"⚠️ 허용되지 않은 앱입니다. (허용 목록: {', '.join(allowed_apps.keys())})"

                    target_exe = allowed_apps[app_name]
                    subprocess.Popen([target_exe], shell=False)
                    logger.info(f"[MinosMemory] Launched app: {app_name}")
                    return f"🚀 앱 실행 성공: '{app_name}'"

                else:
                    return f"❌ 알 수 없는 액션: '{action}'. (사용 가능: get_volume, set_volume, mute, unmute, lock_screen, open_app)"

            except Exception as ex:
                logger.error(f"[MinosMemory] PC system control failed: {ex}")
                return f"❌ PC 시스템 제어 오류: {ex}"

        return None

    def shutdown(self) -> None:
        pass

    # Helper Methods
    def _hybrid_search(self, query: str, top_k: int = 3) -> List[str]:
        """BM25 and vector retrieval, each filtered for relevance, fused by Reciprocal Rank Fusion."""
        timestamps: Dict[str, float] = {}

        bm25_ranked = []
        for doc, ts in self._query_bm25(query, n=top_k * 2):
            bm25_ranked.append(doc)
            timestamps[doc] = max(ts, timestamps.get(doc, 0.0))

        vector_ranked = []
        if self._chroma_collection:
            try:
                q_emb = self._get_embedding(query, timeout=EMBEDDING_HTTP_TIMEOUT)
                if q_emb:
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
            except Exception as e:
                logger.debug(f"[MinosMemory] Vector search skipped: {e}")

        return fuse_rankings([bm25_ranked, vector_ranked], timestamps, top_k)

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
                    self._semantic_memory = clean_cot_and_tags(data.get("semantic_memory", ""))
                    self._working_memory = list(data.get("working_memory", []))
                    self._pinned_memories = list(data.get("pinned_memories", []))
                    self._projects = dict(data.get("projects", {}))
            except Exception as e:
                logger.error(f"[MinosMemory] Failed to load memory file: {e}")

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
            logger.error(f"[MinosMemory] Failed to save memory file: {e}")

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
                logger.error(f"[MinosMemory] Failed to load graph file: {e}")

    def _save_graph_unlocked(self):
        try:
            atomic_write_json(self._graph_file, {
                "nodes": self._graph_nodes,
                "edges": self._graph_edges
            })
            self._graph_mtime = self._mtime(self._graph_file)
        except Exception as e:
            logger.error(f"[MinosMemory] Failed to save graph file: {e}")

    def _get_embedding(self, content: str, timeout: float = EMBEDDING_HTTP_TIMEOUT) -> Optional[List[float]]:
        clean = content.strip()
        if not clean:
            return None
        endpoints = [
            ("http://127.0.0.1:1234/v1/embeddings", {"input": clean, "model": "nomic-embed-text"}),
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
            logger.debug(f"[MinosMemory] Korean Bi-gram BM25 search failed: {e}")
            return []

    def _append_semantic_summary(self, summary: str):
        clean_sum = clean_cot_and_tags(summary).strip()
        if not clean_sum:
            return

        formatted = f"- [과거 압축 요약]: {clean_sum}"

        with self._shared_state():
            if self._semantic_memory.strip():
                combined = self._semantic_memory.strip() + "\n" + formatted
            else:
                combined = formatted

            max_chars = 3000
            if len(combined) > max_chars:
                lines = [l for l in combined.split("\n") if l.strip()]
                while len("\n".join(lines)) > max_chars and len(lines) > 2:
                    lines.pop(0)
                combined = "\n".join(lines)

            self._semantic_memory = combined
            self._save_memory_unlocked()

    def _condense_memory_thread(self, old_messages: list):
        def task():
            try:
                text_to_condense = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
                prompt = (
                    "당신은 과거 대화를 3줄 이내로 핵심만 요약하는 요약 도우미입니다. "
                    "사용자의 성향이나 중요한 팩트, 맥락 위주로 압축하세요. "
                    "별도의 서론이나 추가 메시지 없이 핵심 요약문만 3줄 이내의 글머리기호(-) 형태로 대답하세요.\n\n"
                    f"{text_to_condense}"
                )

                url = "http://127.0.0.1:1234/v1/chat/completions"
                payload = {
                    "model": "google/gemma-4-12b-qat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 500,
                    "stream": False
                }

                try:
                    res = requests.post(url, json=payload, timeout=35)
                    if res.status_code == 200:
                        res_data = res.json()
                        raw_summary = res_data["choices"][0]["message"]["content"].strip()
                        cleaned_summary = clean_cot_and_tags(raw_summary)
                        if cleaned_summary:
                            self._append_semantic_summary(cleaned_summary)
                            logger.info("[MinosMemory] Memory Condenser: Completed clean memory compression via LM Studio.")
                            return
                except Exception as ex:
                    logger.debug(f"[MinosMemory] LM Studio condensation failed, trying Ollama: {ex}")

                url_ollama = "http://127.0.0.1:11434/api/generate"
                payload_ollama = {
                    "model": "gemma4-e4b:q4km",
                    "prompt": prompt,
                    "stream": False
                }
                try:
                    res = requests.post(url_ollama, json=payload_ollama, timeout=25)
                    if res.status_code == 200:
                        raw_summary = res.json().get("response", "").strip()
                        cleaned_summary = clean_cot_and_tags(raw_summary)
                        if cleaned_summary:
                            self._append_semantic_summary(cleaned_summary)
                            logger.info("[MinosMemory] Memory Condenser: Completed clean memory compression via Ollama.")
                except Exception as ex:
                    logger.debug(f"[MinosMemory] Ollama condensation failed: {ex}")

            except Exception as e:
                logger.error(f"[MinosMemory] Memory Condenser background compression failed: {e}")

        threading.Thread(target=task, daemon=True).start()


def register(ctx):
    """Hermes plugin registration hook."""
    if hasattr(ctx, "register_memory_provider"):
        ctx.register_memory_provider(MinosMemoryProvider())
