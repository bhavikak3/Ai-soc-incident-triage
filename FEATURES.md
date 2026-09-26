# Feature Descriptions for Dissertation

## 1. Dashboard Feature

**Description**: The Dashboard serves as the central landing page providing at-a-glance security posture information.

**Functionality**:
- Displays total count of all submitted alerts
- Shows alert distribution across four severity levels: Critical, High, Medium, and Low
- Shows incident status breakdown: Open, Investigating, and Closed
- Lists the five most recent alerts with severity badges

**Technical Implementation**:
- `database.get_dashboard_stats()` - SQL aggregation query
- Streamlit metric cards with custom CSS styling
- Auto-refresh on tab navigation

**Dissertation Relevance**: Demonstrates real-time alert monitoring capability essential for SOC environments.

---

## 2. Alert Submission Feature

**Description**: Enables SOC analysts to submit security alerts for AI-powered analysis.

**Functionality**:
- Text area input for alert description (max 1000 characters)
- "Analyze Alert" button triggers AI processing
- Pre-loaded example alerts for demonstration
- Example button click populates text area via session state

**User Flow**:
1. Analyst enters alert description
2. Clicks "Analyze Alert"
3. System processes via LLM
4. Results displayed with structured analysis
5. Alert automatically saved to database

**Dissertation Relevance**: Simulates real-world alert ingestion process from SIEM or detection tools.

---

## 3. AI Incident Analysis Engine

**Description**: Core feature that leverages Large Language Models to provide structured incident analysis.

**Analysis Output**:
- **Alert Summary**: Concise description of the detected activity
- **Severity Classification**: One of Critical/High/Medium/Low
- **Confidence Score**: 0-100 percentage indicating analysis certainty
- **MITRE ATT&CK Mapping**:
  - Technique ID and name (e.g., T1059.001 PowerShell)
  - Tactical category (e.g., Execution)
- **Reasoning**: Plain-language explanation of the analysis
- **Recommended Actions**: Four prioritized next steps for the analyst
- **Escalation Recommendation**: Yes/No indicating if senior analyst involvement is needed

**AI System Prompt**:
```
You are an AI Incident Triage Assistant designed for Junior Tier-1 SOC Analysts.
Analyse security alerts and provide structured guidance suitable for junior analysts.
```

**Dissertation Relevance**: This is the primary innovation - demonstrating how LLMs can augment Tier-1 analyst decision-making.

---

## 4. Alert Tracking Module

**Description**: Persistent storage system for all analyzed alerts.

**Database Schema**:
| Field | Type | Description |
|-------|------|-------------|
| alert_id | INTEGER | Auto-incrementing primary key |
| description | TEXT | Original alert description |
| date | TEXT | Timestamp of analysis |
| severity | TEXT | Classification result |
| confidence_score | INTEGER | AI confidence percentage |
| mitre_technique | TEXT | MITRE ATT&CK technique |
| mitre_tactic | TEXT | MITRE ATT&CK tactic |
| reasoning | TEXT | Analysis explanation |
| recommended_actions | TEXT | JSON array of actions |
| escalation_required | TEXT | Yes/No flag |
| status | TEXT | Open/Investigating/Closed |

**Dissertation Relevance**: Demonstrates data persistence patterns suitable for audit trails and compliance.

---

## 5. Alert History Feature

**Description**: Searchable and filterable repository of all analyzed alerts.

**Functionality**:
- **Search**: Full-text search across alert descriptions
- **Severity Filter**: Dropdown to filter by Critical/High/Medium/Low
- **Status Filter**: Dropdown to filter by Open/Investigating/Closed
- **Export**: Download filtered results as CSV file
- **Alert Cards**: Visual display with severity badges and status icons

**Technical Implementation**:
- Parameterized SQL queries to prevent injection
- Real-time filtering without page reload
- Streamlit column layout for responsive design

**Dissertation Relevance**: Shows how alert data can be organized for case management and historical analysis.

---

## 6. Mock Analysis Mode

**Description**: Fallback analysis engine for environments without API access.

**Functionality**:
- Keyword-based severity determination
- Pattern matching for MITRE technique mapping
- Randomized confidence scores within appropriate ranges
- Full structured output compatibility

**Use Cases**:
- Demonstration without API key
- Offline development/testing
- Initial project evaluation

**Dissertation Relevance**: Ensures the system is self-contained and demonstrable regardless of API availability.

---

## Feature Comparison Table

| Feature | Complexity | Dissertation Value | Implementation Status |
|---------|------------|-------------------|---------------------|
| Dashboard | Low | Shows real-time monitoring | Complete |
| Alert Submission | Low | User input handling | Complete |
| AI Analysis Engine | High | Core innovation | Complete |
| Alert Tracking | Medium | Data persistence | Complete |
| Alert History | Medium | Search & filtering | Complete |
| Mock Mode | Low | Accessibility | Complete |

---

## Security Considerations Addressed

1. **SQL Injection Prevention**: All database queries use parameterized statements
2. **Input Validation**: Character limits enforced on text inputs
3. **API Key Security**: Credentials stored in environment variables
4. **No Sensitive Data Exposure**: No PII stored in the system

---

## Limitations (for Future Work)

1. **No Multi-user Support**: Single-user authentication only
2. **No Real-time Updates**: Manual page refresh required
3. **Limited MITRE Coverage**: Mock mode uses subset of techniques
4. **No Integration**: No SIEM or EDR connectors (by design)
5. **Local Storage Only**: Not suitable for distributed teams

---

## Potential Enhancements (Future Research)

1. Integration with enterprise SIEM platforms (Splunk, QRadar)
2. User authentication and role-based access control
3. Real-time WebSocket updates for dashboard
4. Expanded MITRE ATT&CK technique database
5. Integration with threat intelligence feeds
6. Automated ticket creation in ServiceNow/Jira
7. Machine learning model for anomaly detection