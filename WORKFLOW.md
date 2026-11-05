# "Why Did This Happen?" Multi-Agent RCA System Workflow

This document defines the operational architecture, state machine, data contracts, and implementation workflow for the Multi-Agent Root Cause Analysis (RCA) system based on `RCA_Agent_Project_Blueprint.pdf`.

---

## 1. System Architecture & Information Flow

The architecture decouples investigation into specialized domain agents orchestrated via **LangGraph**:

```
+-------------------------------------------------------------+
|               User Event ("sales dropped 18%")              |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     Manager Orchestrator                    |
|  - Parses event window and anomaly metric                   |
|  - Decomposes problem into 4 targeted sub-hypotheses        |
+-------------------------------------------------------------+
                              |
        +---------------------+---------------------+
        |                     |                     |
        v                     v                     v
+---------------+     +---------------+     +---------------+     +---------------+
|  Data Agent   |     | Deploy Agent  |     |  Comms Agent  |     |Analytics Agent|
| (DB / SQL)    |     | (Git / PRs)   |     | (Slack Logs)  |     | (Funnel Logs) |
+---------------+     +---------------+     +---------------+     +---------------+
        |                     |                     |                     |
        +---------------------+---------------------+---------------------+
                              |  (Parallel returns)
                              v
+-------------------------------------------------------------+
|                         Synthesizer                         |
|  - Unifies findings into a synchronized temporal timeline   |
|  - Correlates cause -> effect (e.g., Deploy -> Errors)      |
|  - Computes composite causal confidence score               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|              Manager Decision / Stopping Check              |
|  Is confidence >= 0.85 & multi-source evidence confirmed?   |
+-------------------------------------------------------------+
        |                                             |
     [No & iter < max]                             [Yes]
        |                                             |
        v                                             v
+-----------------------------+       +-------------------------------+
| Re-dispatch with sharper    |       | Generate Investigation Report |
| hypotheses / narrow window  |       | + Concrete Actionable Fix     |
+-----------------------------+       +-------------------------------+
        |                                             |
        +-----> (Loop to Investigators)               v
                                              [Deliver Final RCA]
```

---

## 2. Agent Roster & Specialization

| Agent | Responsibility | Primary Tools & Inputs | Expected Output |
| :--- | :--- | :--- | :--- |
| **Manager / Orchestrator** | Coordinates the entire loop; decomposes goals, verifies evidence sufficiency, enforces termination condition. | LangGraph conditional edges, internal LLM reasoning | Sub-hypotheses or Final RCA Report |
| **Data Agent** | Analyzes transactional database to localize the drop by dimension (region, customer segment, device, platform). | Read-only SQL connection (SQLite/Postgres), Pandas | Quantitative breakdown & anomaly timestamp |
| **Deploy/Code Agent** | Searches code repositories for commits, PRs, and deployment events around the incident window. | Git CLI / GitHub API / Commit logs | List of suspicious changes & touched modules |
| **Comms Agent** | Scours incident channels, Slack logs, and monitoring alerts for real-time human chatter and alert spikes. | Slack API or structured incident JSON exports | Alert triggers & incident message timestamps |
| **Analytics Agent** | Analyzes funnel drop-off rates, conversion pipelines, and user telemetry. | Funnel analytics API or event log tables | Precise stage where user drop-off occurred |
| **Synthesizer** | Temporal cross-correlation and evidence scoring across all investigator outputs. | Pure reasoning / cross-correlation module | Ranked candidate causes & confidence score |

---

## 3. LangGraph Execution Workflow Specification

### 3.1 State Definition

```python
from typing import TypedDict, List, Dict, Any, Optional

class AgentFinding(TypedDict):
    source: str
    anomaly_detected: bool
    summary: str
    confidence: float
    evidence: Dict[str, Any]
    detected_timestamp: Optional[str]

class RCAState(TypedDict):
    event_query: str
    incident_window: Dict[str, str]
    iteration: int
    max_iterations: int
    active_hypotheses: List[str]
    findings: Dict[str, AgentFinding]
    correlation_results: Optional[Dict[str, Any]]
    is_sufficient: bool
    final_report: Optional[str]
    suggested_fix: Optional[str]
```

### 3.2 Stopping Condition Algorithm
```python
def check_stopping_condition(state: RCAState) -> str:
    """
    Evaluates whether the gathered evidence satisfies the sufficiency criteria
    or if maximum retry budget has been exhausted.
    """
    iteration = state.get("iteration", 1)
    max_iter = state.get("max_iterations", 3)
    correlation = state.get("correlation_results", {})
    confidence = correlation.get("confidence", 0.0)
    source_count = len(correlation.get("corroborating_sources", []))

    # Threshold: high confidence and corroborated by at least 2 distinct sources
    if (confidence >= 0.85 and source_count >= 2) or iteration >= max_iter:
        return "generate_report"
    
    return "re_dispatch"
```

---

## 4. 3-Week Implementation Plan

### Week 1: Foundations & Core Data Agent
- **Day 1–2**: Core LLM mechanics, structured JSON outputs, function calling schema design.
- **Day 3–4**: Build synthetic ground-truth dataset in SQLite (seeding a known root cause e.g., bad payment config change buried in realistic background noise).
- **Day 5–7**: Build and unit-test the **Data Agent** to reliably detect, segment, and isolate metric anomalies.

### Week 2: Multi-Agent Orchestration
- **Day 8–9**: Implement **Deploy Agent** (GitHub/Git parser) and **Comms Agent** (Slack JSON log searcher).
- **Day 10–11**: Implement **Analytics Agent** (Funnel drop-off detector).
- **Day 12–14**: Build the LangGraph Orchestrator with parallel dispatch, state merging, and the evaluate/retry loop.

### Week 3: Synthesis, UI & Viva Preparation
- **Day 15–16**: Build **Synthesizer** to cross-correlate events across the timeline and rank root-cause candidates.
- **Day 17–18**: Wire up final report generator and a minimal Streamlit dashboard.
- **Day 19–20**: End-to-end testing against seeded ground-truth scenarios to prove system accuracy.
- **Day 21**: Rehearse oral defense: Explain parallel dispatch, stopping logic, and architectural trade-offs.

---

## 5. Viva Defense Talking Points

1. **Why multi-agent instead of a single prompt?**
   - Eliminates tool-schema overload, keeps context narrow, and allows parallel retrieval across orthogonal data sources.
2. **How is accuracy validated?**
   - Through a synthetic ground-truth dataset where the true root cause is pre-seeded and known, allowing objective precision/recall measurement.
3. **What is the hardest engineering challenge?**
   - The stopping decision: knowing when an evidence chain is mathematically and causally sufficient to terminate rather than re-querying indefinitely.
4. **Why is this not simply RAG?**
   - RAG retrieves similar text. This system autonomously investigates, formulates hypotheses, executes code/SQL, cross-correlates temporal events, and identifies causation.

