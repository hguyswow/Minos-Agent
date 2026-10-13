# Minos v5.1 upgrade runbook (for an agent to execute)

Upgrades an existing Minos install (Hermes memory plugin v4.x and/or `standalone/minos_engine_v4.py` users)
to v5.1: one SQLite store `minos.db` (WAL, FTS5 trigram full-history search) shared by the Hermes plugin
and the standalone engine. Existing v4 JSON memory is migrated automatically on first start and kept as `*.v4_backup`.

## 0. Rules
- Work step by step and report the output of every check. Stop and report if a check fails.
- Never delete memory files. Back up before replacing anything.

## 1. Get v5.1
```
git clone https://github.com/hguyswow/Minos-Agent C:\temp\Minos-Agent-v5
```
New files: `hermes_plugin/minos/{__init__.py, store.py, plugin.yaml}`, `hermes_plugin/minos_pc/` (PC tools moved out
of the memory plugin), `standalone/{minos_engine_v4.py, minos_store.py}`.

## 2. Find every installed copy
- Hermes plugin copies: search the Hermes source checkout and Hermes home for `plugins/memory/minos/__init__.py`
  and `plugins/minos/__init__.py` (there are often several: source checkout, `installs/*/environments/*/workspace`,
  user plugin dirs, every profile). The one Hermes actually loads logs as `plugins.memory.minos`.
- Standalone users: every `minos_engine_v4.py` imported by your own scripts (e.g. a Telegram bot, a custom agent).
- Memory directory: `MINOS_STORAGE_DIR` if set (check `.env` files), otherwise `<hermes_home>/memories`.
  All programs that should share memory must point to the SAME directory.

## 3. Back up
Copy the memory directory and every plugin/standalone copy found in step 2 to a dated backup folder.

## 4. Stop writers
Stop the Hermes gateway (`hermes gateway stop`), any open Hermes chat/dashboard windows, and any script that imports
`minos_engine_v4.py` (Telegram bot etc.). Old processes keep old code in memory and would keep writing JSON.

## 5. Replace
- For each Hermes plugin copy: copy `__init__.py`, `store.py`, `plugin.yaml` from `hermes_plugin/minos/` into that folder;
  delete its `__pycache__`.
- Optional PC tools: copy `hermes_plugin/minos_pc/` to the user plugin dir and `hermes plugins enable minos_pc`.
- For each standalone copy: put `minos_engine_v4.py` AND `minos_store.py` side by side (the engine imports the store).
- `pip install rank-bm25` in the Python that runs them (chromadb is optional).

## 6. Start and verify
1. `hermes plugins doctor minos` → must say OK.
2. Start the gateway and the other programs again.
3. In the memory directory: `minos.db` exists and `minos_memory.json`, `minos_episodic.jsonl`, `minos_graph.json`
   were renamed to `*.v4_backup`.
4. Ask the agent to run the `memory_stats` tool → `backend: sqlite`, and the episode / pin counts match the old data.
5. Ask about something only present in old memory → it must be recalled.
6. If a standalone program shares the directory: pin a fact from it, then `list_pins` in Hermes → the fact appears.

## Rollback
Stop everything, restore the backed-up plugin/standalone files and rename the `*.v4_backup` files back
(delete or move away `minos.db`).
