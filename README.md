<div align="center">

# 🐙 MINOS: Minos Memory Engine

**로컬 LLM의 한계를 뛰어넘는 초경량 자율 에이전트 시스템**<br>
*Overcoming the limits of heavy agents. Maximizing the performance of Local LLMs.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Ollama Powered](https://img.shields.io/badge/AI-Ollama-black?logo=ollama)](https://ollama.com)
[![Platform](https://img.shields.io/badge/platform-Windows-0078d7?logo=windows)](https://microsoft.com)

[**한국어(Korean)**](#-주요-기능) | [**English**](#-key-features)

</div>

<br>

## 🚀 What is Minos? (Minos Memory Engine)

**Minos**는 오프라인 로컬 PC 환경에서 완벽하게 독립적으로 구동되는 **초경량 자율 에이전트 시스템**입니다. 
외부 클라우드 API(OpenAI 등)에 의존하지 않고 **Ollama**를 두뇌로 사용하여 완벽한 프라이버시를 보장하면서도, 기존 챗봇의 한계를 뛰어넘는 진정한 '에이전트'로서 작동합니다.

*Minos is an **ultra-lightweight autonomous agent system** that runs completely independently in an offline local PC environment. By using **Ollama** as its brain without relying on external cloud APIs (such as OpenAI), it ensures complete privacy while operating as a true 'agent' that goes beyond traditional chatbots.*

무거운 기존 에이전트 프레임워크(OpenCLo, Hermes 등)와 달리, Minos는 **CPU/RAM 점유율 0%에 수렴하는 백그라운드 '촉수(Tentacles)'**와 강력한 **하이브리드 RAG 메모리 엔진**을 결합하여 로컬 자원을 극도로 효율적으로 사용합니다.

*Unlike heavy legacy agent frameworks (such as OpenCLo, Hermes, etc.), Minos combines **background 'Tentacles'** that converge to 0% CPU/RAM usage with a powerful **hybrid RAG memory engine** to utilize local resources extremely efficiently.*

<br>

---

## ✨ 핵심 기능 (Key Features)

### 🧠 1. 하이브리드 RAG 메모리 엔진 (Hybrid Memory)
단순한 대화 기록을 넘어 인간의 뇌 구조를 모방한 3단계 아키텍처(Working, Semantic, Episodic)를 채택했습니다.
- **ChromaDB (Vector)** + **BM25 (Keyword)** 듀얼 검색 엔진을 통해 10,000줄 이상의 방대한 대화에서도 문맥 유실이 발생하지 않습니다.

*It adopts a 3-stage architecture (Working, Semantic, Episodic) mimicking the human brain structure, going beyond simple conversation history.*
*- Through the dual search engine of **ChromaDB (Vector)** + **BM25 (Keyword)**, context loss does not occur even in massive conversations of over 10,000 lines.*

### 🐙 2. 자율 신경망 시스템: 문어발 (Tentacle Daemons)
무거운 LLM을 항상 켜두지 않습니다. 가벼운 Python 스크립트(문어발)들이 백그라운드에서 24시간 세계(주식, 날씨, 메일 등)를 모니터링하다가 **특정 이벤트(특이점)**가 발생할 때만 LLM을 깨워 스스로 생각하고 행동합니다.

*It doesn't keep heavy LLMs turned on at all times. Lightweight Python scripts (Tentacles) monitor the world (stocks, weather, email, etc.) 24/7 in the background and wake up the LLM to think and act only when **specific events (singularities)** occur.*

### 🛠️ 3. 즉각적인 행동: 스킬 시스템 (Action Skills)
Minos는 단순한 대화 상대가 아닙니다.
- `Playwright`를 이용한 실제 브라우저 렌더링 기반 한국어 웹 검색
- 로컬 파일 읽기/쓰기, 클립보드 제어, 시스템 프로세스 관리
- 필요한 기능을 Python 스크립트 하나로 무한 확장 가능

*Minos is not just a chatbot.*
*- Real browser rendering-based Korean web search using `Playwright`*
*- Local file read/write, clipboard control, and system process management*
*- Infinitely expandable functions with a single Python script*

### 📱 4. 완벽한 미러링 (Telegram ↔ Web Dashboard)
데스크톱의 **Web Dashboard**와 모바일의 **Telegram Bot**이 실시간으로 완벽하게 연동됩니다. 밖에서는 텔레그램으로 명령을 내리고, 집에서는 웹 대시보드로 시스템 자원과 로그를 모니터링하세요.

*The desktop **Web Dashboard** and the mobile **Telegram Bot** are perfectly linked in real-time. Give commands via Telegram outside, and monitor system resources and logs with the web dashboard at home.*

### 🧳 5. 100% 포터블 (Portable Setup)
USB에 담아서 어떤 윈도우 PC에 꽂아도 동작합니다. 환경 설정 스크립트 하나로 Python, Ollama, 필수 라이브러리, 브라우저 엔진까지 모두 자동 설치됩니다.

*You can save it on a USB drive and run it on any Windows PC. With a single environment setup script, Python, Ollama, required libraries, and the browser engine are all installed automatically.*

<br>

---

## 📥 빠른 시작 (Quick Start)

새로운 윈도우 PC에서 Minos를 실행하는 방법은 매우 간단합니다.
*Running Minos on a new Windows PC is very simple.*

1. **저장소 클론 또는 다운로드** (*Clone or download the repository*)
   ```bash
   git clone https://github.com/hguyswow/Minos-Agent.git
   cd Minos-Agent
   ```
2. **초기 환경 셋업 (최초 1회)** (*Initial environment setup (first time only)*)
   ```cmd
   Setup-Environment.bat
   ```
   *Python, Ollama 및 필수 AI 모델(Embedding), Playwright 등이 완전 자동으로 설치됩니다.*
   *\*Python, Ollama, essential AI models (Embedding), Playwright, etc., will be installed completely automatically.\**

3. **시스템 실행** (*Start the system*)
   ```cmd
   Start-Minos.bat
   ```
   *웹 대시보드와 텔레그램 봇이 백그라운드에서 자동 최소화 상태로 실행됩니다.*
   *\*Web Dashboard and Telegram Bot will run automatically minimized in the background.\**

4. **대시보드 접속** (*Access the Dashboard*)
   브라우저에서 `http://localhost:5000`에 접속하여 텔레그램 봇 토큰(Bot Token)을 입력하고 대화를 시작하세요!
   *Access `http://localhost:5000` in your browser, enter your Telegram Bot Token, and start chatting!*

<br>

---

## 📖 문서 및 메뉴얼 (Documentation)

시스템 아키텍처, 메모리 로직 및 문어발 데몬 생성 방법에 대한 상세한 가이드는 아래 문서를 참고하세요.
*Please refer to the documents below for detailed guides on system architecture, memory logic, and creating tentacle daemons.*

- 📘 [**한국어 설명서 (Korean Manual)**](docs/Manual_KR.md)
- 📙 [**English Manual**](docs/Manual_EN.md)

<br>

---

## 🛠️ 기술 스택 (Tech Stack)

- **AI Engine:** Ollama (Llama3, Qwen 등) + Faster-Whisper (STT) + Edge-TTS (음성)
- **Memory/Vector DB:** ChromaDB, Rank-BM25
- **Automation & Scraping:** Playwright (Chromium), DuckDuckGo Search
- **Backend/Frontend:** Python (Flask), Vanilla JS, Telegram Bot API

<br>

---

## ☕ 개발자 후원 (Support the Developer)

Minos 프로젝트가 로컬 AI 활용에 도움이 되셨다면, 개발자에게 커피 한 잔을 후원해 주시면 감사하겠습니다! ✨
*If the Minos project helped you utilize local AI, please consider supporting the developer with a cup of coffee! \**

- 💳 **PayPal:** [paypal.me/hguyswow](https://paypal.me/hguyswow)
- 🏦 **KB 국민은행:** `027210862460 강*호` (KB Kookmin Bank: `027210862460 Kang * Ho`)
- 📧 **이메일 문의 (Email Contact):** `hguyswow@gmail.com`

<br>

---

<div align="center">
  <p>Made with ❤️ by <b>hguyswow</b> & Minos AI</p>
  <p>This project is licensed under the <a href="LICENSE">MIT License</a>.</p>
</div>
