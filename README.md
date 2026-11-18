# "Why Did This Happen?" Multi-Agent Root Cause Analysis (RCA) System

An autonomous multi-agent incident investigation system designed to perform causal attribution across heterogeneous data sources (databases, code commits, incident logs, and analytics).

---

##  Architecture Overview

When presented with an anomaly or incident event (e.g. *"sales dropped 18% last week"*), the system decomposes the problem and coordinates a team of specialized investigator agents:

- **Manager / Orchestrator**: Manages state, breaks down the query into sub-hypotheses, evaluates evidence sufficiency, and drives the re-dispatch / stopping loop.
- **Data Agent**: Queries relational databases (SQL / Pandas) to isolate the anomaly by dimension (region, platform, user cohort).
- **Deploy / Code Agent**: Inspects GitHub commits, pull requests, and deployment logs around the event window.
- **Comms Agent**: Searches incident channels and chat logs (Slack / alerts) for correlated outages or team discussions.
- **Analytics Agent**: Evaluates conversion funnel metrics and user drop-off points.
- **Synthesizer**: Aligns findings onto a single chronological timeline, calculates causal confidence scores, and generates actionable fixes.

---

##  Repository Structure

```text
├── agents/                  # Specialized investigator agents
│   ├── manager.py           # LangGraph supervisor & stopping logic
│   ├── data_agent.py        # SQL & segmentation tool agent
│   ├── deploy_agent.py      # GitHub PR & commit inspector
│   ├── comms_agent.py       # Slack & incident chatter analyzer
│   ├── analytics_agent.py   # Funnel & conversion telemetry agent
│   └── synthesizer.py       # Evidence correlation & ranking engine
├── data/                    # Synthetic ground-truth datasets & schema
│   ├── seed_data.py         # Anomaly & noise database seeder
│   └── mock_slack_logs.json # Pre-seeded incident chat history
├── graph/                   # LangGraph state machine definitions
│   ├── state.py             # TypedDict & Pydantic state schemas
│   └── workflow.py          # StateGraph edges, nodes, and router
├── app.py                   # Streamlit dashboard interface
├── requirements.txt         # Project dependencies
├── WORKFLOW.md              # Detailed technical specification
└── RCA_Agent_Project_Blueprint.pdf # Project reference blueprint
```

---

##  Getting Started

### 1. Prerequisites
- Python 3.10+
- Git

### 2. Setup Virtual Environment
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## 📖 Documentation
For the full system specification, agent interaction contracts, stopping criteria, and college viva defense guide, see [WORKFLOW.md](WORKFLOW.md).

