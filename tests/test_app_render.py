"""
Render tests for app.py, using the Streamlit stub in this directory.

These exercise the real render functions headlessly and assert on what was
emitted, which catches the class of bug that a syntax check cannot: literal
f-string placeholders, unbalanced HTML, unescaped user input, and click
handlers that never reach the database.

Uses a throwaway database; never touches incident_triage.db.

Run with:  python tests/test_app_render.py
"""

import os
import re
import sys
import tempfile

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as stub  # the local stub, not the real package  # noqa: E402
import database  # noqa: E402
import llm  # noqa: E402

# Pin to the mock analyser: these render tests assert that specific text such as
# "T1059.001" appears on the page, which a live model would not guarantee.
os.environ["GEMINI_API_KEY"] = ""

TMP = tempfile.mkdtemp(prefix="triage_render_")
DB = os.path.join(TMP, "render.db")
database.DB_PATH = DB
database.init_db()

import app  # noqa: E402

app.database.DB_PATH = DB

ANALYZE = "🔍 Analyze Alert"


def audit(tag):
    """Assertions that should hold after any render pass."""
    joined = "\n".join(stub.MARKDOWN)

    leaks = re.findall(
        r"\{analysis\[[^\]]*\]\}|\{alert\[[^\]]*\]\}|\{stats\[[^\]]*\]\}", joined
    )
    assert not leaks, f"[{tag}] literal placeholder leaked into output: {set(leaks)}"

    for block in stub.HTML:
        if "<div" in block:
            opened, closed = block.count("<div"), block.count("</div>")
            assert opened == closed, (
                f"[{tag}] unbalanced divs ({opened} open / {closed} close): {block[:100]!r}"
            )
        if "<span" in block:
            assert block.count("<span") == block.count("</span>"), (
                f"[{tag}] unbalanced span in: {block[:100]!r}"
            )

    mismatched = re.findall(r'class="(?:severity|status)-(?:[A-Z]\w*)"', joined)
    assert not mismatched, f"[{tag}] CSS class case mismatch: {set(mismatched)}"

    return joined


def test_empty_database():
    print("=== empty database ===")
    stub.reset()
    app.main()
    out = audit("empty")
    assert "AI Incident Triage System" in out, "header did not render"
    assert "No alerts submitted yet" in out, "empty-state message missing"
    assert any(m == "tabs" for m, _ in stub.CALLS), "tabs never created"
    assert "Mock mode" in out or "Gemini" in out, "backend banner missing"
    print(f"  {len(stub.CALLS)} render calls; header, empty state, tabs, banner OK")


def test_submit_flow():
    print("\n=== submit an alert ===")
    stub.reset()
    stub.session_state.clear()
    stub.session_state["alert_input"] = (
        "Suspicious PowerShell executed an encoded command and downloaded a file"
    )
    stub.CLICK.add(ANALYZE)
    app.main()
    out = audit("submit")

    alert_id = stub.session_state.get("last_alert_id")
    assert alert_id, "alert id not stored in session state"
    row = database.get_alert_by_id(alert_id)
    assert row, "alert was not written to the database"
    assert "Analysis complete" in out
    assert row["reasoning"] and row["reasoning"] in out, "reasoning text not rendered"
    assert "T1059.001" in out, "MITRE technique not rendered"
    assert "Escalation" in out
    assert any(m == "progress" for m, _ in stub.CALLS), "confidence bar missing"
    print(
        f"  saved #{alert_id}: {row['severity']} {row['confidence_score']}% "
        f"{row['mitre_technique']}"
    )
    print("  reasoning, severity, confidence, MITRE and escalation all rendered OK")


def test_blank_submit_saves_nothing():
    print("\n=== blank submit ===")
    before = database.get_dashboard_stats()["total_alerts"]
    stub.reset()
    stub.session_state.clear()
    stub.session_state["alert_input"] = "   "
    stub.CLICK.add(ANALYZE)
    app.main()
    audit("blank")
    after = database.get_dashboard_stats()["total_alerts"]
    assert after == before, "a blank alert was saved"
    assert any("Please enter an alert description" in m for m in stub.MARKDOWN)
    print(f"  rejected with a warning, row count unchanged ({before}) OK")


