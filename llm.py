"""
LLM analysis layer for the AI Incident Triage System.

Uses Google Gemini when an API key is available, and falls back to a
deterministic keyword-based mock analyser otherwise so the app is always
usable for demonstration without credentials.
"""

import hashlib
import os
import re
import time

from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY is picked up when running locally.
load_dotenv()

# ---------------------------------------------------------------------------
# SDK detection
# ---------------------------------------------------------------------------
SDK_STYLE = None  # "genai" (current), "legacy" (deprecated), or None

try:
    from google import genai as _genai_new

    SDK_STYLE = "genai"
except ImportError:
    try:
        import google.generativeai as _genai_legacy

        SDK_STYLE = "legacy"
        print(
            "Warning: using the deprecated google-generativeai package. "
            "Install google-genai for future compatibility."
        )
    except ImportError:
        SDK_STYLE = None

# Model names configured for the active endpoint
MODEL_NEW = "gemini-3.6-flash"
MODEL_LEGACY = "gemini-3.6-flash"

SYSTEM_PROMPT = """You are an AI Incident Triage Assistant designed for Junior Tier-1 SOC Analysts.

Analyse security alerts and provide:

- Alert summary
- Severity classification
- Confidence score
- MITRE ATT&CK mapping
- Short reasoning
- Recommended next steps
- Escalation recommendation

Keep explanations concise, clear and suitable for junior analysts."""

RESPONSE_TEMPLATE = """Please provide your analysis in the following structured format:

Alert Summary: [Brief summary of the alert]

Severity: [Critical/High/Medium/Low]

Confidence Score: [0-100]

MITRE ATT&CK Mapping:
Technique: [Specific technique ID and name, e.g., T1059.001 PowerShell]
Tactic: [Tactic name, e.g., Execution]

Reasoning: [Short explanation of your analysis]

Recommended Actions:
1. [First recommended action]
2. [Second recommended action]
3. [Third recommended action]
4. [Fourth recommended action]

Escalation Required: [Yes/No]"""


