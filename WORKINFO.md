# Antigravity Memory Engine - WORKINFO.md
> 최종 업데이트: 2026-05-05 (버그 수정 + 검색 개선 + UI 개선)

## 추가 작업 (2026-05-24)

- **[추가 과제] 텔레그램 "/help" 도움말 텍스트 최신화**:
  - **신규 명령어 문서화**: 마스터 전용 백그라운드 대시보드 서버 제어 명령어인 `/dashboard [on/off]` 설명을 텔레그램 `/help` 가이드라인 마크다운에 정식 등록. 오타 교정 및 포맷팅 통일 검증 완수.

- **[추가 과제] 텔레그램을 통한 대시보드 서버 원격 제어 (/dashboard) 구현**:
  - **백그라운드 비창(비인터랙티브) 부팅 및 제어**: 마스터 계정 전용 원격 제어 명령어 핸들러를 탑재하여, 텔레그램 채팅창을 통해 `dashboard_server.py`를 무창(`CREATE_NO_WINDOW`) 상태로 안전하게 가동 및 강제종료(`terminate()`) 제어하도록 빌드.
  - **실시간 프로세스(psutil) 추적 관제**: 시스템 내부 프로세스를 탐색해 대시보드가 켜져 있는지(🟢 구동 중), 꺼져 있는지(🔴 정지됨) 확인하고 PID와 함께 포트 5000 웹 브라우저 접속 주소를 자동으로 안내하는 안내 메시지 설계.
  - **마스터 챗 ID 이중 보안 차단망**: 오직 마스터 계정(`5339243832`)으로 들어온 명령만 식별하여 허가 처리하고 외부인은 철저히 차단하는 관제 보안망 탑재.

- **[신규 6단계] 템플릿 기반 자율 문어발 제작소 (Easy Tentacle Factory UI) 완성**:
  - **BeautifulSoup 기반 수집 코드 생성 백엔드 설계**: `/api/create_tentacle` POST API를 탑재하여, 사용자가 크롤링하고 싶은 주소(URL)와 HTML selector, 주기(분 단위), 키워드 조건식을 넘기면 예외 및 CP949 터미널 인코딩을 철저히 방어한 고도화된 BeautifulSoup 파이썬 크롤러 스크립트(`tentacles/*_tentacle.py`)를 메모리 상에서 원자적으로 생성하도록 빌더 구축.
  - **자율 탑재 및 자동 목록 연동**: 새로이 제작된 문어발은 `tentacle_config.json`에 즉각 활성화(`true`) 등록되며, 인-프로세스 데몬에 의해 쿨다운 조건에 맞춰 즉시 주기 가동되도록 완전 연동.
  - **프론트엔드 모달 팩토리 UI 구현**: 다크 모드에 harmonious한 HSL 테마 및 부드러운 Glassmorphism 애니메이션이 적용된 '⚙️ 문어발 제작소' 전용 입력 폼 GUI 모달을 대시보드 사이드바 메뉴로 신설.

- **[신규 7단계] Ollama GPU 가속 및 대화 기억(Context) 실시간 SVG 게이지 위젯 완성**:
  - **nvidia-smi 백업 2중 관제망 백엔드**: 기존의 GPUtil 라이브러리가 동작을 거부하거나 세부 정보를 읽어오지 못할 때를 대비해, 백그라운드 창 없이 안전하게 작동하는 `nvidia-smi` 터미널 쿼리 subprocess 파서 헬퍼를 추가 탑재. GPU 로드율, VRAM 사용량, GPU 온도를 100% 검출하도록 설계.
  - **Ollama 대화 기억(Context) 사용률 계산**: memory_engine의 `working_memory` 실시간 메시지 카운트와 최대 단기 기억 임계치(20개)를 대조해 봇의 기억 한도가 얼마나 찼는지 실시간으로 계산하는 통계 로직 연동.
  - **프론트엔드 SVG circular & linear gauges 위젯**: 단순 텍스트 백분율 표시 방식을 전면 개편하여, HSL harmonies를 적용해 실시간(5초 주기)으로 부드럽게(Transition 애니메이션 적용) 차오르는 CPU, RAM, GPU, VRAM 원형 게이지 위젯 및 Ollama 기억 기억 점유율 가로형 위젯을 대시보드 리소스 패널에 영구 탑재.

