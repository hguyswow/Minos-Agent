<div align="center">
  <h1>🐙 Minos Local AI Agent</h1>
  <p><strong>Overcoming the limits of heavy agents. Maximizing the performance of Local LLMs.</strong></p>
</div>

<br>

## 🚀 What is Minos?

Minos is a fully independent, ultra-lightweight autonomous agent system designed to run entirely on your local PC. It uses **Ollama** as its brain, providing a completely private and blazingly fast AI experience without relying on external cloud APIs.

Unlike traditional chatbots, Minos acts as a true agent with its own **Nervous System (Tentacles)**, **Action Skills**, and a robust **Hybrid RAG Memory Engine**.

## 💡 Key Features

- 🧠 **Ultra-Lightweight Hybrid Memory Engine:** Features a 3-tier architecture (Working, Semantic, Episodic) with ChromaDB (Vector) and BM25 (Keyword) fallback RAG. Never lose context, even in 10,000+ line conversations.
- 🐙 **Nervous System (Tentacle Daemons):** Tiny, resource-efficient (0% CPU) background Python scripts that monitor the world (e.g., stocks, weather) 24/7 and "wake up" the heavy LLM only when a specific singularity/event occurs.
- 🛠️ **Extensible Skill System:** Add Python scripts as "skills" that Minos can use to read local files, scrape the web, read clipboard contents, or control Windows processes.
- 🪞 **Mirroring Sync:** Flawless real-time synchronization between the Telegram Messenger (Mobile) and the Web Dashboard (Desktop).
- 🧳 **100% Portable:** Designed to be installed on a USB and run on any PC with minimal setup.

## 📥 Installation (Portable Setup)

To run Minos on a completely new Windows PC:

1. Clone or download this repository.
2. Run `Setup-Environment.bat` (This will automatically install Python 3, Ollama, and pull necessary embedding models).
3. Run `Start-Minos.bat` to launch the Web Dashboard and Telegram Bot.
4. Access the Dashboard at `http://localhost:5000` to enter your Telegram Bot Token.

## 📖 Manual

For a detailed breakdown of the system architecture, memory logic, and tentacle operations:
- [Korean Manual (한국어 설명서)](docs/Manual_KR.md)
- [English Manual](docs/Manual_EN.md)

## ⚖️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## ☕ Support the Developer

If Minos has helped you optimize your local LLM experience, consider buying the developer a coffee!

- **PayPal:** [paypal.me/hguyswow](https://paypal.me/hguyswow)
- **KB 국민은행 (Kookmin Bank):** `027210862460 강*호`
