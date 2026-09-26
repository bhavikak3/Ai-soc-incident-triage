"""
Tests for the Gemini code path in llm.py.

This is the one path the other suites never exercise, because it needs both a
Gemini SDK and a network connection. Here the SDK is replaced with a stub that
returns a canned reply, so the real code - client construction, prompt
assembly, parsing, mode labelling and the fallback on failure - runs offline
and end to end.

A passing run does NOT prove the API key is valid. It proves that when the API
answers, the app handles the answer correctly, and that when it does not, the
app degrades instead of crashing.

Run with:  python tests/test_gemini_path.py
"""

import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(1, ROOT)

CANNED = """Alert Summary: Encoded PowerShell downloaded a payload from an external host.

Severity: High

Confidence Score: 87

MITRE ATT&CK Mapping:
Technique: T1059.001 PowerShell
Tactic: Execution

Reasoning: Base64-encoded command lines combined with an outbound fetch match a
common loader pattern used to stage second-stage malware.

Recommended Actions:
1. Capture PowerShell script block logs (Event ID 4104) from the host
2. Check reputation of the external domain contacted
3. Isolate the host if the download completed
4. Hunt for the same command line across other endpoints

Escalation Required: Yes
"""

SENT = []          # prompts the stub was asked to send
BEHAVIOUR = {"mode": "ok"}   # flipped per test: ok | raise | empty


class _Response:
    def __init__(self, text):
        self.text = text


class _Models:
    def generate_content(self, model=None, contents=None):
        SENT.append({"model": model, "prompt": contents})
        if BEHAVIOUR["mode"] == "raise":
            raise RuntimeError("429 RESOURCE_EXHAUSTED (simulated rate limit)")
        if BEHAVIOUR["mode"] == "empty":
            return _Response("")
        return _Response(CANNED)


class _Client:
    def __init__(self, api_key=None):
        self.api_key = api_key
        SENT.append({"client_key": api_key})
        self.models = _Models()


def _install_stub_sdk():
    """Put a fake `google.genai` on sys.modules before llm.py imports it."""
    google_pkg = types.ModuleType("google")
    google_pkg.__path__ = []
    genai_mod = types.ModuleType("google.genai")
    genai_mod.Client = _Client
    google_pkg.genai = genai_mod
    sys.modules["google"] = google_pkg
    sys.modules["google.genai"] = genai_mod


_install_stub_sdk()

import llm  # noqa: E402  (must come after the stub is installed)


def test_env_file_supplies_a_key():
    print("=== the key is read from .env, not hardcoded ===")
    env_path = os.path.join(ROOT, ".env")
    assert os.path.exists(env_path), ".env is missing"

    with open(env_path, encoding="utf-8") as handle:
        body = handle.read()
    assert "GEMINI_API_KEY=" in body, ".env has no GEMINI_API_KEY line"

    from dotenv import dotenv_values

    key = (dotenv_values(env_path).get("GEMINI_API_KEY") or "").strip()
    assert key, "GEMINI_API_KEY is empty"
    if key in ("your_api_key_here", "your_gemini_api_key_here", "your gemini api key here"):
        print("  placeholder key present (safe for public git repository)")
        return key

    for source in ("llm.py", "app.py", "database.py"):
        with open(os.path.join(ROOT, source), encoding="utf-8") as handle:
            assert key not in handle.read(), f"key is hardcoded in {source}"

    print(f"  found a {len(key)}-char key ending ...{key[-4:]}, absent from all source files")
    return key


def test_sdk_detected():
    print("\n=== SDK detection ===")
    assert llm.SDK_STYLE == "genai", f"expected the current SDK, got {llm.SDK_STYLE!r}"
    os.environ["GEMINI_API_KEY"] = "test-key-1234"
    label = llm.get_mode_label()
    print(f"  SDK_STYLE={llm.SDK_STYLE}  label={label!r}")
    assert label.startswith("Gemini"), "a present key should not report mock mode"
    assert llm.MODEL_NEW in label


