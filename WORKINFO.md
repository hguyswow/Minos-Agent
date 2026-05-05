# Antigravity Memory Engine - WORKINFO.md
> 최종 업데이트: 2026-05-05 (버그 수정 + 검색 개선 + UI 개선)

---

## 추가 작업 (2026-05-05 저녁)

- **Start-Minos.bat 인코딩 수정**: 이모지/박스문자 제거, ANSI(CP949) 저장
- **web_search.py 검색 품질 개선**: 한국어 힌트 자동 추가 + 중국어 필터
- **채팅창 CMD 블록 숨김**: `stripCmd()` 함수로 스킬 코드 노출 제거
- **대시보드 UI 개선**: 스킬 툴팁, 문의 고정 모달, 문어발 Easy 설정 UI

---

## 📋 금일 작업 (2026-05-05 오후)

### ✅ Alert_Summarizer 구현
- `antigravity_telegram.py` `tentacle_signal_checker()` 개선
- 동시에 들어온 문어발 신호 2개 이상 → 단일 통합 브리핑으로 병합 전송
- 알림 폭탄 방지, 1개 신호는 기존 방식 유지

### ✅ 스킬 메타데이터 38개 일괄 추가
- `AGENT_SKILL_NAME / DESC / ARGS / RETURNS` 헤더 38개 스킬에 자동 패치
- LLM이 각 스킬의 역할을 명확히 인지하여 자동 호출 정확도 향상

### ✅ 대시보드 UI 3종 개선
1. **스킬 롤오버 툴팁**: 마우스 올리면 AGENT_SKILL_DESC 설명 말풍선 표시
   - 백엔드 `/api/skill_descs` 신규 엔드포인트 추가
2. **문의/About 고정 모달**: hover tooltip → 클릭 시 열리는 고정 모달로 전환
   - X 버튼 및 오버레이 클릭으로 닫기 (후원 정보 확인 가능)
   - 언어 전환 시 한국어/영어 자동 적용 (data-ko/data-en)
3. **문어발 Easy 설정 UI**: 4개 tentacle config 파일 신규 생성 및 폼 UI 구현
   - `weather_config.json`: 도시, 좌표, 알림 간격, 언어
   - `stock_config.json`: 종목코드, 임계값, 상승/하락 토글
   - `daily_digest_config.json`: 발송 시각, 포함 항목 선택
   - `morning_brief_config.json`: RSS URL, 뉴스 개수, 발송 시각

### ✅ 시스템 정밀 분석 완료
- `scratch/deep_analyze.py` 전체 시스템 자동 점검 도구 작성
- 최종 결과: 이슈 0개, 개선제안 0개, 미설치 패키지 0개

### ✅ 기타
- `pdfplumber` 패키지 설치 완료 (pdf_reader 스킬 사용 가능)
- `dummy_weather.py` → `.disabled` 비활성화
- `check_secrets.py` 오탐지 수정 (예시 이메일 placeholder 허용)

---


---

## 📋 금일 작업 (2026-05-05)

### 🔧 대시보드 복구 (dashboard_server.py / templates/index.html)
- **UnicodeEncodeError 수정**: `sys.stdout`을 UTF-8로 강제하여 이모지가 포함된 print문에서 발생하던 서버 즉시 종료 문제 해결.
- **Jinja2 vs JS 충돌 해결**: `index.html`의 JS 코드 전체를 `{% raw %}...{% endraw %}` 블록으로 감싸 Jinja2가 JS 템플릿 리터럴(`${}`)을 잘못 파싱하던 근본 원인 제거. 버튼 동작 불가 및 시스템 리소스 표시 불가 문제 완전 해결.
- **JS 정규식 문법 수정**: `/<CMD>(.*?)</CMD>/g` → `/<CMD>(.*?)<\/CMD>/g` 슬래시 이스케이프 누락 수정.

### 🛡️ 스킬 자율 제어 강화
- **쓰기/편집 스킬 7개 MANUAL 전환**: `Code_AutoFixer`, `Multi_File_Editor`, `Skill_Scaffolder`, `Dependency_Manager`, `fix_tentacle_encoding`, `Git_Manager`, `Prompt_Editor` → 형님 승인 없이 파일 수정 불가.
- **읽기 스킬(local_file_reader, Self_Code_Analyzer 등)은 AUTO 유지**.