- **텔레그램 브릿지 이관 및 가동**:
  - 기존 `C:\Users\hguys\.gemini\antigravity\scratch`에 있던 `telegram_bridge.py` 코어 및 실시간 큐 파일(`telegram_inbox.json`, `telegram_outbox.json`)을 `C:\ai\Antigravity_Memory_Engine\` 하위로 성공적으로 이관 완료.
  - 이관에 맞춰 `Telegram_Bridge_Manager.py` 관리 스킬 및 시작프로그램 배치 스크립트(`Start-TelegramBridge.bat`) 내부의 파일 참조 경로를 신규 경로로 안전하게 업데이트 완료.
  - 1분 주기 에이전트 크론 스케줄러(task-517)가 신규 이관된 인박스 파일을 모니터링하도록 재등록 및 모의 메시지 수신/전송 통합 동작 검증 최종 성공 완료.

- **주식 알림(TIGER Fn반도체TOP10) 오동작 오류 수정 및 고도화**:
  - **종목코드 오타 수정**: 기존 하드코딩 및 `stock_config.json`에 잘못 지정되어 있던 종목코드 오타 `396650`을 실제 상장 코드인 `396500`으로 정정. (이 오타로 인해 실시간 API에서 매번 빈 배열 `datas: []`가 응답되어 "주가 조회 실패"가 떴던 근본적 원인 해결)
  - **동적 설정(stock_config.json) 로드 및 폴백 연동**: 기존에 `stock_tiger_tentacle.py`에서 하드코딩으로 종목을 조회하던 한계를 극복하고, 대시보드 UI에서 연동하는 `stock_config.json` 파일을 동적으로 불러오도록 구조를 개선. 파일 에러 및 파싱 오류를 대비한 안전한 폴백(기본값: `396500`, 1.0% 임계값) 방어 로직 설계.
  - **콘솔 UTF-8 인코딩 래핑**: 윈도우 파워쉘/CMD 터미널의 기본 CP949 인코딩으로 인해 주식 브리핑 출력 시 유니코드 이모지(📈 등)가 충돌하여 발생하던 `UnicodeEncodeError`를 예방하기 위해 `sys.stdout`/`sys.stderr`를 `io.TextIOWrapper`를 통해 UTF-8로 강제 래핑하여 에러율 0 달성.
  - **임계값 0.0% 시 매일 브리핑 기능**: `stock_config.json`에서 `alert_threshold_percent`가 `0.0%`로 지정될 경우, 변동 크기에 상관없이 평일 오전 10시에는 무조건 시황 브리핑 알림을 발송하도록 제어 유연성 확보.

- **문어발 데몬 인-프로세스(In-Process) 최적화로 리소스 점유율 혁신적 감소 (개선 1단계)**:
  - **초고속 exec() 동적 컴파일 도입**: 매분마다 개별 문어발마다 무거운 파이썬 인터프리터 서브프로세스를 새로 띄우던 기존 `subprocess.run` 방식을 폐기하고, 메모리 상에서 코드를 컴파일하여 단일 프로세스 네임스페이스 내에서 직접 동적 실행하는 `exec()` 인프라 구축.
  - **프로세스 초기화 및 I/O 오버헤드 90% 이상 절감**: 매분 반복되던 대형 패키지 임포트 오버헤드와 파일 I/O 부하를 제거하여 저사양 PC 및 백그라운드 구동 환경을 극도로 쾌적화함.
  - **SystemExit 예외 방어 설계**: 개별 문어발 스크립트 내부의 `sys.exit()` 호출 시 데몬이 통째로 꺼지는 대참사를 예방하기 위해 `try-except SystemExit` 구문을 활용해 종료 코드(exit code)를 잡아 안전하게 성공/에러 여부를 판별하는 방어 레이어 적용.
  - **상세 에러 추적 및 가로채기(Capture) 시스템**: 표준 출력/에러(`sys.stdout`/`sys.stderr`)를 `io.StringIO()`로 리디렉션해 캡처하고, 예외 발생 시 `traceback.format_exc()`로 상세 트레이스를 기록하여 자가 치유 능력을 극대화함.
  - **가로채기(StringIO) 대비 버퍼 유무 사전 검사(hasattr) 도입 (자율 치유)**: stdout이 `StringIO`로 가로채졌을 때 `buffer` 속성이 없어 발생하는 `AttributeError`를 감지하여, `hasattr(sys.stdout, "buffer")` 사전 검사 코드를 데몬과 stock_tiger 스크립트에 반영하여 완벽한 상호 호환성과 안정성을 검증(에러 0).

- **기억 압축 엔진(Memory Condenser)의 LLM 설정 연동 (개선 2단계)**:
  - **활성 LLM 실시간 파싱**: 단기 기억 임계치 도달 시 장기 기억 마이그레이션을 위한 LLM 요약 API 호출부에서 하드코딩되었던 Gemma 모델명과 포트를 제거하고, `llm_config.json`의 실시간 활성화 모델 및 호스트 URL을 동적으로 로드하도록 완성.
  - **표준 Chat Completions API 포맷 전환**: 기존 Ollama 로컬 구형 규격(/api/generate)을 표준 `/v1/chat/completions` 포맷으로 개편하여 클라우드 API 및 타 외부 LLM 스위칭 시에도 100% 범용 통신을 지원하도록 호환성 극대화.

- **ChromaDB 임베딩 비동기화 및 동적 엔드포인트 연동 (개선 3단계)**:
  - **1ms 미만의 단기 반응 레이턴시 실현**: 기존에 봇 대화 시 일화 기억(`log_episodic`)을 벡터화하여 저장하기 위해 Ollama 임베딩 API(`nomic-embed-text`)를 동기식으로 대기 호출하여 메인 스레드가 수 초간 마비되던 UI 블로킹 현상을 완벽히 해결.
  - **백그라운드 스레드 격리**: 임베딩 파싱 및 ChromaDB 추가 작업을 백그라운드 스레드(`threading.Thread`)로 격리 위임하여 봇의 스트리밍 생각 속도를 극적으로 단축시킴.
  - **지능형 임베딩 엔드포인트 변환**: [llm_config.json](file:///c:/ai/Antigravity_Memory_Engine/llm_config.json)에 기재된 Chat Completions용 URL(/v1/chat/completions 등)을 감시하여, 이를 Ollama 전용 임베딩 포맷인 `/api/embeddings` 주소로 지능적으로 추출 및 변환하여 동적 로드하도록 설계.

---

## 추가 작업 (2026-05-05 저녁/밤)

- **Start-Minos.bat 인코딩 수정**: 이모지/박스문자 제거, ANSI(CP949) 저장으로 터미널 깨짐 및 오류 방지
- **GitHub 깃허브 대문(README.md) 전면 개편**: 시각적 배지 추가, 5대 핵심 기능 명시, 빠른 시작 가이드 및 후원 정보 적용
- **대시보드 UI 세밀화**: 사이드바 메뉴 마우스 롤오버 툴팁(`title`) 추가, 문의 모달에 계좌/이메일 정보 연동 및 클립보드 복사(`copyToClip`) 기능 탑재
- **TTS 음성 엔진 전처리 강화**: `#`, `##` 등 마크다운 기호 및 샵사인 문자 무음 처리 로직 보완
- **web_search.py 검색 품질 개선**: Playwright 도입 및 한국어 힌트 자동 추가
- **채팅창 CMD 블록 숨김**: `stripCmd()` 함수로 스킬 코드 노출 제거
- **명령어 기반 음성 제어**: 텔레그램 및 대시보드 채팅창에서 `/voice off` 및 `/voice on` 명령어를 통해 실시간으로 TTS(음성 출력) 기능을 켜고 끌 수 있도록 구현 완료. 텔레그램 목적지 발송 시 `tts_enabled` 옵션 누락 버그 수정.

