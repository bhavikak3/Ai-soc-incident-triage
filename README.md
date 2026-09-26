# AI-Assisted Incident Triage System for Junior SOC Analysts

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28%2B-FF4B4B.svg)](https://streamlit.io/)
[![Google Gemini API](https://img.shields.io/badge/Google_Gemini-gemini--3.6--flash-4285F4.svg)](https://ai.google.dev/)
[![MITRE ATT&CK](https://img.shields.io/badge/MITRE-ATT%26CK_v14-orange.svg)](https://attack.mitre.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Proof-of-Concept Master's Dissertation Project**  
> **Researcher:** Bhavika Kothari  
> **Degree:** MSc Cyber Security and Forensic Information Technology  
> **Institution:** University of Portsmouth (2026)

---

## 🎬 System Walkthrough Demo

![AI Incident Triage System Walkthrough](demo_walkthrough.gif)

*A Full HD 1080p walkthrough video is also available in this repository: [`demo_video.mp4`](demo_video.mp4).*

---

## 📌 Executive Overview

Modern Security Operations Centres (SOCs) are overwhelmed with alert volumes ranging from 10,000 to over 1,000,000 events daily, with false positive rates between 50% and 90%. Tier-1 and junior analysts face severe cognitive fatigue while manually correlating raw SIEM logs against complex frameworks like MITRE ATT&CK.

The **AI-Assisted Incident Triage System** is a lightweight, explainable decision-support artefact engineered specifically for Junior SOC Analysts. It transforms unstructured alert feeds into standardized 7-field incident reports with defensible reasoning, actionable containment playbooks, and automated MITRE ATT&CK mapping in under 2 seconds.

---

## ✨ Key Features

1. **📊 Real-Time Executive SOC Dashboard**
   - KPI metric counters for Total Alerts, Critical, High, and Open incidents.
   - Interactive severity breakdown and investigation status distribution charts.
   - 5 recent alerts feed with color-coded urgency indicators.

2. **⚡ Intelligent Alert Ingestion & Analysis**
   - Ingests raw logs or pre-loaded threat scenarios (PowerShell, Brute Force, Exfiltration, Registry Tampering, Video Capture).
   - Generates a structured 7-field triage verdict: Alert Summary, Severity, Confidence Score (0-100%), MITRE Mapping, Reasoning, Ordered Actions, and Escalation Flag.

3. **🎯 Automated MITRE ATT&CK Mapping**
   - Real-time classification of attacker techniques (e.g., `T1059.001 PowerShell`, `T1110 Brute Force`, `T1486 Data Encrypted for Impact`, `T1041 Exfiltration Over C2`).
   - Maps tactics directly to the enterprise matrix without requiring manual taxonomy lookups.

4. **📋 Containment Playbooks & Human-in-the-Loop (HITL) Escalation**
   - Contextual, step-by-step containment checklists (host isolation, memory dump capture, IOC blacklisting).
   - Defensible HITL recommendation preserving human decision authority and preventing automation drift.

5. **🔍 Searchable Lifecycle History & CSV Export**
   - Parameterized multi-filter search by severity, investigation status, or freeform text.
   - Live status workflow progression (`Open` ➔ `Investigating` ➔ `Closed`) backed by SQLite.
   - Single-click CSV export for external reporting and SIEM integration.

6. **🛡️ Dual-Mode Resilient Architecture**
   - Primary: Live cloud inference via Google Gemini API (`gemini-3.6-flash`).
   - Fallback: Offline deterministic keyword-based mock analysis engine with SHA-256 stable confidence scoring, ensuring 100% operational uptime during network or API disruptions.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│             PRESENTATION LAYER (Streamlit UI)               │
│  [ Dashboard Tab ]    [ Submit Alert Tab ]   [ History Tab ]│
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   LOGIC & AI ANALYSIS LAYER                 │
│                 llm.py (Dual-Mode Engine)                   │
│                                                             │
│       ┌───────────────────────┐   ┌─────────────────────┐   │
│       │ Google Gemini API     │   │ Deterministic Mock  │   │
│       │ (gemini-3.6-flash)    │◄─►│ Fallback Engine     │   │
│       └───────────────────────┘   └─────────────────────┘   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 DATA PERSISTENCE LAYER (SQLite)             │
│        database.py (ACID Compliant, Parameterized Queries)  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- `pip` package manager

### 2. Clone and Install
```bash
git clone https://github.com/bhavikakothari3-cloud/Ai-soc-incident-triage.git
cd Ai-soc-incident-triage
pip install -r requirements.txt
```

### 3. Configure API Key (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your Google Gemini API key in `.env`:
```bash
GEMINI_API_KEY=your_gemini_api_key_here
```
> *Note: If no API key is provided, the application runs seamlessly in **Offline Mock Mode** using deterministic keyword-based evaluation.*

### 4. Run Application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Automated Test Verification

Run all test suites locally:
```bash
python tests/test_gemini_path.py   # Gemini API integration & degradation
python tests/test_llm.py           # Analysis layer & structured extraction
python tests/test_database.py      # SQLite schema, queries & migrations
python tests/test_app_render.py    # UI layout & component verification
```

---

## 🔒 Security & Privacy Notice
- **Zero PII Storage:** No Personally Identifiable Information is collected or retained.
- **Credential Isolation:** API keys are loaded via isolated `.env` configurations excluded from version control.
- **SQL Injection Prevention:** 100% parameterized SQLite queries.
- **XSS Protection:** Automatic HTML tag neutralization across dynamic UI views.

---

## 👩‍💻 Author
**Bhavika Kothari**  
MSc Cyber Security and Forensic Information Technology  
School of Computing, University of Portsmouth