def test_successful_call():
    print("\n=== a good reply is parsed into all seven fields ===")
    SENT.clear()
    BEHAVIOUR["mode"] = "ok"
    alert = "Suspicious PowerShell executed an encoded command and downloaded a file"
    result = llm.analyze_alert(alert)

    assert result["mode"] == "Gemini", f"mode should be Gemini, got {result['mode']!r}"
    assert result["severity"] == "High"
    assert result["confidence_score"] == 87
    assert result["mitre_technique"] == "T1059.001 PowerShell"
    assert result["mitre_tactic"] == "Execution"
    assert "loader pattern" in result["reasoning"]
    assert len(result["recommended_actions"]) == 4, result["recommended_actions"]
    assert result["escalation_required"] == "Yes"

    # The actions must be the model's, not the hardcoded mock list.
    assert result["recommended_actions"] != llm._default_actions(), (
        "fell back to the generic mock actions"
    )
    assert "4104" in result["recommended_actions"][0], "model-specific detail lost"

    print(f"  {result['severity']} {result['confidence_score']}% {result['mitre_technique']}")
    print(f"  actions are alert-specific: {result['recommended_actions'][0][:52]}...")


def test_request_was_well_formed():
    print("\n=== the outgoing request ===")
    keys = [c["client_key"] for c in SENT if "client_key" in c]
    calls = [c for c in SENT if "prompt" in c]
    assert keys == ["test-key-1234"], f"key not passed to the client: {keys}"
    assert len(calls) == 1, f"expected exactly one API call, made {len(calls)}"

    prompt = calls[0]["prompt"]
    assert calls[0]["model"] == llm.MODEL_NEW, calls[0]["model"]
    assert "Suspicious PowerShell" in prompt, "the alert text never reached the prompt"
    assert "Alert Summary:" in prompt and "Escalation Required:" in prompt, (
        "the response template was not included, so replies would be unparseable"
    )
    print(f"  1 call to {calls[0]['model']}, {len(prompt)} char prompt, key passed, template included")


def test_api_failure_degrades_to_mock():
    print("\n=== an API failure degrades instead of crashing ===")
    SENT.clear()
    BEHAVIOUR["mode"] = "raise"
    result = llm.analyze_alert("Ransomware encrypted files on the finance share")
    assert result["mode"] == "Mock (Gemini call failed)", result["mode"]
    assert result["severity"] == "Critical", "mock analyser did not run"
    assert result["recommended_actions"], "no actions after fallback"
    print(f"  rate limit -> {result['mode']!r}, still returned {result['severity']}")


def test_empty_reply_degrades_to_mock():
    print("\n=== an empty reply degrades too ===")
    SENT.clear()
    BEHAVIOUR["mode"] = "empty"
    result = llm.analyze_alert("Multiple failed login attempts from unusual IP")
    assert result["mode"] == "Mock (Gemini call failed)", result["mode"]
    assert result["mitre_technique"].startswith("T1110")
    print(f"  empty response -> {result['mode']!r}, mapping still {result['mitre_technique']}")


def test_missing_key_forces_mock():
    print("\n=== no key means mock, even with the SDK present ===")
    SENT.clear()
    BEHAVIOUR["mode"] = "ok"
    saved = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = "your_api_key_here"
        result = llm.analyze_alert("Unauthorized registry modification detected")
        assert result["mode"] == "Mock", result["mode"]
        assert not SENT, "the placeholder key still triggered an API call"
        print("  placeholder treated as absent, no call attempted OK")

        os.environ["GEMINI_API_KEY"] = ""
        assert llm.analyze_alert("test")["mode"] == "Mock"
        assert not SENT, "an empty key still triggered an API call"
        print("  empty key treated as absent, no call attempted OK")
    finally:
        if saved is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = saved


if __name__ == "__main__":
    test_env_file_supplies_a_key()
    test_sdk_detected()
    test_successful_call()
    test_request_was_well_formed()
    test_api_failure_degrades_to_mock()
    test_empty_reply_degrades_to_mock()
    test_missing_key_forces_mock()
    print("\nALL GEMINI PATH TESTS PASSED (stubbed SDK - does not validate the key itself)")
