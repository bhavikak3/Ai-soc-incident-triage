# AI-Assisted Incident Triage System for Junior SOC Analysts

An AI-driven decision support system developed as an MSc Cyber Security and Forensic Information Technology dissertation project at the University of Portsmouth[cite: 3]. Designed to assist junior Tier-1 SOC analysts by automating alert severity classification, mapping threats to the MITRE ATT&CK framework, and providing structured mitigation guidance.

## Key Features
- **Structured 7-Field Triage:** Summary, severity, confidence score, MITRE mapping, reasoning, recommended actions, and escalation guidance.
- **Resilient Dual-Mode Architecture:** Integrates the Google Gemini API for live LLM intelligence with an automatic fallback to a deterministic rule-based mock engine for offline operation.
- **Persistent Audit Logging:** Built with SQLite to maintain a complete historical audit trail and support CSV exports for shift handovers.

## System Architecture & Design
For detailed technical documentation, please refer to our [System Architecture Documentation](ARCHITECTURE.md).

## Tech Stack
- **Language:** Python
- **Frontend/UI:** Streamlit
- **AI/LLM:** Google Gemini API (`gemini-2.0-flash` / `3.6-flash`)
- **Database:** SQLite

## Installation & Local Setup
1. Clone the repository:
   ```bash
   git clone [https://github.com/bhavikakothari-cloud/Ai-soc-incident-triage.git](https://github.com/bhavikakothari-cloud/Ai-soc-incident-triage.git)
   cd Ai-soc-incident-triage