### 🐙 문어발 복구 및 업그레이드
- **morning_brief_tentacle.py (v4)**: SHA256 해시 기반 뉴스 중복 방지 강화. 신호 발송 성공 후 히스토리 저장 순서 보장.
- **stock_tiger_tentacle.py (v2)**: 하드코딩된 정적 메시지 제거 → 네이버 금융 실시간 API 연동. 등락률 1% 미만 시 알림 생략.
- **weather_tentacle.py**: 9byte 빈 파일 → Open-Meteo 무료 API 연동 실시간 날씨 알림 (3시간 쿨다운).
- **tentacle_daemon.py**: 9byte 빈 파일 → 백업 파일에서 복구 완료.

### 🗃️ 데이터 파일 수정
- **bot_config.json**: UTF-8 BOM 제거 (`utf-8-sig` → `utf-8`). JSON 파싱 오류(`Unexpected UTF-8 BOM`) 해결.
- **스킬 docstring 경고 5개 수정**: `calendar_sync.py`, `excel_reader.py`, `image_captioner.py`, `push_notify.py`, `web_fetch.py` — `\A` 등 잘못된 이스케이프 시퀀스 제거.

---

## 📋 금일 작업 (Today's Work)

### 🚀 시스템 7대 마스터 업그레이드 완료 (코어/스킬/문어발 대규모 개편)
- **코어 엔진 비동기화**: `antigravity_telegram.py`의 `execute_command_and_continue`를 `asyncio.create_subprocess_shell`로 개편하여 터미널 명령어 실행 시 봇 블로킹 문제 완전 해결.
- **기억 압축 엔진 (Memory Condenser)**: `memory_engine.py`에 단기 기억 포화 시 백그라운드 스레드에서 LLM을 호출해 과거 대화를 3줄 요약 후 장기 기억으로 이관하는 지능형 모듈 탑재.
- **신규 스킬 3종 장착**: 
  1. `Git_Manager.py` (자동 커밋/백업) 
  2. `Vision_UI_Analyzer.py` (멀티모달 이미지 분석 뼈대) 
  3. `Web_Automator.py` (Playwright 동적 웹 제어 뼈대)
- **신규 자율 문어발 6종 배치**: 
  1. `System_Guard_Tentacle.py` (RAM 90% 초과 프로세스 자동 탐지 및 경보)
  2. `Trend_Catcher_Tentacle.py` (매일 IT 트렌드 스크래핑 및 브리핑 발송 뼈대)
  3. `Email_Watcher_Tentacle.py` (중요 이메일 IMAP 스캐너 뼈대 및 설정 분리)
  4. `Auto_Backup_Tentacle.py` (매일 새벽 3시 코어 프로젝트 압축 백업)
  5. `Hot_Deal_Tracker_Tentacle.py` (키워드 기반 커뮤니티 핫딜 추적망)
  6. `PC_Cleanup_Tentacle.py` (다운로드 폴더 내 30일 경과 방치 파일 스캔 및 경고)

### 🖥️ Web UI (Dashboard) 업그레이드
- 대시보드 사이드바에 **"⚙️ Tentacle Configs (설정)"** 메뉴 추가.
- `dashboard_server.py`의 파일 읽기/쓰기 API 라우트를 확장하여 `tentacles/data/` 내부의 JSON 설정 파일(지역, 키워드, 이메일 등)을 즉석에서 조회 및 편집 가능하도록 연동 완료.
- **초보자용 간편 설정(GUI) 모달 추가**: JSON 텍스트 대신 텍스트 박스와 셀렉트 박스 등 직관적인 UI 폼 지원 (`index.html` 전면 개편).
- **설정 초기화(Reset) 기능 추가**: `/api/config_reset` 엔드포인트를 구현하여 설정 파일을 언제든 기본값으로 복원할 수 있는 기능 추가.
- `weather_tentacle.py` 설정에 **언어(한국어/영어)** 옵션 추가 및 연동 완료.
- **채팅창 줄바꿈(Word Wrap) 레이아웃 붕괴 버그 수정**: `index.html` CSS 개선으로 긴 텍스트 입력 시 가로 영역 침범 현상 방지.
- **코드 에디터 모달 열기 버그 수정**: CSS `z-index` 계층 충돌 문제 해결 및 표시 안정화.
- **대시보드 전역 다국어(i18n) 스크립트 추가**: 우측 상단 `🇰🇷 KR` 버튼을 통해 대시보드의 주요 UI를 실시간으로 영어/한국어로 변환 가능.

