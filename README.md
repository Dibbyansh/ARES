# ARES — AI Emergency Response System

A Python project that uses AI to handle emergency incidents: classify them, plan tasks, assign teams, track progress, and send alerts.

---

## What It Does

You type an incident in plain English. The system:

1. **Classifies** it — type, severity, location, risks
2. **Plans** response tasks using emergency guidelines (RAG)
3. **Assigns** available teams to each task
4. **Tracks** status — activate, stabilize, or close
5. **Alerts** via Telegram (optional)

---

## How It Works

```
You type incident
       ↓
   app.py  →  loads teams + guidelines
       ↓
 Coordinator  →  runs agents in order
       ↓
 ┌─────────────────────────────────────┐
 │ Classifier → Planner → Assigner     │
 │      ↓          ↓          ↓        │
 │   Tracker → Alerter (if new)        │
 └─────────────────────────────────────┘
       ↓
   PostgreSQL (saves everything)
```

`app.py` always runs the **LangGraph coordinator** (`core/coordinator_langgraph.py`), where an AI router decides which agent runs next.

`core/coordinator.py` (fixed, step-by-step ordering, no AI routing) is kept in the repo for reference but is not wired into `app.py`.

---

## Project Structure

```
├── app.py                         # Start here — CLI entry point
├── config.py                      # Loads .env settings
├── evaluation.py                  # Evaluates LLM response correctness — not yet wired in, in progress
├── core/
│   ├── coordinator.py             # Simple sequential flow (not wired into app.py — kept for reference)
│   └── coordinator_langgraph.py   # AI-routed LangGraph flow (used by app.py)
├── agents/
│   ├── classifier.py              # Classify incident
│   ├── planner.py                 # Generate tasks (uses RAG)
│   ├── assigner.py                # Match teams to tasks
│   ├── tracker.py                 # Update task/incident status
│   └── alerter.py                 # Send Telegram alert
├── tools/
│   ├── llm.py                     # OpenRouter AI calls
│   ├── db.py                      # PostgreSQL operations
│   ├── rag.py                     # ChromaDB guideline search
│   └── telegram.py                # Telegram notifications
├── utils/
│   └── json_parser.py             # Strips code fences, parses AI JSON responses
├── teams.json                     # Emergency teams roster
├── docs.txt                       # Emergency guidelines (one per line)
├── schema.sql                     # Database tables
└── .env.example                   # Copy to .env and fill in
```

---

## Run Locally

**Requirements:** Python 3.10+, PostgreSQL, OpenRouter API key

### 1. Clone and set up Python

```bash
cd "ARES GitHub"
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Set up PostgreSQL

```sql
CREATE DATABASE ares;
```

```bash
psql -U postgres -d ares -f schema.sql
```

### 3. Configure environment

```bash
copy .env.example .env    # Windows
cp .env.example .env      # Mac/Linux
```

Edit `.env` — fill in at minimum:

```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
MODEL=model
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ares
DB_USER=postgres
DB_PASSWORD=your_password
```

Get an API key at [openrouter.ai](https://openrouter.ai). Telegram fields are optional.

### 4. Run

```bash
python app.py
```

Type an incident at the `ARES>` prompt. Type `exit` to quit.

---

## Live Example

```
ARES> Major fire at warehouse on 5th Street. Workers may be trapped.

⚡ Processing incident...
------------------------------------------------------------

🔍 Step 1: Classifying incident...
   Type: new
   Category: fire
   Severity: high
   Location: Warehouse, 5th Street

📋 Step 2: Planning response tasks...
   Generated 4 tasks:
   1. [HIGH] Evacuate all occupants immediately
   2. [HIGH] Establish water supply for suppression
   3. [HIGH] Search and rescue trapped workers
   4. [MEDIUM] Set up perimeter and traffic control

🧑‍🚒 Step 3: Assigning teams to tasks...
   Assigned 4 teams:
   - Fire Response Team → Evacuate all occupants immediately
   - Engine Company 1 → Establish water supply for suppression
   - Search & Rescue Unit → Search and rescue trapped workers
   - Police Unit → Set up perimeter and traffic control

📊 Step 4: Activating teams...
   ✓ Teams are now working on their tasks

🚨 Step 5: Sending alert...
   ✓ Alert sent (if Telegram is configured)

✅ Processing complete!

============================================================
INCIDENT SUMMARY
============================================================
Incident ID: 1
Type: new
Category: fire
Severity: high
Location: Warehouse, 5th Street
Status: active
============================================================
```

**Follow-up inputs** the system understands:
- `"Update on incident 1: fire spreading"` → links to existing incident
- `"Incident 1 is under control"` → stabilizing
- `"Incident 1 resolved, all clear"` → closes incident

---

## Credits

Educational project. Built for learning how multi-agent AI systems work.
