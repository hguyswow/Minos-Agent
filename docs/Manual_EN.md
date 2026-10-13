# Minos Local Agent System Manual

## 1. System Overview
Minos is a fully independent autonomous agent system that uses Ollama (local LLM) as its core brain. Going beyond traditional one-way chatbots (like OpenClo or Hermes), it combines a **Nervous System (Tentacles)**, **Action Skills (Skills)**, and a **Long/Short-term Memory Ledger (Memory Engine)** to control your Windows environment and monitor information in real-time.
This system is **designed by default to run continuously on a PC's SSD**, delivering 100% local performance without relying on internet stability or external clouds. Furthermore, because all data and configurations are centralized within the project folder, it offers the flexibility to be copied to a **USB drive for testing, emergencies, or backup** when migrating between PCs (Portable capability).

### ⚠️ Portable Requirements
If you wish to **run this system (via USB) immediately on a new computer**, the following 3 conditions must be met on the new machine:
1. **Python 3 Installed:** The essential engine required to run the agent's neural network (Python scripts) and the web dashboard server.
2. **Ollama Running:** Ollama, which acts as the actual 'Brain (LLM)' of Minos, must be installed and running in the background.
3. **AI Models Downloaded:** The specific text reasoning models (e.g., llama3, gemma) and the embedding model for memory processing (`nomic-embed-text`) must be `pull`ed into the Ollama engine.
*(The above conditions can be automatically set up by running the included `Setup-Environment.bat` file once.)*

## 2. Core Process & Synchronization
The Minos system supports a flawless **Mirroring Sync** in both directions: Telegram (Mobile) and the Web Dashboard (Desktop).

### Workflow
1. **Input:** The user issues commands via Telegram Messenger or the browser dashboard.
2. **Brain (Core Engine):** `core_engine.py` receives the command, evaluates its own status (CPU/RAM load, memory saturation) and available skills, and autonomously decides how to act.
3. **Memory (Memory Engine):** Decided actions and results are continuously logged into JSON files in the `memory_logs/` directory. When short-term memory is full, it automatically compresses/forgets old data to manage system load.
4. **Synchronization (Sync):** Commands sent from the dashboard instantly trigger a Telegram API call to push a notification to your mobile device. Commands sent via Telegram are pulled by the dashboard every 5 seconds by reading the memory, displaying them in real-time.

## 3. Ultra-Lightweight Memory Engine (Memory Processing Logic)
The core feature of the Minos system is its `Memory Engine`, which combines a 3-tier memory structure with a Hybrid RAG (Retrieval-Augmented Generation) system. Minos mimics human memory processing to overcome finite context window limitations.

### 3-Tier Memory Architecture
1. **Working Memory (Short-term):** Maintains only the most recent conversation history up to a set limit (default 30 turns). When the limit is reached, it automatically discards the oldest memory (FIFO) to prevent context overflow errors and maintain consistent response speeds.
2. **Semantic Memory (Long-term):** Condenses core user information, preferences, and crucial knowledge bases, perpetually injecting them into the system prompt.
3. **Episodic Memory:** All dialogue history is permanently preserved without deletion, saved into both a `.jsonl` file and a vector database (ChromaDB) complete with timestamps.

### Hybrid RAG Processing Workflow
When a user inputs a new question, Minos does not answer blindly. It undergoes the following process:
1. **Vector Embedding Search (Option B):** It converts the user's question into a vector using the `nomic-embed-text` model and queries ChromaDB to extract the top-K most semantically similar past episodic memories.
2. **Keyword Fallback Search (Option A):** If ChromaDB encounters an error or is unavailable, the system instantly falls back to a text-matching search mode using the `BM25` algorithm to ensure uninterrupted stability.
3. **Prompt Injection:** The retrieved past memories are fused with the current query and dynamically injected into the LLM's prompt under the section `[Past Related Conversation Context]`.
Through this mechanism, Minos can converse for tens of thousands of lines without speed degradation, accurately recalling past contexts.

## 4. Skill System Operation
Skills are the "hands and feet" that Minos uses to directly control the Windows system or retrieve external information. They exist as `.py` files in the `skill_system/skills/` folder.

### Key Skills & Features
- **PC_System_Status.py**: Queries current CPU, RAM, and storage status.
- **process_manager.py**: Forcefully terminates or checks the status of running Windows processes.
- **local_file_reader.py / clipboard_manager.py**: Reads text files and manages the clipboard.
- **screen_ocr.py**: Recognizes text on the screen and converts it to usable data.
- **web_search.py / web_scraper.py**: Performs real-time internet searches and scrapes web pages.
- **tentacle_manager.py**: Toggles background tentacles (daemons) on/off and queries their status.
- **gui_output_engine.py**: Displays output neatly in a separate GUI window.

### Auto-Approve Mechanism
Potentially dangerous commands require "User Approval" via the dashboard or Telegram. However, for frequently used, safe skills, you can toggle them on in the **[Skills (Auto-Approve)]** panel on the left side of the dashboard. Minos will execute these in 0.1 seconds without asking for permission.

## 5. Tentacle Daemon System Operation
Tentacles are the sensory organs that Minos runs quietly in the background to monitor information in real-time. They are `.py` files located in the `tentacles/` folder, managed by `tentacle_daemon.py`.

### Key Tentacles & Features
- **morning_brief_tentacle.py**: Collects weather and major news every morning to prepare a briefing.
- **stock_tiger_tentacle.py**: Monitors specific stocks or indicators in real-time. If it detects a sudden change, it signals the Agent's Brain (Core), prompting Minos to send a proactive message (first-contact text) to the user!

### Operation Method
In the dashboard's left panel, under the **[Tentacles (Daemon)]** accordion menu, you can click the toggle switch for each tentacle to turn it on or off in real-time.

## 6. Maintenance & Execution
### Running the System
- Double-click the `C:\ai\Antigravity_Memory_Engine\Start-Minos.bat` file.
- The Telegram Bot and the Dashboard Server will launch simultaneously in two separate terminal windows.
- Open your browser and navigate to `http://localhost:5000` to access the command dashboard.

### Telegram Bot Integration
- Click **[⚙️ Telegram Config]** at the bottom left of the dashboard.
- Enter the Telegram token obtained via `@BotFather` and click Save. The system will safely store it in `bot_config.json`.

### Adding New Skills
Simply command Minos in the chat window: "Write a python code that does [feature] and save it as a new skill." Minos will autonomously write the code, create a new `.py` file in the `skills/` folder, and equip it instantly.