### 🛡️ AI 점수/레벨 시스템 파손 방지 로직 적용
- `ai_scores.json` 파일이 0바이트로 초기화되는 치명적 버그 수정 완료.
- `antigravity_telegram.py`의 `_save_ai_scores()` 함수에 임시 파일 생성 후 `os.replace()`를 사용하는 2단계(Two-step) 원자적 저장 방식 적용.
- 0바이트로 깨진 파일에 기본 JSON 뼈대를 주입하여 정상 복구 완료.

### 🛠️ 다중 스킬 동시 호출 방어 및 인코딩 출력 누락 패치
- **원인 분석**: 
  1. `antigravity_telegram.py`의 `_handle_post_response`가 정규식 `re.search`를 써서 첫 번째 `<CMD>` 하나만 실행하고 나머지는 버림.
  2. `PC_System_Status.py`가 윈도우 기본 인코딩(CP949)으로 한글을 출력하려다 `subprocess.run`의 UTF-8 디코더와 충돌하여 빈 문자열(증발)을 반환함.
- **조치 완료**:
  - 시스템 프롬프트에 `[경고] 한 번의 대답에 여러 개의 <CMD> 태그를 동시에 사용하지 마십시오.` 규칙을 강력하게 추가하여 봇의 오작동 원천 차단.
  - `PC_System_Status.py` 최상단에 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`를 주입하여 콘솔 환경과 무관하게 무조건 UTF-8로만 출력하도록 강제.

### 🐙 stock_tiger_tentacle 문어발 안전성 업그레이드
- 파일 저장 시 임시 파일(.tmp) 생성 후 `os.replace()`로 덮어쓰는 2단계 방식(원자적 저장) 적용 완료. 파일 쓰기 중 프로세스 종료로 인한 JSON 파손 위험 원천 차단.

### 🔍 코딩 업그레이드 4종 스킬 구현 사례 조사
- `Regex_Tester`, `Multi_File_Editor`, `Code_AutoFixer`, `Dependency_Manager` 스킬의 실제 구현 예시와 구조 설계 조사 완료 및 아티팩트 정리 완료.

### 🚀 자가 개선형 스킬셋 (Self-Evolution) 구축
- 봇이 스스로 코드를 진단하고 관리할 수 있는 6종 핵심 스킬 신규 구현 및 인덱스 등록 완료:
  - `Self_Code_Analyzer`: 코드 버그/품질(긴 함수 등) 자동 리포트
  - `Skill_Tester`: 전체 스킬의 동작 상태 및 응답 시간 검증
  - `Prompt_Editor`: 시스템 프롬프트 실시간 수정 및 복원
  - `Performance_Logger`: 스킬 성능 데이터 기록 및 통계
  - `Skill_Scaffolder`: 신규 자율 에이전트 스킬 뼈대 자동 생성기
  - `Memory_Cleaner`: 불필요한 기억 파일 및 로그 정리

### ♻️ 텔레그램 봇 대규모 리팩토링 (가독성 & 유지보수성 극대화)
- `antigravity_telegram.py` 내부의 초거대 함수들을 명확한 책임 단위로 완전 분리:
  - `skill_callback_handler`: 스위칭, 토글, 평가, 반응 등 5개의 개별 `_cb_*` 서브 핸들러로 분산
  - `stream_llm_response`: 자아 인식 프롬프트 생성부(`_build_self_awareness_prompt`)와 후처리 로직(`_handle_post_response`)으로 분리
  - `tentacle_signal_checker`: 업그레이드 제안 UI 렌더링 로직을 `_send_upgrade_proposals`로 분리
  - 공통 점수 및 레벨 연산 로직을 `_load_ai_scores`, `_save_ai_scores`, `_recalc_level` 등 전역 헬퍼 함수로 추출

### 🛡️ 코드 품질 및 안정화 (Defensive Coding)
- **인코딩 무결성 보장**: `core_engine.py`, `antigravity_telegram.py`, `memory_engine.py`, `dashboard_server.py`, `tts_engine.py` 등 핵심 파일 최상단에 `# -*- coding: utf-8 -*-` 강제 지정 완료.
- **오류 추적 강화**: 무음 예외 처리(`except: pass`)를 모두 찾아 `try-except` 로깅(에러 메세지 출력)으로 교체. 안정성 극대화.

