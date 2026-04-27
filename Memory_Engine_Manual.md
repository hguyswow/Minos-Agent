# 안티그래비티 초경량 범용 기억력 엔진 (Memory Engine) 사용 설명서

본 문서는 `memory_engine.py` 모듈의 동작 원리 및 다른 파이썬 프로젝트에 범용적으로 이식(적용)하는 방법을 안내합니다.

## 🧠 1. 아키텍처 개요 (Tri-Tier Memory)

본 엔진은 무거운 에이전트 도구를 걷어내고, 오직 **'대화 문맥 유지'**에 최적화된 최신 3계층 아키텍처를 사용합니다.

1.  **단기 기억 (Working Memory - 롤링 윈도우)**
    *   최근 N개의 대화를 RAM처럼 즉각적으로 제공합니다.
    *   기본값은 20개(질문 10개, 답변 10개)이며 설정값을 넘어가면 가장 오래된 대화부터 자동으로 삭제하여 메모리 오버플로우를 방지합니다.
2.  **장기 기억 (Semantic Memory - 사용자 프로필)**
    *   시간이 지나 단기 기억에서 밀려나더라도 절대 잊지 말아야 할 사용자 특징이나 지시사항을 시스템 프롬프트에 영구 주입합니다.
3.  **일화 기억 (Episodic Memory - 영구 보관 로그)**
    *   모든 대화는 하드디스크(`memory_logs/`)에 JSONL 형태로 타임스탬프와 함께 영구 기록됩니다. 나중에 RAG(검색 증강 생성) 확장용으로 사용할 수 있습니다.

---

## 💻 2. 사용 방법 (다른 프로젝트에 적용하기)

`memory_engine.py` 파일만 복사해서 붙여넣으면 어떤 파이썬 챗봇 프로젝트(카카오톡, 디스코드, 웹서버 등)든 즉시 최신 뇌를 이식할 수 있습니다.

### Step 1. 엔진 초기화

```python
from memory_engine import MemoryEngine

# 메모리를 저장할 폴더와 최대 보관할 대화 수(롤링 윈도우 크기) 지정
memory = MemoryEngine(memory_dir="./my_bot_memory", max_working_memory=20)
```

### Step 2. 대화 기록 저장

사용자의 질문이나 AI의 답변이 생성될 때마다 `add_message` 함수를 호출하여 기억 상자에 넣습니다. (자동으로 디스크에 JSON으로 저장됩니다.)

```python
chat_id = "user_12345" # 사용자 고유 ID

# 사용자가 한 말 저장
memory.add_message(chat_id, role="user", content="내 이름은 철수야. 파이썬을 좋아해.")

# 챗봇이 한 말 저장
memory.add_message(chat_id, role="assistant", content="네, 알겠습니다 철수님!")
```

### Step 3. AI에게 최적화된 문맥(Context) 던져주기

AI 엔진(OpenAI, Ollama 등)에게 API 요청을 보낼 때, 방금 들어온 질문 1개만 덜렁 보내는 것이 아니라 `get_optimized_context` 함수를 통해 완벽히 조립된 과거 대화 리스트를 받아서 통째로 보냅니다.

```python
base_system = "당신은 친절한 어시스턴트입니다."

# 시스템 지시문 + 장기기억 + 과거대화 리스트를 모두 합쳐서 배열로 예쁘게 반환해 줌
messages_for_llm = memory.get_optimized_context(chat_id, base_system)

# 이 배열을 그대로 API에 전송
payload = {
    "model": "gemma4-e4b:q4km",
    "messages": messages_for_llm
}
# requests.post(..., json=payload)
```

### Step 4. 기억 포맷 (초기화)

사용자가 "기억 지워줘"라고 요청하면 다음 함수를 호출합니다. 단기 기억만 깨끗하게 포맷되며 영구 로그(Episodic Memory)는 백업용으로 남습니다.

```python
memory.clear_memory(chat_id)
```

### Step 5. (심화) 장기 기억 업데이트

나중에 다른 요약용 AI 에이전트를 돌려서 "이 사용자는 파이썬을 좋아함"이라는 사실을 알아냈다면, 다음과 같이 장기 기억에 영구 주입할 수 있습니다.

```python
memory.update_semantic_memory(chat_id, "사용자 이름: 철수\n선호 언어: 파이썬")
```

---

## 📂 3. 생성되는 파일 구조

봇을 구동하면 `memory_dir`에 지정한 폴더 내부에 다음과 같이 사용자별로 파일이 생성됩니다.

*   `{chat_id}_memory.json`: 현재 봇이 실시간으로 활용 중인 단기/장기 기억 상태
*   `{chat_id}_episodic.jsonl`: 지금까지 나눈 모든 대화의 무한 누적 로그 (타임스탬프 포함)

---

## 💾 4. 기억 백업 및 PC 이동 (영구 보존)

PC를 교체하거나 포맷하더라도 봇의 기억을 영구적으로 보존하고 다른 PC에서 그대로 이어서 사용할 수 있도록 **원클릭 백업/복구 기능**이 탑재되어 있습니다.

### 기억 백업하기 (현재 PC)
1. 이 폴더 안에 있는 `Backup_Memory.bat` 파일을 더블클릭합니다.
2. 현재까지의 모든 봇 기억(대화 기록)이 이 폴더 안의 `memory_backup` 폴더로 안전하게 복사됩니다.
3. 이제 이 `Antigravity_Memory_Engine` 폴더 전체를 USB나 클라우드(구글 드라이브 등)에 복사하여 새 PC로 옮깁니다.

### 기억 복구하기 (새 PC)
1. 새 PC로 폴더를 옮긴 후, 폴더 안에 있는 `Restore_Memory.bat` 파일을 더블클릭합니다.
2. 백업되었던 기억이 새 PC의 시스템으로 즉시 복원 및 활성화됩니다.
3. 봇을 켜고 텔레그램으로 대화를 걸면, 예전 PC에서 나누었던 마지막 대화부터 완벽하게 기억하고 답변합니다!

---

## 🛠️ 5. 봇의 자가 학습: 스킬(Skill) 저장소 시스템

안티그래비티 봇은 단순히 대화를 기억하는 것을 넘어, 터미널 명령어나 파이썬 스크립트를 작성하며 알게 된 유용한 도구들을 **'절차적 기억(Procedural Memory)'**으로 영구 학습할 수 있습니다.

*   **저장 위치:** 이 시스템은 `Antigravity_Memory_Engine/skill_system/` 폴더 내부에 완벽히 모듈화되어 있습니다.
*   **작동 원리 (초경량 아키텍처):**
    *   무거운 파이썬 코드와 스크립트 파일은 `skills` 폴더 깊숙이 파일로만 저장됩니다.
    *   봇의 뇌(잠재의식) 안에는 오직 `skills_index.txt` 에 기록된 "1줄짜리 사용법 요약" 만 주입됩니다.
    *   이를 통해 LLM의 토큰(VRAM) 낭비를 0에 가깝게 줄이면서 무한한 기능을 확장할 수 있습니다.
*   **자가 학습 방법:**
    *   봇이 채팅 중 스스로 유용하다고 판단되는 파이썬 코드를 `<SAVE_SKILL>` 태그로 감싸서 내뱉으면, 시스템이 이를 가로채어 자동으로 `.py` 스크립트를 생성하고 인덱스에 추가합니다.
    *   이후 봇은 필요할 때마다 `<CMD>python 경로/스킬.py</CMD>` 를 통해 습득한 스킬을 꺼내 씁니다.