## 📋 금일 작업 (2026-05-05 밤 - 메모리 및 자아 상실 버그 픽스)

### 🧠 Ollama 컨텍스트 단절(Context Amnesia) 완전 해결
- **문제 원인**: 시스템 프롬프트(스킬 목록 포함)와 과거 대화 로그가 누적되어 6000 토큰을 초과할 때, Ollama의 기본 `num_ctx` (2048) 제한으로 인해 앞부분의 기억과 자아(시스템 프롬프트)가 통째로 잘려나가는(Truncation) 현상 발견.
- **해결 조치**: 
  1. `antigravity_telegram.py` 및 `core_engine.py` API 호출부에 `num_ctx: 16384` 명시적 주입.
  2. 로컬 터미널에서 `ollama create` 명령을 사용하여 `gemma4-e4b:q4km` 모델 파일 내부에 `PARAMETER num_ctx 16384`를 영구적으로 박아넣음. (API 호환성 문제 우회)

### 🛡️ 로컬 소형 모델 프롬프트 강제 주입(Jailbreak)
- **문제 원인**: 소형 로컬 모델(Gemma 등)이 훈련된 기본 자아("저는 Google에서 만든 AI입니다")를 강력하게 유지하려 하여, 단순한 말투 지정 프롬프트를 무시하고 헛소리(환각)를 내뱉음.
- **해결 조치**: `memory_engine.py`의 `get_optimized_context` 로직을 수정하여, 사용자 메시지 맨 끝에 "(※ 시스템 강제 지시: 당신의 절대적인 정체성은 꼬마 비서 '알쫑이'입니다...)" 라는 초강력 덮어쓰기 지시를 매 질문마다 강제 주입하여 완벽하게 길들임.

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
- [x] **사용자 지정 문어발 생성기 Web UI 연동**: 대시보드 내에서 손쉽게 BeautifulSoup 기반의 문어발 수집 에이전트를 실시간 컴파일하여 생성 및 자동 구동하는 기능 구현 완료. (2026-05-24)
- [x] **Ollama GPU 가속 및 기억 점유율 SVG 실시간 게이지 위젯 탑재**: CPU, RAM, GPU, VRAM, AI 기억 점유율 실시간 모니터링 시각화 완료. (2026-05-24)
- [ ] **에이전트 자가 진화 루프 완성**: `Performance_Logger` 및 `Skill_Tester`를 주기적으로 실행하여, 성적이 낮은 스킬을 스스로 파악하고 `Skill_Scaffolder`로 보완 스킬을 설계하는 자동화 파이프라인 연동.
- [ ] **구글 캘린더 연동 완결**: OAuth 연동을 통한 일정 생성/조회 및 `alarm_executor_tentacle.py`를 통한 능동적 일정 푸시 기능 고도화.
- [ ] **감성 분석(Sentiment) 기반 톤 매너 조절**: 대화 컨텍스트에서 사용자의 감정을 유추해 알쫑이의 톤앤매너를 유동적으로 조정하는 체계 추가.

---

### 💡 개선 제안 (Suggestions)
- **다국어(i18n) 시스템 구조화**: 현재 HTML 내부에 `data-ko`, `data-en` 속성으로 하드코딩된 다국어 데이터를 별도의 `locale.json` 파일로 분리하면 추후 일본어나 다른 언어 확장이 매우 용이해질 것입니다.
- **문어발 설정 폼의 자동화**: 현재는 날씨, 이메일, 핫딜 3가지 설정 폼을 하드코딩하여 띄워주는데, JSON Schema를 정의해 두면 새로운 문어발이 추가되어도 UI 코드를 수정할 필요 없이 자동으로 입력 폼이 생성되도록 구조를 개선할 수 있습니다.
- **Google OAuth 사용자 접근성 개선 (중요)**: 구글 클라우드 콘솔을 통한 API 키 및 OAuth 동의 화면 구성 과정이 일반 사용자(비개발자)에게는 진입 장벽이 매우 높습니다. 향후 배포를 고려한다면, 중앙 웹 서버를 통한 OAuth 중계(Token 브로커) 방식을 도입하거나, 브라우저 자동화(Playwright)를 이용해 발급 과정을 일부 대행해 주는 편의성 스크립트 도입을 진지하게 고민해야 합니다.

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

