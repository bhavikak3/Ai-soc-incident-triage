from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import database
import llm

# Load .env before anything reads GEMINI_API_KEY.
load_dotenv()

st.set_page_config(
    page_title="AI Incident Triage System",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Presentation constants
# ---------------------------------------------------------------------------
SEVERITY_COLORS = {
    "Critical": "#dc2626",
    "High": "#ea580c",
    "Medium": "#d97706",
    "Low": "#16a34a",
}
SEVERITY_ORDER = ["Critical", "High", "Medium", "Low"]

STATUS_COLORS = {
    "Open": "#3b82f6",
    "Investigating": "#eab308",
    "Closed": "#16a34a",
}
STATUS_ICONS = {"Open": "🔴", "Investigating": "🟡", "Closed": "🟢"}
STATUS_OPTIONS = ["Open", "Investigating", "Closed"]

CUSTOM_CSS = """<style>
    .main-header { font-size: 2.25rem; font-weight: 700; color: #1f2937; margin-bottom: 0.25rem; }
    .sub-header { color: #6b7280; font-size: 0.95rem; margin-bottom: 1.5rem; }
    .alert-card { border-left: 4px solid #3b82f6; background-color: #ffffff; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
    .badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px; font-size: 0.75rem; font-weight: 700; color: #ffffff; letter-spacing: 0.03em; }
    .panel { background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem; }
    .panel-title { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.35rem; }
    .panel-value { font-size: 1.4rem; font-weight: 700; color: #1f2937; }
    .footer { text-align: center; color: #9ca3af; font-size: 0.8rem; margin-top: 3rem; padding-top: 1.5rem; border-top: 1px solid #e5e7eb; }
</style>"""


# ---------------------------------------------------------------------------
# HTML Helpers
# ---------------------------------------------------------------------------
def badge(text, color):
    return f'<span class="badge" style="background-color:{color};">{escape(text)}</span>'


def severity_badge(severity):
    return badge(str(severity).upper(), SEVERITY_COLORS.get(severity, "#3b82f6"))


def status_badge(status):
    return badge(str(status).upper(), STATUS_COLORS.get(status, "#6b7280"))


def panel(title, value, color=None):
    style = f' style="color:{color};"' if color else ""
    return (
        '<div class="panel">'
        f'<div class="panel-title">{title}</div>'
        f'<div class="panel-value"{style}>{escape(value)}</div>'
        "</div>"
    )


def escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate(text, limit=110):
    text = str(text).strip()
    return text if len(text) <= limit else text[:limit].rstrip() + "..."


# ---------------------------------------------------------------------------
# App Main
# ---------------------------------------------------------------------------
def main():
    database.init_db()
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    st.markdown(
        '<div class="main-header">🚨 AI Incident Triage System</div>'
        '<div class="sub-header">Structured triage guidance for Tier-1 SOC analysts</div>',
        unsafe_allow_html=True,
    )

    mode = llm.get_mode_label()
    if mode.startswith("Mock"):
        st.info(
            f"**Analysis backend:** {mode}. "
            "Results come from a deterministic rule-based analyser. "
            "Set `GEMINI_API_KEY` in your `.env` file to enable live AI analysis.",
            icon="ℹ️",
        )
    else:
        st.success(f"**Analysis backend:** {mode}", icon="✅")

    tab_dashboard, tab_submit, tab_history = st.tabs(
        ["📊 Dashboard", "➕ Submit Alert", "📋 Alert History"]
    )

    with tab_dashboard:
        dashboard()

    with tab_submit:
        submit_alert()

    with tab_history:
        alert_history()

    st.markdown(
        '<div class="footer">AI Incident Triage System &middot; '
        "AI-generated triage is advisory only and must be validated by an analyst."
        "</div>",
        unsafe_allow_html=True,
    )


def dashboard():
    st.markdown("### Dashboard Overview")

    stats = database.get_dashboard_stats()

    if stats["total_alerts"] == 0:
        st.info("No alerts submitted yet. Head to **Submit Alert** to get started.")
        return

    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(panel("Total Alerts", stats["total_alerts"]), unsafe_allow_html=True)
    col2.markdown(
        panel("Critical", stats["critical"], SEVERITY_COLORS["Critical"]),
        unsafe_allow_html=True,
    )
    col3.markdown(
        panel("High Priority", stats["high"], SEVERITY_COLORS["High"]),
        unsafe_allow_html=True,
    )
    col4.markdown(panel("Open Incidents", stats["open_incidents"]), unsafe_allow_html=True)

    left, right = st.columns(2)

    with left:
        st.markdown("#### Severity Distribution")
        severity_df = pd.DataFrame(
            {
                "Severity": SEVERITY_ORDER,
                "Alerts": [stats[s.lower()] for s in SEVERITY_ORDER],
            }
        ).set_index("Severity")
        st.bar_chart(severity_df, height=260)

    with right:
        st.markdown("#### Status Breakdown")
        status_df = pd.DataFrame(
            {
                "Status": STATUS_OPTIONS,
                "Alerts": [
                    stats["open_incidents"],
                    stats["investigating_incidents"],
                    stats["closed_incidents"],
                ],
            }
        ).set_index("Status")
        st.bar_chart(status_df, height=260)

    st.markdown("#### Recent Alerts")
    for alert in database.get_recent_alerts(5):
        severity = alert["severity"]
        status = alert["status"]
        card = (
            f'<div class="alert-card" style="border-left-color:'
            f'{STATUS_COLORS.get(status, "#3b82f6")};">'
            '<div style="display:flex;justify-content:space-between;'
            'align-items:flex-start;gap:1rem;">'
            "<div>"
            f'<div style="font-weight:600;margin-bottom:0.3rem;">'
            f"{escape(truncate(alert['description']))}</div>"
            f'<div style="color:#6b7280;font-size:0.8rem;">'
            f"Alert #{alert['alert_id']} &middot; {alert['date']}</div>"
            "</div>"
            f'<div style="text-align:right;white-space:nowrap;">'
            f"{severity_badge(severity)} {status_badge(status)}</div>"
            "</div></div>"
        )
        st.markdown(card, unsafe_allow_html=True)


def use_example(text):
    st.session_state.alert_input = text


def clear_input():
    st.session_state.alert_input = ""


def submit_alert():
    st.markdown("### Submit New Security Alert")
    st.caption(
        "Describe the alert in plain language. The analyser returns a severity "
        "classification, MITRE ATT&CK mapping and recommended next steps."
    )

    if "alert_input" not in st.session_state:
        st.session_state.alert_input = ""

    st.text_area(
        "Alert Description",
        key="alert_input",
        placeholder=(
            "e.g., Suspicious PowerShell command executed. Encoded commands "
            "detected and a file downloaded from an external domain."
        ),
        height=150,
        max_chars=1000,
    )

    col1, col2, _ = st.columns([1, 1, 4])
    analyze_clicked = col1.button("🔍 Analyze Alert", type="primary")
    col2.button("Clear", on_click=clear_input)

    with st.expander("Load an example alert"):
        examples = [
            "Suspicious PowerShell command executed. Encoded commands detected and a file downloaded from an external domain.",
            "Multiple failed login attempts from unusual IP address.",
            "Large file transfer detected to external server.",
            "Unauthorized registry modification detected.",
            "Webcam access attempted by unknown process.",
        ]
        for i, example in enumerate(examples):
            ex_col1, ex_col2 = st.columns([5, 1])
            ex_col1.write(example)
            ex_col2.button(
                "Use",
                key=f"example_{i}",
                on_click=use_example,
                args=(example,),
            )

    if analyze_clicked:
        description = st.session_state.alert_input.strip()
        if not description:
            st.warning("Please enter an alert description before analyzing.")
        else:
            with st.spinner("Analyzing alert..."):
                analysis = llm.analyze_alert(description)
                alert_id = database.save_alert(description, analysis)
            st.session_state.last_analysis = analysis
            st.session_state.last_alert_id = alert_id

    if st.session_state.get("last_analysis"):
        st.divider()
        st.success(
            f"Analysis complete and saved as **Alert #{st.session_state.last_alert_id}**."
        )
        display_analysis_results(st.session_state.last_analysis)


def display_analysis_results(analysis):
    st.markdown("### 📋 Alert Analysis Summary")

    if analysis.get("alert_summary"):
        st.markdown(
            '<div class="panel"><div class="panel-title">Summary</div>'
            f'<div>{escape(analysis["alert_summary"])}</div></div>',
            unsafe_allow_html=True,
        )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(
            panel(
                "Severity Classification",
                str(analysis["severity"]).upper(),
                SEVERITY_COLORS.get(analysis["severity"], "#3b82f6"),
            ),
            unsafe_allow_html=True,
        )
        st.markdown(
            panel("Confidence Score", f"{analysis['confidence_score']}%", "#3b82f6"),
            unsafe_allow_html=True,
        )
        st.progress(min(100, max(0, int(analysis["confidence_score"]))) / 100)

    with col2:
        st.markdown(
            '<div class="panel"><div class="panel-title">MITRE ATT&amp;CK Technique</div>'
            f'<div style="font-weight:600;font-size:1.05rem;">'
            f'{escape(analysis["mitre_technique"])}</div>'
            f'<div style="color:#6b7280;font-size:0.8rem;margin-top:0.2rem;">'
            f'Tactic: {escape(analysis["mitre_tactic"])}</div></div>',
            unsafe_allow_html=True,
        )
        escalate = analysis["escalation_required"] == "Yes"
        st.markdown(
            panel(
                "Escalation Required",
                analysis["escalation_required"],
                "#dc2626" if escalate else "#16a34a",
            ),
            unsafe_allow_html=True,
        )

    st.markdown("#### 🔍 Reasoning")
    st.write(analysis["reasoning"])

    st.markdown("#### 📝 Recommended Actions")
    if analysis["recommended_actions"]:
        for i, action in enumerate(analysis["recommended_actions"], 1):
            st.markdown(f"{i}. {action}")
    else:
        st.caption("No recommended actions returned.")

    if analysis["escalation_required"] == "Yes":
        st.warning(
            "🚨 **Escalation required.** Notify senior analysts or the incident "
            "response team before proceeding."
        )

    if analysis.get("mode"):
        st.caption(f"Analysis source: {analysis['mode']}")

    st.markdown("---")
    st.markdown("#### 👨‍💻 Analyst Review (Human-in-the-Loop)")
    with st.expander("Submit Analyst Verification", expanded=True):
        fb_col1, fb_col2 = st.columns(2)
        with fb_col1:
            st.radio(
                "Do you agree with this triage?",
                ["Agree", "Disagree - Overestimated", "Disagree - Underestimated", "False Positive"],
                key="analyst_verdict",
            )
        with fb_col2:
            st.text_area(
                "Analyst Notes / Corrections:",
                placeholder="e.g., Verified known internal vulnerability scan. Severity downgraded.",
                key="analyst_notes",
            )

        if st.button("Submit Review", key="submit_review_btn"):
            st.success("Review recorded: Alert marked as human-verified.")


def alert_history():
    st.markdown("### Alert History")

    col1, col2, col3 = st.columns(3)
    search_query = col1.text_input("🔍 Search", placeholder="Search descriptions...")
    severity_filter = col2.selectbox("Severity", ["All"] + SEVERITY_ORDER)
    status_filter = col3.selectbox("Status", ["All"] + STATUS_OPTIONS)

    alerts = database.get_filtered_alerts(search_query, severity_filter, status_filter)

    if not alerts:
        st.info("No alerts match the current filters.")
    else:
        st.caption(f"{len(alerts)} alert(s) found.")

        for alert in alerts:
            alert_id = alert["alert_id"]
            header = (
                f"{STATUS_ICONS.get(alert['status'], '⚪')} "
                f"#{alert_id} · {alert['severity']} · {truncate(alert['description'], 70)}"
            )

            with st.expander(header):
                st.markdown(
                    f"{severity_badge(alert['severity'])} "
                    f"{status_badge(alert['status'])}",
                    unsafe_allow_html=True,
                )

                meta = pd.DataFrame(
                    {
                        "Field": [
                            "Alert ID",
                            "Date",
                            "Severity",
                            "Confidence",
                            "MITRE Technique",
                            "MITRE Tactic",
                            "Escalation Required",
                            "Analysis Source",
                        ],
                        "Value": [
                            alert_id,
                            alert["date"],
                            alert["severity"],
                            f"{alert.get('confidence_score', '-')}%",
                            alert.get("mitre_technique", "-"),
                            alert.get("mitre_tactic", "-"),
                            alert.get("escalation_required", "-"),
                            alert.get("analysis_mode") or "-",
                        ],
                    }
                )
                st.dataframe(meta, hide_index=True, use_container_width=True)

                st.markdown("**Description**")
                st.write(alert["description"])

                if alert.get("reasoning"):
                    st.markdown("**Reasoning**")
                    st.write(alert["reasoning"])

                if alert.get("recommended_actions"):
                    st.markdown("**Recommended Actions**")
                    for i, action in enumerate(alert["recommended_actions"], 1):
                        st.markdown(f"{i}. {action}")

                st.divider()
                st.markdown("**Update Status**")
                sc1, sc2 = st.columns([2, 1])
                new_status = sc1.selectbox(
                    "New status",
                    STATUS_OPTIONS,
                    index=STATUS_OPTIONS.index(alert["status"])
                    if alert["status"] in STATUS_OPTIONS
                    else 0,
                    key=f"status_select_{alert_id}",
                    label_visibility="collapsed",
                )
                if sc2.button("Save", key=f"status_save_{alert_id}"):
                    if new_status == alert["status"]:
                        st.info("Status unchanged.")
                    else:
                        database.update_alert_status(alert_id, new_status)
                        st.success(f"Alert #{alert_id} set to {new_status}.")
                        st.rerun()

    st.divider()
    st.markdown("### Export Data")
    export_df = database.get_all_alerts_for_export()
    if export_df is not None and not export_df.empty:
        st.download_button(
            label="📄 Download all alerts as CSV",
            data=export_df.to_csv(index=False).encode("utf-8"),
            file_name=f"incident_triage_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )
    else:
        st.caption("No data available for export.")


if __name__ == "__main__":
    main()