def analyze_alert(alert_description):
    """
    Analyse a security alert and return a structured result dict.

    Falls back to the mock analyser if no API key is set, if no SDK is
    installed, or if the API call fails for any reason.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # Treat the placeholder from .env.example as "no key".
    if api_key in ("", "your_api_key_here", "your_gemini_api_key_here", "your gemini api key here"):
        api_key = None

    if SDK_STYLE and api_key:
        try:
            return analyze_with_gemini(alert_description, api_key)
        except Exception as exc:  # noqa: BLE001 - any failure must degrade gracefully
            print(f"Gemini API error: {exc}. Falling back to mock mode.")
            result = analyze_with_mock(alert_description)
            result["mode"] = "Mock (Gemini call failed)"
            return result

    return analyze_with_mock(alert_description)


def analyze_with_gemini(alert_description, api_key):
    """Analyse an alert using the Gemini API."""
    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Alert Description: {alert_description}\n\n"
        f"{RESPONSE_TEMPLATE}\n"
    )

    if SDK_STYLE == "genai":
        client = _genai_new.Client(api_key=api_key)
        response = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=MODEL_NEW, contents=prompt
                )
                break
            except Exception as exc:
                if attempt == 2:
                    raise exc
                time.sleep(2)
        response_text = response.text
    elif SDK_STYLE == "legacy":
        _genai_legacy.configure(api_key=api_key)
        model = _genai_legacy.GenerativeModel(MODEL_LEGACY)
        response = model.generate_content(prompt)
        response_text = response.text
    else:
        raise RuntimeError("No Gemini SDK installed")

    if not response_text or not response_text.strip():
        raise ValueError("Gemini returned an empty response")

    result = parse_gemini_response(response_text, alert_description)
    result["mode"] = "Gemini"
    return result


def parse_gemini_response(response_text, alert_description=""):
    """
    Parse a Gemini text response into the structured result dict.

    Any field the model omits keeps its default, so a partially malformed
    response still yields a usable result rather than an exception.
    """
    result = {
        "alert_summary": "",
        "severity": "Medium",
        "confidence_score": 50,
        "mitre_technique": "Unknown",
        "mitre_tactic": "Unknown",
        "reasoning": "Analysis completed",
        "recommended_actions": [],
        "escalation_required": "No",
    }

    try:
        summary_match = re.search(
            r"Alert Summary:\s*(.+?)(?:\n|$)", response_text, re.IGNORECASE
        )
        if summary_match:
            result["alert_summary"] = summary_match.group(1).strip()

        severity_match = re.search(
            r"Severity:\s*(Critical|High|Medium|Low)", response_text, re.IGNORECASE
        )
        if severity_match:
            result["severity"] = severity_match.group(1).strip().capitalize()

        conf_match = re.search(
            r"Confidence Score:\s*(\d+)", response_text, re.IGNORECASE
        )
        if conf_match:
            result["confidence_score"] = max(0, min(100, int(conf_match.group(1))))

        tech_match = re.search(
            r"Technique:\s*(.+?)(?:\n|$)", response_text, re.IGNORECASE
        )
        if tech_match:
            result["mitre_technique"] = tech_match.group(1).strip()

        tactic_match = re.search(
            r"Tactic:\s*(.+?)(?:\n|$)", response_text, re.IGNORECASE
        )
        if tactic_match:
            result["mitre_tactic"] = tactic_match.group(1).strip()

        reasoning_match = re.search(
            r"Reasoning:\s*(.+?)(?:\nRecommended|\n\n|$)",
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        if reasoning_match:
            result["reasoning"] = reasoning_match.group(1).strip()

        actions_section = re.search(
            r"Recommended Actions:(.*?)(?:\nEscalation|$)",
            response_text,
            re.IGNORECASE | re.DOTALL,
        )
        if actions_section:
            actions = re.findall(
                r"^\s*\d+[.)]\s*(.+)$", actions_section.group(1), re.MULTILINE
            )
            result["recommended_actions"] = [a.strip() for a in actions if a.strip()]

        escalation_match = re.search(
            r"Escalation Required:\s*(Yes|No)", response_text, re.IGNORECASE
        )
        if escalation_match:
            result["escalation_required"] = escalation_match.group(1).strip().capitalize()

    except Exception as exc:  # noqa: BLE001
        print(f"Error parsing Gemini response: {exc}. Falling back to mock mode.")
        return analyze_with_mock(alert_description)

    if not result["alert_summary"]:
        result["alert_summary"] = _truncate(alert_description, 100)
    if not result["recommended_actions"]:
        result["recommended_actions"] = _default_actions()

    return result


# ---------------------------------------------------------------------------
# Mock analyser
# ---------------------------------------------------------------------------

SEVERITY_KEYWORDS = [
    (
        "Critical",
        [
            "malware",
            "ransomware",
            "data breach",
            "exfiltration",
            "privilege escalation",
            "lateral movement",
            "command and control",
        ],
    ),
    (
        "High",
        [
            "suspicious",
            "unauthorized",
            "unauthorised",
            "brute force",
            "phishing",
            "powershell",
            "encoded",
        ],
    ),
    (
        "Medium",
        ["anomaly", "unusual", "failed login", "port scan", "scan"],
    ),
]

SEVERITY_RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}

CONFIDENCE_RANGES = {
    "Critical": (85, 95),
    "High": (75, 88),
    "Medium": (65, 80),
    "Low": (50, 70),
}

TACTIC_SEVERITY_FLOOR = {
    "Impact": "Critical",
    "Exfiltration": "High",
    "Lateral Movement": "High",
    "Privilege Escalation": "High",
    "Initial Access": "High",
    "Credential Access": "Medium",
    "Collection": "Medium",
    "Command and Control": "Medium",
    "Defense Evasion": "Medium",
    "Execution": "Medium",
    "Discovery": "Low",
}

DEFAULT_TECHNIQUE = "T1071 Application Layer Protocol"
DEFAULT_TACTIC = "Command and Control"

TECHNIQUE_RULES = [
    (["powershell", "encoded command", "encoded"], "T1059.001 PowerShell", "Execution"),
    (
        ["brute force", "failed login", "multiple failed", "password spray"],
        "T1110 Brute Force",
        "Credential Access",
    ),
    (["ransomware", "encrypted files"], "T1486 Data Encrypted for Impact", "Impact"),
    (
        ["exfiltration", "large file transfer", "data transfer"],
        "T1041 Exfiltration Over C2 Channel",
        "Exfiltration",
    ),
    (["registry"], "T1112 Modify Registry", "Defense Evasion"),
    (["webcam", "camera"], "T1125 Video Capture", "Collection"),
    (["audio", "microphone"], "T1123 Audio Capture", "Collection"),
    (["phishing", "malicious attachment"], "T1566 Phishing", "Initial Access"),
    (
        ["privilege escalation", "elevated privileges"],
        "T1068 Exploitation for Privilege Escalation",
        "Privilege Escalation",
    ),
    (["lateral movement", "remote service"], "T1021 Remote Services", "Lateral Movement"),
    (["download", "upload", "file transfer"], "T1105 Ingress Tool Transfer", "Command and Control"),
    (["valid account", "compromised account"], "T1078 Valid Accounts", "Defense Evasion"),
]


def analyze_with_mock(alert_description):
    """Deterministic keyword-based analysis used when Gemini is unavailable."""
    alert_lower = (alert_description or "").lower()

    severity = "Low"
    for level, keywords in SEVERITY_KEYWORDS:
        if any(word in alert_lower for word in keywords):
            severity = level
            break

    technique, tactic = DEFAULT_TECHNIQUE, DEFAULT_TACTIC
    matched_technique = False
    for keywords, tech, tac in TECHNIQUE_RULES:
        if any(word in alert_lower for word in keywords):
            technique, tactic = tech, tac
            matched_technique = True
            break

    if matched_technique:
        floor = TACTIC_SEVERITY_FLOOR.get(tactic, "Low")
        if SEVERITY_RANK[floor] > SEVERITY_RANK[severity]:
            severity = floor

    confidence = _stable_score(alert_description, *CONFIDENCE_RANGES[severity])

    reasoning = (
        f"Keyword analysis of the alert indicates {severity.lower()} severity activity. "
        f"The described behaviour is consistent with {technique} under the "
        f"{tactic} tactic. This is a rule-based assessment and should be "
        f"confirmed against host and network telemetry before acting."
    )

    return {
        "alert_summary": _truncate(alert_description, 100),
        "severity": severity,
        "confidence_score": confidence,
        "mitre_technique": technique,
        "mitre_tactic": tactic,
        "reasoning": reasoning,
        "recommended_actions": _default_actions(),
        "escalation_required": "Yes" if severity in ("Critical", "High") else "No",
        "mode": "Mock",
    }


def _default_actions():
    return [
        "Isolate the affected system from the network",
        "Collect volatile memory and disk images for forensic analysis",
        "Review related logs for additional indicators of compromise",
        "Block associated IOCs at perimeter defences",
    ]


def _stable_score(text, low, high):
    """Map text to a repeatable value in [low, high] via a content hash."""
    if high <= low:
        return low
    digest = hashlib.sha256((text or "").encode("utf-8")).digest()
    return low + (digest[0] % (high - low + 1))


def _truncate(text, limit):
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


def get_mode_label():
    """Human-readable description of the active analysis backend."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key in ("", "your_api_key_here", "your_gemini_api_key_here", "your gemini api key here"):
        api_key = None

    if not SDK_STYLE:
        return "Mock mode - no Gemini SDK installed"
    if not api_key:
        return "Mock mode - no GEMINI_API_KEY set"
    return f"Gemini ({MODEL_NEW if SDK_STYLE == 'genai' else MODEL_LEGACY})"
