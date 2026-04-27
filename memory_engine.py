import os
import json
import time
import requests
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


class MemoryEngine:
    """
    안티그래비티 초경량 범용 기억력 엔진 (Memory Engine)
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
        
    def _get_file_path(self, chat_id: str) -> str:
        return os.path.join(self.memory_dir, f"{chat_id}_memory.json")
        
    def load_memory(self, chat_id: str) -> Dict[str, Any]:
        path = self._get_file_path(chat_id)
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    pass
        return {
            "working_memory": [],
            "semantic_memory": ""
        }

    def save_memory(self, chat_id: str, data: Dict[str, Any]):
        path = self._get_file_path(chat_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def log_episodic(self, chat_id: str, role: str, content: str):
        """
        일화 기억 (Episodic Memory) 저장. 
        단순 로그(.jsonl)와 벡터 DB(ChromaDB)에 동시 기록합니다.
        """
        timestamp = time.time()
        
        # 1. 파일 로그 기록
        log_path = os.path.join(self.memory_dir, f"{chat_id}_episodic.jsonl")
        entry = {"timestamp": timestamp, "role": role, "content": content}
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
        # 2. ChromaDB (임베딩) 기록
        if self.chroma_collection:
            try:
                # Ollama API를 이용해 텍스트를 벡터로 변환
                res = requests.post('http://127.0.0.1:11434/api/embeddings', json={
                    'model': 'nomic-embed-text', # 기본 임베딩 모델
                    'prompt': content
                }, timeout=5)
                
                if res.status_code == 200:
                    embedding = res.json().get('embedding')
                    if embedding:
                        doc_id = f"{chat_id}_{timestamp}"
                        self.chroma_collection.add(
                            embeddings=[embedding],
                            documents=[content],
                            metadatas=[{"role": role, "chat_id": chat_id, "timestamp": timestamp}],
                            ids=[doc_id]
                        )
            except Exception as e:
                pass

    def add_message(self, chat_id: str, role: str, content: str):
        self.log_episodic(chat_id, role, content)
        mem = self.load_memory(chat_id)
        mem["working_memory"].append({"role": role, "content": content})
        if len(mem["working_memory"]) > self.max_working_memory:
            mem["working_memory"] = mem["working_memory"][-self.max_working_memory:]
        self.save_memory(chat_id, mem)

    def retrieve_past_context(self, chat_id: str, query: str, mode: str = 'embedding', top_k: int = 3) -> str:
        """
        사용자의 질문(query)에 기반하여 과거 일화 기억을 검색(RAG)합니다.
        """
        if not query.strip():
            return ""
            
        past_docs = []
        
        # [옵션 B: 임베딩 방식 검색]
        if mode == 'embedding' and self.chroma_collection:
            try:
                res = requests.post('http://127.0.0.1:11434/api/embeddings', json={
                    'model': 'nomic-embed-text',
                    'prompt': query
                }, timeout=5)
                if res.status_code == 200:
                    query_embedding = res.json().get('embedding')
                    if query_embedding:
                        results = self.chroma_collection.query(
                            query_embeddings=[query_embedding],
                            n_results=top_k,
                            where={"chat_id": chat_id}
                        )
                        if results['documents'] and results['documents'][0]:
                            past_docs = results['documents'][0]
            except Exception as e:
                print(f"[MemoryEngine] 임베딩 검색 실패, 키워드 모드로 폴백: {e}")
                mode = 'keyword' # 에러 발생 시 키워드 모드로 자동 Fallback
                
        # [옵션 A: 키워드(BM25) 방식 검색]
        if mode == 'keyword' and BM25Okapi:
            log_path = os.path.join(self.memory_dir, f"{chat_id}_episodic.jsonl")
            if os.path.exists(log_path):
                corpus = []
                with open(log_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            corpus.append(data['content'])
                        except:
                            pass
                if corpus:
                    # 형태소 분석기 대신 공백 기반 토큰화
                    tokenized_corpus = [doc.split() for doc in corpus]
                    bm25 = BM25Okapi(tokenized_corpus)
                    tokenized_query = query.split()
                    top_docs = bm25.get_top_n(tokenized_query, corpus, n=top_k)
                    past_docs = top_docs
                    
        if past_docs:
            context_str = "\n".join([f"- {doc}" for doc in past_docs])
            return context_str
        return ""

    def get_optimized_context(self, chat_id: str, base_system_prompt: str, current_query: str = "", memory_mode: str = 'embedding') -> List[Dict[str, str]]:
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
        messages.extend(mem["working_memory"])
        
        return messages

    def clear_memory(self, chat_id: str):
        mem = self.load_memory(chat_id)
        mem["working_memory"] = []
        self.save_memory(chat_id, mem)

    def update_semantic_memory(self, chat_id: str, new_semantic_text: str):
        mem = self.load_memory(chat_id)
        mem["semantic_memory"] = new_semantic_text
        self.save_memory(chat_id, mem)
