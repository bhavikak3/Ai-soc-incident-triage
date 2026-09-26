"""
Tests for llm.py - the analysis layer.

Run with:  python tests/test_llm.py
"""

import os
import sys

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import llm  # noqa: E402

# These tests assert on exact severities and confidence values, so they must run
# against the deterministic mock analyser. Without this, a populated .env would
# send every example to the live API - spending quota and failing the
# determinism check, since a model is free to word things differently each call.
# The Gemini path is covered separately in test_gemini_path.py.
os.environ["GEMINI_API_KEY"] = ""

REQUIRED_KEYS = {
    "alert_summary",
    "severity",
    "confidence_score",
    "mitre_technique",
    "mitre_tactic",
    "reasoning",
    "recommended_actions",
    "escalation_required",
    "mode",
}

EXAMPLES = [
    "Suspicious PowerShell command executed. Encoded commands detected and a file downloaded from an external domain.",
    "Multiple failed login attempts from unusual IP address.",
    "Large file transfer detected to external server.",
    "Unauthorized registry modification detected.",
    "Webcam access attempted by unknown process.",
    "Ransomware encrypted files on the finance share.",
    "Routine antivirus definition update completed.",
    "",
]


def test_backend_label():
    print("=== analysis backend ===")
    print("  ", llm.get_mode_label())


def test_result_shape():
    print("\n=== every alert returns a well-formed result ===")
    for text in EXAMPLES:
        result = llm.analyze_alert(text)
        missing = REQUIRED_KEYS - set(result)
        assert not missing, f"missing keys {missing} for {text!r}"
        assert result["severity"] in ("Critical", "High", "Medium", "Low")
        assert 0 <= result["confidence_score"] <= 100
        assert isinstance(result["recommended_actions"], list)
        assert result["recommended_actions"], "no actions returned"
        assert result["escalation_required"] in ("Yes", "No")
        label = text[:45] or "<empty string>"
        print(
            f"  [{result['severity']:8}] {result['confidence_score']:3}% "
            f"{result['mitre_technique']:42} esc={result['escalation_required']:3} | {label}"
        )


def test_determinism():
    print("\n=== same input yields the same verdict ===")
    first = llm.analyze_alert(EXAMPLES[0])
    second = llm.analyze_alert(EXAMPLES[0])
    assert first == second, "analysis is not deterministic"
    print(f"  confidence stable across calls: {first['confidence_score']}%")


def test_brute_force_mapping():
    print("\n=== failed logins map to T1110, not T1078 ===")
    result = llm.analyze_alert("Multiple failed login attempts from unusual IP address.")
    print(f"  {result['mitre_technique']} / {result['mitre_tactic']}")
    assert result["mitre_technique"].startswith("T1110")
    assert result["mitre_tactic"] == "Credential Access"


WELL_FORMED = """Alert Summary: Encoded PowerShell execution with external download.

Severity: High

Confidence Score: 88

MITRE ATT&CK Mapping:
Technique: T1059.001 PowerShell
Tactic: Execution

Reasoning: Base64-encoded commands paired with an outbound fetch is a common loader pattern.

Recommended Actions:
1. Isolate the host
2. Capture the PowerShell script block logs
3. Check the destination domain reputation
4. Hunt for the same command line elsewhere

Escalation Required: Yes
"""


def test_parse_well_formed():
    print("\n=== parsing a well-formed model reply ===")
    parsed = llm.parse_gemini_response(WELL_FORMED, "fallback description")
    assert parsed["severity"] == "High"
    assert parsed["confidence_score"] == 88
    assert parsed["mitre_technique"] == "T1059.001 PowerShell"
    assert parsed["mitre_tactic"] == "Execution"
    assert len(parsed["recommended_actions"]) == 4, parsed["recommended_actions"]
    assert parsed["escalation_required"] == "Yes"
    print(
        f"  {parsed['severity']} {parsed['confidence_score']}% | "
        f"{len(parsed['recommended_actions'])} actions | esc={parsed['escalation_required']}"
    )


def test_parse_malformed():
    print("\n=== parsing a malformed reply (previously raised NameError) ===")
    parsed = llm.parse_gemini_response("total nonsense, no fields", "my alert text")
    assert parsed["recommended_actions"], "should fall back to default actions"
    assert parsed["alert_summary"], "should fall back to the description"
    print(f"  survived: severity={parsed['severity']} summary={parsed['alert_summary'][:40]!r}")


def test_confidence_clamped():
    print("\n=== out-of-range confidence is clamped ===")
    high = llm.parse_gemini_response("Severity: High\nConfidence Score: 999", "x")
    assert high["confidence_score"] == 100, high["confidence_score"]
    print("  999 -> 100 OK")


if __name__ == "__main__":
    test_backend_label()
    test_result_shape()
    test_determinism()
    test_brute_force_mapping()
    test_parse_well_formed()
    test_parse_malformed()
    test_confidence_clamped()
    print("\nALL LLM TESTS PASSED")