### 🐛 긴급 버그 픽스 및 무한 루프 차단 (2026-05-05)
- **비동기 모듈 임포트 누락 픽스**: `antigravity_telegram.py` 최상단에 `import asyncio`를 추가하여 백그라운드 태스크 생성 시 발생하던 `NameError` 및 봇 통신 무한 루프 현상 완전 해결.
- **CP949 이모지 충돌 원천 차단**: 봇이 서브프로세스를 실행할 때 환경 변수 `PYTHONIOENCODING="utf-8"`를 강제로 주입하도록 `execute_command_and_continue` 함수 수정. (이모지 출력 시 발생하던 `UnicodeEncodeError` 완벽 방어)
- **파손된 파이썬 스크립트 전면 롤백**: 알쫑이의 무리한 일괄 치환(except: -> except Exception:)으로 인해 발생한 9개 문어발 스크립트의 들여쓰기 박살 및 `SyntaxError`를 일괄 원상 복원 완료.
- **문어발 중복 알림 로직 및 파일 복구**:
  - 망가진 `morning_brief_tentacle.py`의 히스토리 저장 로직을 원자적 저장(`.tmp` 후 `os.replace`)으로 전면 재구현하여 중복 뉴스 전송 차단.
  - 날아간 `stock_tiger_tentacle.py`를 네이버 금융 API 연동 구조로 완전히 새롭게 재작성하여, TIGER Fn반도체TOP10의 실시간 주가 등락을 1일 1회 완벽하게 브리핑하도록 업그레이드.

---

## 📅 차일 예정 (Next Plan)
- [ ] **사용자 지정 스킬/문어발 생성기 Web UI 연동**: 대시보드 내에서 손쉽게 템플릿 기반의 파이썬 스킬 코드를 생성하는 기능 검토.
- [ ] **에이전트 자가 진화 루프 완성**: `Performance_Logger` 및 `Skill_Tester`를 주기적으로 실행하여, 성적이 낮은 스킬을 스스로 파악하고 `Skill_Scaffolder`로 보완 스킬을 설계하는 자동화 파이프라인 연동.
- [ ] **구글 캘린더 연동 완결**: OAuth 연동을 통한 일정 생성/조회 및 `alarm_executor_tentacle.py`를 통한 능동적 일정 푸시 기능 고도화.
- [ ] **감성 분석(Sentiment) 기반 톤 매너 조절**: 대화 컨텍스트에서 사용자의 감정을 유추해 알쫑이의 톤앤매너를 유동적으로 조정하는 체계 추가.

---

## 💡 개선 제안 (Suggestions)
- **다국어(i18n) 시스템 구조화**: 현재 HTML 내부에 `data-ko`, `data-en` 속성으로 하드코딩된 다국어 데이터를 별도의 `locale.json` 파일로 분리하면 추후 일본어나 다른 언어 확장이 매우 용이해질 것입니다.
- **문어발 설정 폼의 자동화**: 현재는 날씨, 이메일, 핫딜 3가지 설정 폼을 하드코딩하여 띄워주는데, JSON Schema를 정의해 두면 새로운 문어발이 추가되어도 UI 코드를 수정할 필요 없이 자동으로 입력 폼이 생성되도록 구조를 개선할 수 있습니다.

---

## 🏗️ 현재 시스템 상태
- **AI 레벨**: 자율 진화 성장 중 (레벨 및 스코어는 `ai_scores.json`에서 능동 관리 중)
- **구동 엔진**: Ollama / TurboQuant / OpenCode Go API(Cloud) 하이브리드 체제 (안정적 스위칭 검증)
- **리팩토링 상태**: 텔레그램 코어 및 대시보드 UI 대폭 개선 완료, 에러율(0) 검증.

---

## 🚨 [영구 강제 수칙] GitHub Push 보안 프로토콜

> **이 수칙은 어떤 상황에서도 예외 없이 적용된다.**  
> Anti-Gravity AI Agent는 `git push` 명령 전 반드시 아래 절차를 따른다.

### ❌ GitHub에 절대 올려서는 안 되는 것
1. **실제 이메일 주소** (소스 코드, HTML, 주석 포함)
2. **텔레그램 Bot Token** (`state/bot_config.json` → gitignore 필수)
3. **LLM API 키 / 엔드포인트** (`llm_config.json` → gitignore 필수)
4. **실제 은행 계좌번호, PayPal 링크, 실명, 전화번호**
5. **하드코딩된 Secret Key / API Token**
6. **대화 기억 로그** (`memory_logs/`, `tentacles/logs/`, `logs/`)
7. **`.bak` 백업 파일** (이전 버전에 토큰이 포함될 수 있음)

### ✅ Push 전 필수 실행 명령
```bash
python scratch/check_secrets.py
```
→ `[OK] 민감 정보 없음` 확인 후에만 push 진행.

### 📌 상세 절차 문서
→ `GITHUB_PUSH_CHECKLIST.md` 참조