def test_example_button_not_sticky():
    print("\n=== example buttons ===")
    stub.reset()
    stub.session_state.clear()
    stub.CLICK.add("example_1")
    app.main()
    audit("example")
    loaded = stub.session_state.get("alert_input", "")
    assert "failed login" in loaded.lower(), f"example not loaded: {loaded!r}"
    print(f"  loaded: {loaded[:55]}")

    stub.session_state["alert_input"] = "user typed over it"
    stub.reset()
    app.main()
    assert stub.session_state["alert_input"] == "user typed over it", (
        "text area is stuck on the example"
    )
    print("  a user edit survives the next rerun OK")


def test_dashboard_with_data():
    print("\n=== dashboard with data ===")
    stub.reset()
    stub.session_state.clear()
    for text in (
        "Ransomware encrypted the finance share",
        "Multiple failed login attempts",
        "Unauthorized registry modification",
    ):
        database.save_alert(text, llm.analyze_alert(text))
    app.main()
    out = audit("dashboard")
    stats = database.get_dashboard_stats()
    charts = [c for m, c in stub.CALLS if m == "bar_chart"]
    assert len(charts) == 2, f"expected 2 charts, got {len(charts)}"
    assert "No alerts submitted yet" not in out
    assert str(stats["total_alerts"]) in out
    assert "#dc2626" in out, "critical severity colour not applied"
    print(
        f"  total={stats['total_alerts']} critical={stats['critical']} "
        f"high={stats['high']} open={stats['open_incidents']}; 2 charts; colours OK"
    )


def test_status_update_writes():
    print("\n=== status update reaches the database ===")
    target = database.get_filtered_alerts()[0]["alert_id"]
    original = database.get_alert_by_id(target)["status"]
    stub.reset()
    stub.session_state.clear()
    stub.session_state[f"status_select_{target}"] = "Closed"
    stub.CLICK.add(f"status_save_{target}")
    try:
        app.main()
    except stub._Rerun:
        pass  # st.rerun() after a successful save is expected
    assert database.get_alert_by_id(target)["status"] == "Closed", "status not updated"
    assert stub.RERUN, "st.rerun() was not called after saving"
    print(f"  alert #{target}: {original} -> Closed, rerun triggered OK")


def test_export_and_details():
    print("\n=== export button and detail tables ===")
    stub.reset()
    stub.session_state.clear()
    app.main()
    audit("history")
    downloads = [c for m, c in stub.CALLS if m == "download_button"]
    assert downloads, "no download button rendered"
    assert any(m == "dataframe" for m, _ in stub.CALLS), "detail tables missing"
    print(f"  single-click export ({downloads[0]}) and detail tables OK")


def test_html_is_escaped():
    print("\n=== injected markup never reaches an HTML block ===")
    stub.reset()
    stub.session_state.clear()
    payload = (
        "<script>alert('xss')</script> <img src=x onerror=alert(1)> "
        "<iframe src=evil> suspicious powershell"
    )
    database.save_alert(payload, llm.analyze_alert(payload))
    app.main()
    audit("xss")
    html = "\n".join(stub.HTML)
    for tag in ("<script", "</script>", "<img", "<iframe"):
        assert tag not in html, f"raw {tag!r} reached an unsafe_allow_html block"
    assert "&lt;script&gt;" in html and "&lt;img" in html, "escaping not applied"
    print("  all raw tags neutralised to &lt;...&gt; OK")
    print("  (st.write and expander labels get the raw string; Streamlit escapes those)")


if __name__ == "__main__":
    test_empty_database()
    test_submit_flow()
    test_blank_submit_saves_nothing()
    test_example_button_not_sticky()
    test_dashboard_with_data()
    test_status_update_writes()
    test_export_and_details()
    test_html_is_escaped()
    print(f"\nALL APP RENDER TESTS PASSED (scratch db in {TMP})")
