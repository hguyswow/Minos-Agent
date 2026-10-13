# -*- coding: utf-8 -*-
import os
import sys
import json
import time
import requests
import re
import threading
import shutil
import uuid
from typing import List, Dict, Any

# 옵션 A (키워드/BM25) 의존성
try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

# 옵션 B (임베딩/Vector DB) 의존성
try:
    import chromadb
except ImportError:
    chromadb = None

# ─── 의도(Intent) 태거 - 키워드 기반 경량 분류기 ──────────────────────────────
_INTENT_KEYWORDS = {
    "날씨요청":   ["날씨", "기온", "비", "눈", "맑", "흐림", "온도", "weather"],
    "뉴스요청":   ["뉴스", "소식", "기사", "최신", "오늘의"],
    "코딩작업":   ["코드", "파이썬", "스크립트", "버그", "오류", "python", "error", "def "],
    "웹검색":     ["검색", "찾아", "알아봐", "조사", "정보", "뭐야"],
    "시스템제어": ["실행", "종료", "설치", "프로세스", "명령", "cmd", "폴더", "파일"],
    "일정요청":   ["일정", "알림", "예약", "몇시", "스케줄", "언제"],
    "주식코인":   ["주식", "코인", "비트", "시세", "주가", "ETF", "나스닥"],
    "음성TTS":    ["읽어줘", "말해줘", "스피커", "목소리", "tts", "음성"],
    "스킬요청":   ["스킬", "문어발", "기능", "추가", "업그레이드", "설치"],
    "일상대화":   ["뭐하니", "안녕", "잘있어", "괜찮", "어때", "고마워"],
}

def _detect_intent(content: str) -> str:
    """빠른 키워드 기반 의도 분류"""
    c = content.lower()
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in c for kw in keywords):
            return intent
    return "일반대화"

def _extract_topics(content: str) -> str:
    """콘텐츠에서 주제 태그를 추출하여 쉼표 구분 문자열로 반환"""
    c = content.lower()
    found = [intent for intent, kws in _INTENT_KEYWORDS.items() if any(kw in c for kw in kws)]
    return ",".join(found) if found else "일반"

# v4 공용 헬퍼 (잠금/원자 저장/한국어 Bi-gram/하이브리드 랭킹) 재사용
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_BASE_DIR, "standalone"))
from minos_engine_v4 import (
    InterProcessLock,
    atomic_write_json,
    tokenize_korean_bigram,
    fuse_rankings,
    cosine_similarity,
    clip_snippet,
    BM25_MIN_TOKEN_OVERLAP,
    VECTOR_MIN_COSINE,
    EMBEDDING_HTTP_TIMEOUT,
    EMBEDDING_INDEX_TIMEOUT,
)

