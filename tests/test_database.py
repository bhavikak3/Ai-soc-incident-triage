"""
Tests for database.py - schema, migration and CRUD.

Uses a throwaway database in a temp directory; never touches incident_triage.db.

Run with:  python tests/test_database.py
"""

import json
import os
import sqlite3
import sys
import tempfile

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database  # noqa: E402
import llm  # noqa: E402

# Pin to the mock analyser so a populated .env cannot turn these into live API
# calls; the expected severity counts below depend on deterministic verdicts.
os.environ["GEMINI_API_KEY"] = ""

TMP = tempfile.mkdtemp(prefix="triage_tests_")

OLD_SCHEMA = """
CREATE TABLE alerts (
    alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
    description TEXT NOT NULL,
    date TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence_score INTEGER,
    mitre_technique TEXT,
    mitre_tactic TEXT,
    reasoning TEXT,
    recommended_actions TEXT,
    escalation_required TEXT,
    status TEXT DEFAULT 'Open'
)
"""


def test_migration_from_old_schema():
    """A database created before alert_summary/analysis_mode existed must upgrade."""
    print("=== migration from the pre-existing schema ===")
    path = os.path.join(TMP, "old.db")
    conn = sqlite3.connect(path)
    conn.execute(OLD_SCHEMA)
    conn.execute(
        "INSERT INTO alerts (description,date,severity,confidence_score,"
        "mitre_technique,mitre_tactic,reasoning,recommended_actions,"
        "escalation_required,status) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            "legacy row",
            "2026-08-25 10:00:00",
            "High",
            80,
            "T1059.001 PowerShell",
            "Execution",
            "legacy reasoning",
            json.dumps(["old action"]),
            "Yes",
            "Investigating",
        ),
    )
    conn.commit()
    conn.close()

    before = _columns(path)
    print("  before:", before)
    assert "alert_summary" not in before

    database.DB_PATH = path
    database.init_db()

    after = _columns(path)
    print("  after: ", after)
    assert "alert_summary" in after and "analysis_mode" in after

    row = database.get_alert_by_id(1)
    assert row["description"] == "legacy row", "legacy data lost"
    assert row["recommended_actions"] == ["old action"], "actions did not decode"
    assert row["status"] == "Investigating"
    print("  legacy row preserved and actions decoded OK")

    database.init_db()
    database.init_db()
    print("  init_db() is idempotent OK")


def _columns(path):
    conn = sqlite3.connect(path)
    cols = [r[1] for r in conn.execute("PRAGMA table_info(alerts)")]
    conn.close()
    return cols


def _fresh_db():
    path = os.path.join(TMP, "fresh.db")
    if os.path.exists(path):
        os.remove(path)
    database.DB_PATH = path
    database.init_db()
    return path


def test_empty_state():
    print("\n=== empty database ===")
    _fresh_db()
    stats = database.get_dashboard_stats()
    assert stats["total_alerts"] == 0
    assert database.get_recent_alerts(5) == []
    assert database.get_filtered_alerts() == []
    assert database.get_all_alerts_for_export().empty
    print("  all accessors return clean empty values OK")


def test_round_trip():
    print("\n=== save and read back ===")
    _fresh_db()
    ids = []
    for text in (
        "Ransomware encrypted files on finance share",
        "Multiple failed login attempts from unusual IP",
        "Routine definition update completed",
        "Suspicious PowerShell with encoded command",
    ):
        analysis = llm.analyze_alert(text)
        alert_id = database.save_alert(text, analysis)
        ids.append(alert_id)
        back = database.get_alert_by_id(alert_id)
        assert back["severity"] == analysis["severity"]
        assert back["alert_summary"] == analysis["alert_summary"], "summary not persisted"
        assert back["analysis_mode"] == analysis["mode"], "mode not persisted"
        assert back["recommended_actions"] == analysis["recommended_actions"]
        print(
            f"  #{alert_id} {analysis['severity']:8} summary_stored=True "
            f"mode={back['analysis_mode']} actions={len(back['recommended_actions'])}"
        )

    stats = database.get_dashboard_stats()
    assert stats["total_alerts"] == 4
    total = stats["critical"] + stats["high"] + stats["medium"] + stats["low"]
    assert total == 4, "severity buckets do not sum to the total"
    print(f"  severity buckets sum to {total} OK")
    return ids


def test_status_updates(ids):
    print("\n=== status updates (previously unreachable from the UI) ===")
    assert database.update_alert_status(ids[0], "Investigating") is True
    assert database.get_alert_by_id(ids[0])["status"] == "Investigating"
    assert database.update_alert_status(ids[1], "Closed") is True
    print(f"  #{ids[0]} -> Investigating, #{ids[1]} -> Closed OK")

    assert database.update_alert_status(999999, "Closed") is False
    print("  unknown id returns False OK")

    try:
        database.update_alert_status(ids[0], "Bogus")
        raise AssertionError("invalid status was accepted")
    except ValueError:
        print("  invalid status rejected OK")

    stats = database.get_dashboard_stats()
    counts = (
        stats["open_incidents"],
        stats["investigating_incidents"],
        stats["closed_incidents"],
    )
    assert counts == (2, 1, 1), counts
    print(f"  open/investigating/closed = {counts} OK")


def test_filters():
    print("\n=== filters ===")
    assert len(database.get_filtered_alerts(status_filter="Closed")) == 1
    assert len(database.get_filtered_alerts(status_filter="Open")) == 2
    assert len(database.get_filtered_alerts(search_query="PowerShell")) == 1
    assert len(database.get_filtered_alerts(search_query="zzznomatch")) == 0
    print("  status, search and severity filters OK")


def test_sql_injection():
    print("\n=== injection attempt through the search box ===")
    assert database.get_filtered_alerts(search_query="'; DROP TABLE alerts; --") == []
    assert database.get_dashboard_stats()["total_alerts"] == 4, "table was dropped"
    print("  parameterised query held, table intact OK")


def test_export():
    print("\n=== CSV export ===")
    df = database.get_all_alerts_for_export()
    assert "alert_summary" in df.columns and "analysis_mode" in df.columns
    csv = df.to_csv(index=False)
    assert "Ransomware" in csv
    print(f"  shape={df.shape}, {len(csv.encode())} bytes, new columns present OK")


def test_delete(ids):
    print("\n=== delete ===")
    assert database.delete_alert(ids[2]) is True
    assert database.get_alert_by_id(ids[2]) is None
    assert database.delete_alert(ids[2]) is False
    print("  delete works and is idempotent OK")


if __name__ == "__main__":
    test_migration_from_old_schema()
    test_empty_state()
    ids = test_round_trip()
    test_status_updates(ids)
    test_filters()
    test_sql_injection()
    test_export()
    test_delete(ids)
    print(f"\nALL DATABASE TESTS PASSED (scratch dbs in {TMP})")
