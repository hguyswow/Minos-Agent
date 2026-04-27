# 🛠️ 안티그래비티 스킬 시스템 (Procedural Memory) 개발자 가이드

이 폴더(`skill_system/`)는 안티그래비티 봇의 **절차적 기억(Procedural Memory)** 모듈입니다.
무거운 파이썬 코드는 이 폴더 안에 파일로만 보관하고, 봇의 뇌에는 가벼운 1줄 요약만 주입하는 **초경량 아키텍처**로 설계되었습니다.

---

## 📁 폴더 구조

```
skill_system/
├── skill_registry.py     # 스킬 저장/로드 핵심 모듈 (다른 프로젝트 이식 시 이 파일 사용)
├── skills_index.txt      # 봇의 잠재의식에 주입되는 가벼운 스킬 목록 (1줄 요약)
└── skills/               # 실제 파이썬 스크립트 보관소 (봇의 뇌에 들어가지 않음)
    └── PC_System_Status.py  # 내장 스킬 예시
```

---

## ⚙️ 작동 원리

1. **봇이 생각을 시작할 때마다** `skills_index.txt` 를 읽어 현재 등록된 스킬 목록을 System Prompt 하단에 자동 주입합니다.
2. **봇이 스킬이 필요하다고 판단하면** `<CMD>python 스킬경로.py</CMD>` 를 출력하여 실제로 실행하고 결과를 받아봅니다.
3. **봇이 새로운 코드를 짜다가 "재사용 가능하다!" 판단하면** `<SAVE_SKILL>` 태그를 출력하여 스스로 이 폴더에 `.py` 파일을 생성하고 `skills_index.txt` 에 추가합니다.

---

## 🔧 다른 PC 또는 프로젝트에 이식하는 방법

### Step 1: 파일 복사
이 `skill_system/` 폴더 전체를 새 PC로 복사합니다.

### Step 2: `skill_registry.py` 임포트
```python
import sys
sys.path.append(r'경로\skill_system')
from skill_registry import SkillRegistry

skills = SkillRegistry(system_dir=r'경로\skill_system')
```

### Step 3: 시스템 프롬프트에 인덱스 주입
```python
skills_text = skills.get_skills_index_text()
dynamic_prompt = BASE_SYSTEM_PROMPT + f"\n\n[장착된 스킬 목록]\n{skills_text}"
```

### Step 4: 봇 응답 처리 시 `<SAVE_SKILL>` 태그 파싱
```python
import re
skill_match = re.search(r'<SAVE_SKILL name="(.*?)" desc="(.*?)">(.*?)</SAVE_SKILL>', reply, re.DOTALL)
if skill_match:
    skills.save_skill(skill_match.group(1), skill_match.group(2), skill_match.group(3))
```

---

## ✍️ 스킬 수동 등록 방법

`skills_index.txt`를 메모장으로 열어서 아래 형식으로 한 줄 추가 후 저장:
```
- 스킬이름: 기능 설명 (실행: <CMD>python C:\경로\스킬이름.py</CMD>)
```
그리고 `skills/` 폴더에 해당 `.py` 파일을 직접 작성하여 저장하면 즉시 적용됩니다.
다음번 봇 대화 시작 시부터 그 스킬이 봇의 잠재의식에 자동으로 주입됩니다.