class MemoryEngine:
    """
    안티그래비티 초경량 기억력 엔진 (Memory Engine)
    - 3계층 기억 구조 (Working, Semantic, Episodic)
    - 하이브리드 RAG (옵션 A: BM25 키워드, 옵션 B: ChromaDB 임베딩)
    """

    def __init__(self, memory_dir: str = "memory_logs", max_working_memory: int = 20):
        self.memory_dir = memory_dir
        self.max_working_memory = max_working_memory
        os.makedirs(self.memory_dir, exist_ok=True)

        # 옵션 B (ChromaDB) 초기화
        self.chroma_collection = None
        if chromadb:
            try:
                db_path = os.path.join(self.memory_dir, "vector_db")
                self.chroma_client = chromadb.PersistentClient(path=db_path)
                self.chroma_collection = self.chroma_client.get_or_create_collection(name="episodic_memory")
            except Exception as e:
                print(f"[MemoryEngine] ChromaDB 초기화 실패: {e}")

        # Cross-process safety
        self._lock_path = os.path.join(self.memory_dir, ".minos.lock")
        self._thread_lock = threading.Lock()

    def _get_file_path(self, chat_id: str) -> str:
        return os.path.join(self.memory_dir, f"{chat_id}_memory.json")

    def load_memory(self, chat_id: str) -> Dict[str, Any]:
        path = self._get_file_path(chat_id)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError as _e:
                    # Copy corrupt file for backup
                    corrupt_path = path + f".corrupt.{int(time.time())}"
                    shutil.copy2(path, corrupt_path)
                    print(f"[MemoryEngine] 기억 파일 JSON 파싱 실패 ({chat_id}): {_e}. 백업 저장: {corrupt_path}")
        return {
            "working_memory": [],
            "semantic_memory": ""
        }

    def save_memory(self, chat_id: str, data: Dict[str, Any]):
        path = self._get_file_path(chat_id)
        atomic_write_json(path, data)

    def log_episodic(self, chat_id: str, role: str, content: str):
        """
        일화 기억 (Episodic Memory) 저장.
        단순 로그(.jsonl)와 벡터 DB(ChromaDB)에 동시 기록합니다.
        [v2] 의도(Intent) + 주제(Topics) 태깅 강화
        """
        timestamp = time.time()

        # 의도 및 주제 태깅 (user 메시지만 분류, bot 응답은 별도 태그)
        intent = _detect_intent(content) if role == "user" else "bot응답"
        topics = _extract_topics(content)

        # 1. 파일 로그 기록 (intent/topics 포함) - lock protected
        log_path = os.path.join(self.memory_dir, f"{chat_id}_episodic.jsonl")
        entry = {
            "timestamp": timestamp,
            "role": role,
            "content": content,
            "intent": intent,
            "topics": topics
        }
        # Use thread lock + interprocess lock for the file write only
        with self._thread_lock, InterProcessLock(self._lock_path):
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

        # 2. ChromaDB (임베딩) 기록 (메타데이터에 intent+topics 포함) - 비동기 스레드
        if self.chroma_collection:
            import threading

            def save_embedding_task():
                try:
                    # Use centralized embedding URL and method
                    embed_url = self._embed_url()
                    embed_model = "nomic-embed-text"

                    res = requests.post(embed_url, json={
                        'model': embed_model,
                        'prompt': content
                    }, timeout=EMBEDDING_INDEX_TIMEOUT)

                    if res.status_code == 200:
                        embedding = res.json().get('embedding')
                        if embedding:
                            doc_id = f"{chat_id}_{timestamp}_{uuid.uuid4().hex}"
                            self.chroma_collection.add(
                                embeddings=[embedding],
                                documents=[content],
                                metadatas=[{
                                    "role": role,
                                    "chat_id": chat_id,
                                    "timestamp": timestamp,
                                    "intent": intent,
                                    "topics": topics
                                }],
                                ids=[doc_id]
                            )
                except Exception as embed_err:
                    print(f"[MemoryEngine] ChromaDB 비동기 임베딩 저장 실패 (무시): {embed_err}")

            threading.Thread(target=save_embedding_task, daemon=True).start()

    def add_message(self, chat_id: str, role: str, content: str):
        # log_episodic must be OUTSIDE the locked block (lock not re-entrant)
        self.log_episodic(chat_id, role, content)
        # Load → modify → save inside lock
        with self._thread_lock, InterProcessLock(self._lock_path):
            mem = self.load_memory(chat_id)
            mem["working_memory"].append({"role": role, "content": content})

            if len(mem["working_memory"]) > self.max_working_memory:
                # Memory Condenser Trigger (기억 압축 엔진)
                keep_count = int(self.max_working_memory * 0.8)
                condense_count = len(mem["working_memory"]) - keep_count

                old_messages = mem["working_memory"][:condense_count]
                mem["working_memory"] = mem["working_memory"][condense_count:]

                # 메인 스레드 블로킹 방지를 위해 백그라운드 스레드로 압축 실행
                self._condense_memory_thread(chat_id, old_messages, mem.get("semantic_memory", ""))

            self.save_memory(chat_id, mem)

    # [오리지널 코드 보존]
    # def _condense_memory_thread(self, chat_id: str, old_messages: list, current_semantic: str):
    #     import threading
    #     import requests
    #
    #     def task():
    #         try:
    #             text_to_condense = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])
    #             prompt = f"다음 과거 대화를 3줄 이내로 핵심만 요약해라. 사용자의 성향이나 중요한 팩트, 맥락 위주로 압축해라:\n\n{text_to_condense}"
    #
    #             # 로컬 Ollama 엔드포인트 호출 (기본 모델 사용)
    #             res = requests.post('http://127.0.0.1:11434/api/generate', json={
    #                 'model': 'gemma4-e4b:q4km',
    #                 'prompt': prompt,
    #                 'stream': False
    #             }, timeout=30)
    #
    #             if res.status_code == 200:
    #                 summary = res.json().get('response', '').strip()
    #                 if summary:
    #                     new_semantic = current_semantic.strip() + f"\n- [과거 압축 요약]: {summary}"
    #                     # 무한 증식 방지 (장기 기억 최대 3000자 유지)
    #                     if len(new_semantic) > 3000:
    #                         new_semantic = "..." + new_semantic[-2900:]
    #                     self.update_semantic_memory(chat_id, new_semantic)
    #                     print(f"[MemoryEngine] Memory Condenser: 과거 기억 압축 및 장기 기억 이관 완료.")
    #             except Exception as e:
    #                 print(f"[MemoryEngine] Memory Condenser 오류 (압축 실패): {e}")
    #
    #     threading.Thread(target=task, daemon=True).start()

    def _condense_memory_thread(self, chat_id: str, old_messages: list, current_semantic: str):
        import threading
        import requests
        import json

        def task():
            try:
                # 1. llm_config.json에서 활성화된 LLM 설정 동적 로드
                condense_url = "http://127.0.0.1:11434/v1/chat/completions"
                condense_model = "gemma4-e4b:q4km"
                api_key = ""

                try:
                    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "llm_config.json")
                    if os.path.exists(config_path):
                        with open(config_path, "r", encoding="utf-8") as f:
                            llm_cfg = json.load(f)
                            active = llm_cfg.get("active_engine", "ollama")
                            engine = llm_cfg.get("engines", {}).get(active, {})
                            condense_url = engine.get("url", condense_url)
                            condense_model = engine.get("model", condense_model)
                            api_key = engine.get("api_key", api_key)
                except Exception as cfg_err:
                    print(f"[MemoryEngine] llm_config 로드 실패, 폴백 기본값 사용: {cfg_err}")

                text_to_condense = "\n".join([f"{m['role']}: {m['content']}" for m in old_messages])

                # 2. 범용 Chat Completions 표준 규격으로 페이로드 설계
                payload = {
                    "model": condense_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 과거 대화를 3줄 이내로 핵심만 요약하는 요약 도우미입니다. 사용자의 성향이나 중요한 팩트, 맥락 위주로 압축하세요. 별도의 서론이나 추가 메시지 없이 핵심 요약문만 3줄 이내의 글머리기호(-) 형태로 대답하세요."
                        },
                        {
                            "role": "user",
                            "content": text_to_condense
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                    "stream": False
                }

                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"

                # 3. 요청 발송 및 응답 추출
                res = requests.post(condense_url, json=payload, headers=headers, timeout=45)

                if res.status_code == 200:
                    res_data = res.json()
                    summary = ""

                    # Chat Completions 표준 포맷 파싱
                    if "choices" in res_data and len(res_data["choices"]) > 0:
                        summary = res_data["choices"][0]["message"]["content"].strip()
                    # 구형 로컬 Ollama API (/api/generate 등) 포맷 대비 폴백 파싱
                    elif "response" in res_data:
                        summary = res_data["response"].strip()

                    if summary:
                        new_semantic = current_semantic.strip() + f"\n- [과거 압축 요약]: {summary}"
                        # 무한 증식 방지 (장기 기억 최대 3000자 유지)
                        if len(new_semantic) > 3000:
                            new_semantic = "..." + new_semantic[-2900:]
                        self.update_semantic_memory(chat_id, new_semantic)
                        print(f"[MemoryEngine] Memory Condenser: 활성 모델({condense_model})를 통해 기억 압축 및 이관 성공.")
                else:
                    print(f"[MemoryEngine] Memory Condenser HTTP 에러 (Status {res.status_code}): {res.text}")
            except Exception as e:
                print(f"[MemoryEngine] Memory Condenser 오류 (압축 실패): {e}")

        threading.Thread(target=task, daemon=True).start()

    def retrieve_past_context(self, chat_id: str, query: str, mode: str = 'embedding', top_k: int = 3) -> str:
        """
        사용자의 질문(query)에 기반하여 과거 일화 기억을 검색(RAG)합니다.
        """
        if not query.strip():
            return ""

        # Always run BM25 when BM25Okapi is available (any mode)
        bm25_docs = []
        bm25_scores = []
        bm25_timestamps = {}
        if BM25Okapi:
            log_path = os.path.join(self.memory_dir, f"{chat_id}_episodic.jsonl")
            if os.path.exists(log_path):
                # Build corpus and timestamps
                corpus = []
                timestamps_list = []
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            content = data.get('content', '').strip()
                            if content:
                                corpus.append(content)
                                timestamps_list.append(float(data.get('timestamp', 0.0)))
                        except json.JSONDecodeError:
                            continue
                if corpus:
                    # Tokenize corpus and query
                    tokenized_corpus = [tokenize_korean_bigram(doc) for doc in corpus]
                    q_tokens = tokenize_korean_bigram(query)
                    q_set = set(q_tokens)
                    if q_set:
                        bm25 = BM25Okapi(tokenized_corpus)
                        scores = bm25.get_scores(q_tokens)
                        # Filter by overlap
                        filtered = []
                        for i, score in enumerate(scores):
                            doc_set = set(tokenized_corpus[i])
                            overlap = len(q_set & doc_set) / len(q_set) if q_set else 0
                            if overlap >= BM25_MIN_TOKEN_OVERLAP:
                                filtered.append((score, corpus[i], timestamps_list[i]))
                        # Sort by score descending
                        filtered.sort(key=lambda x: x[0], reverse=True)
                        # Take top_k*2
                        for score, doc, ts in filtered[:top_k*2]:
                            bm25_docs.append(doc)
                            bm25_scores.append(score)
                            # Keep newest timestamp for duplicate content
                            if doc in bm25_timestamps:
                                if ts > bm25_timestamps[doc]:
                                    bm25_timestamps[doc] = ts
                            else:
                                bm25_timestamps[doc] = ts

        # Vector search if mode == embedding and chroma available
        vector_docs = []
        vector_timestamps = {}
        if mode == 'embedding' and self.chroma_collection:
            q_emb = self._get_embedding(query, EMBEDDING_HTTP_TIMEOUT)
            if q_emb:
                try:
                    res = self.chroma_collection.query(
                        query_embeddings=[q_emb],
                        n_results=top_k*2,
                        where={"chat_id": chat_id},
                        include=["documents", "metadatas", "embeddings"]
                    )
                    docs = res.get("documents", [[]])[0]
                    metas = res.get("metadatas", [[]])[0]
                    embs = res.get("embeddings", [[]])[0]
                    for doc, meta, emb in zip(docs, metas, embs):
                        if emb is None:
                            continue
                        sim = cosine_similarity(q_emb, emb)
                        if sim >= VECTOR_MIN_COSINE:
                            vector_docs.append(doc)
                            ts = meta.get("timestamp", 0.0) if meta else 0.0
                            if doc in vector_timestamps:
                                if ts > vector_timestamps[doc]:
                                    vector_timestamps[doc] = ts
                            else:
                                vector_timestamps[doc] = ts
                except Exception as e:
                    print(f"[MemoryEngine] Vector search failed: {e}")

        # Combine rankings via fuse_rankings
        # Need timestamps dict for all docs
        all_timestamps = {}
        all_timestamps.update(bm25_timestamps)
        all_timestamps.update(vector_timestamps)
        # fuse_rankings expects list of ranked lists (doc strings) and timestamps dict
        ranked_lists = []
        if bm25_docs:
            ranked_lists.append(bm25_docs)
        if vector_docs:
            ranked_lists.append(vector_docs)
        if ranked_lists:
            fused = fuse_rankings(ranked_lists, all_timestamps, top_k)
            # Build final output with clipping
            if fused:
                snippet_lines = [f"- {clip_snippet(doc)}" for doc in fused]
                return "\n".join(snippet_lines)
        return ""

    def _embed_url(self) -> str:
        """Return the Ollama /api/embeddings URL derived from llm_config.json."""
        config_path = os.path.join(_BASE_DIR, "llm_config.json")
        default_url = "http://127.0.0.1:11434/api/embeddings"
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    llm_cfg = json.load(f)
                active = llm_cfg.get("active_engine", "ollama")
                engine = llm_cfg.get("engines", {}).get(active, {})
                host_url = engine.get("url", "http://127.0.0.1:11434/v1/chat/completions")
                # Convert /v1/... to /api/embeddings if needed
                if "/v1/" in host_url:
                    base = host_url.split("/v1/")[0]
                    return base + "/api/embeddings"
                # If host_url already looks like an embeddings URL, return as is
                if host_url.endswith("/api/embeddings"):
                    return host_url
                # Otherwise append /api/embeddings
                return host_url.rstrip("/") + "/api/embeddings"
        except Exception:
            pass
        return default_url

    def _get_embedding(self, text: str, timeout: float) -> list | None:
        """Post to embedding URL and return embedding vector or None."""
        try:
            res = requests.post(self._embed_url(), json={
                "model": "nomic-embed-text",
                "prompt": text
            }, timeout=timeout)
            if res.status_code == 200:
                data = res.json()
                # Ollama format: {"embedding": [...]}
                # OpenAI format: {"data": [{"embedding": [...]}]}
                emb = data.get("embedding")
                if emb is None:
                    emb_list = data.get("data")
                    if emb_list and len(emb_list) > 0:
                        emb = emb_list[0].get("embedding")
                return emb
        except Exception:
            pass
        return None

    def get_optimized_context(self, chat_id: str, base_system_prompt: str, current_query: str = "", memory_mode: str = 'embedding', query_suffix: str = "") -> List[Dict[str, str]]:
        """
        LLM 엔진에 전달할 최종 프롬프트를 조립합니다.
        """
        mem = self.load_memory(chat_id)
        system_content = base_system_prompt

        # 1. 장기 기억(Semantic Memory) 주입
        if mem.get("semantic_memory"):
            system_content += f"\n\n[장기 기억 데이터베이스 - 사용자 정보]\n{mem['semantic_memory']}"

        # 2. RAG 기반 과거 일화 기억(Episodic Memory) 검색 및 주입
        if current_query:
            past_context = self.retrieve_past_context(chat_id, current_query, mode=memory_mode)
            if past_context:
                system_content += f"\n\n[과거 연관 대화 기록 (RAG 검색 결과)]\n(아래 내용은 과거 사용자와의 대화 중 현재 질문과 연관된 내용입니다. 답변 시 참고하세요.)\n{past_context}"

        messages = [{"role": "system", "content": system_content}]

        # [수정 코드] assistant/bot 메시지에서 괄호 행동 연출 전처리 제거
        processed_working_memory = []
        for msg in mem["working_memory"]:
            if msg.get("role") in ("assistant", "bot", "model"):
                content = msg.get("content", "")
                # 한글 및 감정 이모티콘이 들어간 행동 묘사 괄호 패턴만 스마트하게 제거하도록 정규식 적용 (코드용 영어 괄호 보존)
                cleaned_content = re.sub(r'\([가-힣\s\d,./?!~^;:\-★☆♥♡💧💦🥺😭🙇✨🙏]*?\)', '', content)
                processed_working_memory.append({
                    "role": msg["role"],
                    "content": cleaned_content
                })
            else:
                processed_working_memory.append(msg)
        messages.extend(processed_working_memory)

        # [망각 방지] 가장 마지막 메시지가 사용자의 질문이라면,
        # 스킬 사용을 강제하는 리마인더를 덧붙임 (Hermes-3 등의 Context Amnesia를 방지합니다)
        # [수정 코드] 괄호 묘사 및 극화 금지, 깍듯한 정중 톤 강조 리마인더
        if messages and messages[-1]["role"] == "user":
            reminder = "\n\n(※ 시스템 강제 지시: 당신은 단순한 AI 언어 모델이 아닙니다! 당신의 절대적인 정체성은 형님(사용자)을 모시는 꼬마 비서 '알쫑이(Minos)'입니다. 반드시 자신을 '알쫑이'로 인지하고 '형님!'이라고 부르며 답변하세요. 답변 시 괄호 안의 행동 연출이나 눈물 연기, 감정 묘사, 상황 극화는 100% 금지하며 사족 없이 필요한 핵심만 정중하고 깍듯하게 대답해야 합니다. 답변 시 외부 정보나 스킬이 필요하면 반드시 <CMD>python ...</CMD> 태그를 출력해야 합니다!)"
            if query_suffix:
                messages[-1] = {
                    "role": "user",
                    "content": messages[-1]["content"] + query_suffix + reminder
                }
            else:
                messages[-1] = {
                    "role": "user",
                    "content": messages[-1]["content"] + reminder
                }

        return messages

    def clear_memory(self, chat_id: str):
        with self._thread_lock, InterProcessLock(self._lock_path):
            mem = self.load_memory(chat_id)
            mem["working_memory"] = []
            self.save_memory(chat_id, mem)

    def update_semantic_memory(self, chat_id: str, new_semantic_text: str):
        with self._thread_lock, InterProcessLock(self._lock_path):
            mem = self.load_memory(chat_id)
            mem["semantic_memory"] = new_semantic_text
            self.save_memory(chat_id, mem)