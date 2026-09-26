import sqlite3
import json
from datetime import datetime
import pandas as pd
import os

# Database file path.
# Anchored to this file's directory so the same database is used regardless of
# which working directory Streamlit is launched from.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "incident_triage.db")

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            date TEXT NOT NULL,
            severity TEXT NOT NULL,
            confidence_score INTEGER,
            mitre_technique TEXT,
            mitre_tactic TEXT,
            reasoning TEXT,
            recommended_actions TEXT,  -- JSON string
            escalation_required TEXT,
            status TEXT DEFAULT 'Open',
            alert_summary TEXT,
            analysis_mode TEXT
        )
    ''')

    # Lightweight migration: add columns that older databases won't have.
    # SQLite has no "ADD COLUMN IF NOT EXISTS", so check the existing schema.
    cursor.execute("PRAGMA table_info(alerts)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    for column, coltype in (("alert_summary", "TEXT"), ("analysis_mode", "TEXT")):
        if column not in existing_columns:
            cursor.execute(f"ALTER TABLE alerts ADD COLUMN {column} {coltype}")

    conn.commit()
    conn.close()

def save_alert(description, analysis):
    """Save an alert and its analysis to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Convert recommended actions to JSON string
    actions_json = json.dumps(analysis.get('recommended_actions', []))

    cursor.execute('''
        INSERT INTO alerts (
            description, date, severity, confidence_score,
            mitre_technique, mitre_tactic, reasoning,
            recommended_actions, escalation_required, status,
            alert_summary, analysis_mode
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        description,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        analysis.get('severity', 'Medium'),
        analysis.get('confidence_score', 50),
        analysis.get('mitre_technique', 'Unknown'),
        analysis.get('mitre_tactic', 'Unknown'),
        analysis.get('reasoning', 'No reasoning provided'),
        actions_json,
        analysis.get('escalation_required', 'No'),
        'Open',
        analysis.get('alert_summary', ''),
        analysis.get('mode', 'Unknown')
    ))

    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return alert_id

def get_dashboard_stats():
    """Get statistics for the dashboard"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Total alerts
    cursor.execute('SELECT COUNT(*) FROM alerts')
    total_alerts = cursor.fetchone()[0]

    # Severity breakdown
    cursor.execute('SELECT severity, COUNT(*) FROM alerts GROUP BY severity')
    severity_counts = dict(cursor.fetchall())

    # Status breakdown
    cursor.execute('SELECT status, COUNT(*) FROM alerts GROUP BY status')
    status_counts = dict(cursor.fetchall())

    conn.close()

    return {
        'total_alerts': total_alerts,
        'critical': severity_counts.get('Critical', 0),
        'high': severity_counts.get('High', 0),
        'medium': severity_counts.get('Medium', 0),
        'low': severity_counts.get('Low', 0),
        'open_incidents': status_counts.get('Open', 0),
        'investigating_incidents': status_counts.get('Investigating', 0),
        'closed_incidents': status_counts.get('Closed', 0)
    }

def get_recent_alerts(limit=5):
    """Get recent alerts for dashboard display"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT alert_id, description, date, severity, status
        FROM alerts
        ORDER BY date DESC, alert_id DESC
        LIMIT ?
    ''', (limit,))

    columns = [description[0] for description in cursor.description]
    alerts = [dict(zip(columns, row)) for row in cursor.fetchall()]

    conn.close()

    return alerts

def get_filtered_alerts(search_query="", severity_filter="All", status_filter="All"):
    """Get alerts with optional filtering"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    query = '''
        SELECT alert_id, description, date, severity, status,
               mitre_technique, mitre_tactic, confidence_score,
               reasoning, recommended_actions, escalation_required,
               alert_summary, analysis_mode
        FROM alerts
        WHERE 1=1
    '''
    params = []

    if search_query:
        query += ' AND description LIKE ?'
        params.append(f'%{search_query}%')

    if severity_filter != "All":
        query += ' AND severity = ?'
        params.append(severity_filter)

    if status_filter != "All":
        query += ' AND status = ?'
        params.append(status_filter)

    query += ' ORDER BY date DESC, alert_id DESC'

    cursor.execute(query, params)
    columns = [description[0] for description in cursor.description]
    alerts = [dict(zip(columns, row)) for row in cursor.fetchall()]

    conn.close()

    # recommended_actions is stored as a JSON string; decode it for the UI.
    for alert in alerts:
        alert['recommended_actions'] = _decode_actions(alert.get('recommended_actions'))

    return alerts


def _decode_actions(raw):
    """Decode the JSON-encoded recommended_actions column into a list."""
    if not raw:
        return []
    try:
        actions = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    return actions if isinstance(actions, list) else []

def get_all_alerts_for_export():
    """Get all alerts for CSV export"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT alert_id, description, date, severity, confidence_score,
               mitre_technique, mitre_tactic, reasoning,
               recommended_actions, escalation_required, status,
               alert_summary, analysis_mode
        FROM alerts
        ORDER BY date DESC, alert_id DESC
    ''')

    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    df = pd.DataFrame(rows, columns=columns)

    conn.close()

    return df

VALID_STATUSES = ("Open", "Investigating", "Closed")


def update_alert_status(alert_id, new_status):
    """Update the status of an alert. Returns True if a row was changed."""
    if new_status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status {new_status!r}; expected one of {VALID_STATUSES}"
        )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE alerts
        SET status = ?
        WHERE alert_id = ?
    ''', (new_status, alert_id))

    changed = cursor.rowcount
    conn.commit()
    conn.close()

    return changed > 0


def get_alert_by_id(alert_id):
    """Fetch a single alert with all fields, or None if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM alerts WHERE alert_id = ?', (alert_id,))
    row = cursor.fetchone()
    columns = [description[0] for description in cursor.description]

    conn.close()

    if row is None:
        return None

    alert = dict(zip(columns, row))
    alert['recommended_actions'] = _decode_actions(alert.get('recommended_actions'))
    return alert


def delete_alert(alert_id):
    """Delete an alert. Returns True if a row was removed."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('DELETE FROM alerts WHERE alert_id = ?', (alert_id,))
    changed = cursor.rowcount

    conn.commit()
    conn.close()

    return changed > 0