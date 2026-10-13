# 🚀 Minos Memory & Knowledge Operating Engine v4.0 이식 가이드 (Porting Guide)

> **다른 AI 에이전트(Hermes Agent, LangChain, AutoGPT, 커스텀 봇 등)에 Minos v4.0 엔진을 3분 만에 이식하고 적용하는 완벽 매뉴얼입니다.**

---

## 📌 1. 개요 (Architecture Overview)

**Minos v4.0**은 단순 텍스트 RAG를 넘어, 에이전트가 사람처럼 기억하고 지식을 구조화할 수 있도록 설계된 **하이브리드 기억 운영 엔진**입니다:
1. **지식 그래프 (Knowledge Graph)**: 엔티티 간 관계망(`A` ──[관계]──> `B`)을 영구 구축 및 동적 확장
2. **영구 중요 핀 (Pinned Facts)**: 14일 반감기 시간 감쇠 없이 최상단에 상시 고정 주입되는 핵심 팩트
3. **한국어 Bi-gram BM25Plus**: 한글 조사(`~을`, `~를`, `~에서`, `~으로`)에 영향받지 않는 100% 매칭
4. **ChromaDB 시계열 벡터 RAG**: 14일 반감기(Time-Decay)가 적용된 최신 기억 우선 재순위화
5. **프로젝트 상태판 (Active Project Dashboard)**: 작업 현황(`진행중`, `완료`)을 추적하고 세션 시작 시 브리핑
6. **시스템 제어 & 진단**: PC 볼륨 조절, 화면 잠금, 화이트리스트 앱 실행, 하드웨어 실시간 진단
7. **오디오북 자동 태거**: MP3 ID3v2 메타데이터 및 앨범 커버 자동 삽입 후 지식 그래프 연계

---

## 🛠️ 2. 필수 의존성 설치 (Prerequisites)

```bash
pip install -r requirements.txt
# 핵심 최소 패키지:
pip install chromadb rank-bm25 requests mutagen psutil
# Windows 시스템 볼륨 제어 기능 사용 시:
pip install pycaw comtypes
```

---

## 🅰️ 방법 A: Hermes Agent 프레임워크에 이식하기 (플러그인 형태)

Hermes Agent 계열에 이식할 때는 **단 1개 폴더 복사**로 즉시 작동합니다.

### 1단계: 플러그인 폴더 복사
저장소의 `hermes_plugin/minos/` 디렉토리를 대상 Hermes Agent의 플러그인 디렉토리로 복사합니다:
```powershell
# 예시 (Windows 환경)
Copy-Item -Recurse -Force "hermes_plugin/minos" "C:\Users\<사용자>\AppData\Local\hermes\plugins\minos"
```

### 2단계: Hermes 설정 활성화 (`config.yaml`)
`config.yaml` 파일에서 메모리 프로바이더를 `minos`로 지정합니다:
```yaml
memory:
  provider: "minos"
```

### 3단계: 게이트웨이 기동
```bash
hermes gateway run
```
* **결과**: 에이전트에 `pin_memory`, `update_project_status`, `add_knowledge_relation`, `query_knowledge_graph`, `get_system_status`, `tag_audiobook_mp3`, `control_pc_system` 총 7개의 전용 도구가 자동 탑재됩니다.

---

## 🅱️ 방법 B: 일반 파이썬 에이전트(LangChain, 커스텀 봇)에 이식하기

`standalone/minos_engine_v4.py` 모듈을 가져와 단 몇 줄로 이식할 수 있습니다.

### 1단계: 파일 배치
`standalone/minos_engine_v4.py` 파일을 대상 프로젝트의 라이브러리 디렉토리에 복사합니다.

### 2단계: 파이썬 코드 연동 예제

