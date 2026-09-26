# System Architecture

## Overview
This document describes the architecture of the AI-Assisted Incident Triage System, a proof-of-concept web application designed for Junior SOC Analysts.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Dashboard   │  │Submit Alert  │  │   Alert History      │  │
│  │   (Tab 1)    │  │   (Tab 2)    │  │      (Tab 3)         │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
└─────────┼─────────────────┼─────────────────────┼──────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Application Layer                │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    app.py (Main Controller)               │   │
│  │  - Routing between tabs                                   │   │
│  │  - Session state management                               │   │
│  │  - UI rendering                                           │   │
│  └──────────────────────┬────────────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌──────────────┐ ┌────────────┐ ┌──────────────┐
   │ database.py  │ │   llm.py   │ │  Utilities   │
   │              │ │            │ │              │
   │ - SQLite     │ │ - Gemini   │ │ - Config     │
   │ - CRUD ops   │ │ - Prompt   │ │ - Helpers    │
   │ - Queries    │ │ - Parsing  │ │              │
   └──────┬───────┘ └─────┬──────┘ └──────┬───────┘
          │               │               │
          ▼               ▼               ▼
   ┌──────────────┐ ┌────────────┐ ┌──────────────┐
   │  SQLite DB   │ │  LLM API   │ │ .env config  │
   │ (incident_   │ │ (Gemini    │ │              │
   │  triage.db)  │ │  or Mock)  │ │              │
   └──────────────┘ └────────────┘ └──────────────┘
```

## Component Details

### 1. Presentation Layer (Streamlit)
- **Technology**: Streamlit 1.28+
- **Pages/Tabs**: Dashboard, Submit Alert, Alert History
- **State Management**: Streamlit session_state for example text persistence
- **Styling**: Custom CSS via `st.markdown` with `unsafe_allow_html=True`

### 2. Application Logic (app.py)
- **Main entry point** with `main()` function
- **Tab routing** using `st.tabs()`
- **Event handling** for button clicks and form submissions
- **Integration** with database and LLM modules

### 3. Data Layer (database.py)
- **Database**: SQLite (file-based, no server required)
- **Schema**:
  ```sql
  CREATE TABLE alerts (
      alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
      description TEXT NOT NULL,
      date TEXT NOT NULL,
      severity TEXT NOT NULL,
      confidence_score INTEGER,
      mitre_technique TEXT,
      mitre_tactic TEXT,
      reasoning TEXT,
      recommended_actions TEXT,  -- JSON array
      escalation_required TEXT,
      status TEXT DEFAULT 'Open'
  );
  ```
- **Operations**: 
  - `init_db()` - Create table if not exists
  - `save_alert()` - Insert new alert with analysis
  - `get_dashboard_stats()` - Aggregate statistics
  - `get_recent_alerts()` - Latest N alerts
  - `get_filtered_alerts()` - Search/filter for history page
  - `get_all_alerts_for_export()` - CSV export

### 4. AI Analysis Layer (llm.py)
- **Primary**: Google Gemini API (google-genai package)
- **Fallback**: Mock analysis engine (keyword-based)
- **Prompt Engineering**: Structured system prompt for consistent output
- **Response Parsing**: Regex-based extraction of structured fields
- **Output Format**:
  - Alert Summary
  - Severity (Critical/High/Medium/Low)
  - Confidence Score (0-100)
  - MITRE ATT&CK Technique & Tactic
  - Reasoning
  - Recommended Actions (numbered list)
  - Escalation Required (Yes/No)

## Data Flow

### Alert Submission Flow
1. User enters alert description in "Submit Alert" tab
2. User clicks "Analyze Alert" button
3. `llm.analyze_alert()` called with description
4. LLM returns structured analysis (or mock generates one)
5. `database.save_alert()` stores description + analysis
6. Results displayed to user

### Dashboard Flow
1. User navigates to Dashboard tab
2. `database.get_dashboard_stats()` queries aggregated counts
3. `database.get_recent_alerts(5)` fetches latest alerts
4. UI renders metrics and alert cards

### History Flow
1. User navigates to Alert History tab
2. User applies search/filters
3. `database.get_filtered_alerts()` executes parameterized query
4. Results rendered as filterable cards

## Security Considerations

- **No authentication** (per dissertation requirements - PoC only)
- **Local SQLite** - no network database exposure
- **API key** stored in `.env` file (not committed to version control)
- **Input validation**: Max 1000 characters on alert description
- **SQL injection prevention**: Parameterized queries only

## Deployment Architecture

```
Development:
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│   Local     │────▶│   Streamlit  │────▶│  Browser UI    │
│   Machine   │     │   Server     │     │  (localhost)   │
└─────────────┘     └──────────────┘     └────────────────┘
                            │
                     ┌──────┴──────┐
                     ▼             ▼
              ┌──────────┐   ┌──────────┐
              │ SQLite   │   │ Gemini   │
              │  File    │   │  API     │
              └──────────┘   └──────────┘
```

## Technology Stack Summary

| Layer | Technology | Version |
|-------|------------|---------|
| Frontend | Streamlit | 1.28+ |
| Backend | Python | 3.10+ |
| Database | SQLite | Built-in |
| AI/ML | Google Gemini | Latest |
| Data Processing | Pandas | 2.0+ |
| Config | python-dotenv | 1.0+ |

## Scalability Notes (for Dissertation Discussion)

This PoC is designed for **single-user, local deployment**. For production scaling:
- Replace SQLite with PostgreSQL/MySQL
- Add user authentication (OAuth, SSO)
- Implement message queue for async LLM processing
- Add caching layer (Redis) for dashboard stats
- Containerize with Docker/Kubernetes
- Add monitoring and logging
- Implement rate limiting on API calls