```python
from minos_engine_v4 import MinosEngine

# 1. 엔진 초기화 (데이터 저장 폴더 지정)
engine = MinosEngine(storage_dir="./my_agent_memory", lms_url="http://127.0.0.1:1234")

# 2. 중요 핀 박기 (영구 기억)
engine.pin_fact("사용자 호칭은 '형님'으로 부른다.")
engine.pin_fact("TIGER 반도체TOP10 알림은 매일 오전 10시 정각 브리핑")

# 3. 지식 그래프 관계 구축
engine.add_relation(source="형님", relation="관심분야", target="AI 에이전트 개발")
engine.add_relation(source="형님", relation="보유프로젝트", target="국화와 칼 오디오북")

# 4. 프로젝트 진행 상황 갱신
engine.update_project(
    project_name="국화와 칼 오디오북",
    status="completed",
    details="10부작 전체 음성 변환 완료"
)

# 5. 사용자 메시지가 들어왔을 때 -> LLM 프롬프트에 주입할 컨텍스트 생성
user_message = "오디오북 진행상황 어때?"
context_block = engine.get_context_block(query=user_message)

# LLM 시스템 프롬프트에 context_block을 합쳐서 전송!
system_prompt = f"""당신은 유능한 비서 AI입니다.
아래의 영구 기억과 지식 그래프를 바탕으로 답변하세요:
{context_block}
"""

# 6. 대화가 끝난 후 에피소드 기억 저장
assistant_reply = "형님! 국화와 칼 오디오북은 10부작 전체 변환이 완료되었습니다!"
engine.record_interaction(user_content=user_message, assistant_content=assistant_reply)
```

---

## 🧰 3. 에이전트 Function Calling (도구) 스키마 정의

OpenAI / Claude / Gemini API의 함수 호출(Function Calling)에 등록하려면 다음 JSON 스키마를 사용하세요:

### 1. `pin_memory` (중요 핀 등록)
```json
{
  "name": "pin_memory",
  "description": "사용자의 중요한 선호도, 규칙, 영구 설정, 핵심 팩트를 시간 감쇠 없이 영구 보존하는 중요 핀으로 등록합니다.",
  "parameters": {
    "type": "object",
    "properties": {
      "fact": {"type": "string", "description": "영구 보존할 팩트나 규칙"}
    },
    "required": ["fact"]
  }
}
```

### 2. `add_knowledge_relation` (지식 그래프 관계 등록)
```json
{
  "name": "add_knowledge_relation",
  "description": "지식 그래프에 엔티티 간의 관계를 추가합니다. (예: 주어: 형님, 관계: 관심종목, 대상: TIGER 반도체TOP10)",
  "parameters": {
    "type": "object",
    "properties": {
      "source": {"type": "string", "description": "주어 엔티티"},
      "relation": {"type": "string", "description": "관계명"},
      "target": {"type": "string", "description": "대상 엔티티"}
    },
    "required": ["source", "relation", "target"]
  }
}
```

### 3. `query_knowledge_graph` (지식 그래프 조회)
```json
{
  "name": "query_knowledge_graph",
  "description": "지식 그래프에서 특정 엔티티와 연결된 모든 속성과 관계망을 조회합니다.",
  "parameters": {
    "type": "object",
    "properties": {
      "entity": {"type": "string", "description": "조회할 엔티티 이름"}
    },
    "required": ["entity"]
  }
}
```

### 4. `update_project_status` (프로젝트 상태 갱신)
```json
{
  "name": "update_project_status",
  "description": "진행 중인 프로젝트 상태(in_progress, completed, paused)와 세부 결과를 갱신합니다.",
  "parameters": {
    "type": "object",
    "properties": {
      "project_name": {"type": "string", "description": "프로젝트 이름"},
      "status": {"type": "string", "enum": ["in_progress", "completed", "paused", "cancelled"]},
      "details": {"type": "string", "description": "진행 내용 요약"}
    },
    "required": ["project_name", "status", "details"]
  }
}
```

---

## 💾 4. 저장 파일 포맷 (Storage Layout)

지정된 `storage_dir` 안에 다음 파일들이 자동으로 생성 및 관리됩니다:
* `vector_db/`: ChromaDB 임베딩 영구 저장소
* `minos_graph.json`: 지식 그래프 엔티티 및 연결망 엣지 (JSON)
* `minos_memory.json`: 영구 핀 목록, 프로젝트 대시보드 상태 (JSON)
* `minos_episodic.jsonl`: 과거 대화 전체 로그 (Bi-gram BM25Plus 검색 대상)
