import json
import re


REQUIRED_TOP_KEYS = {
    "clarifying_questions",
    "summary",
    "suggested_tests",
    "doctor_approval_required",
}

REQUIRED_SUMMARY_KEYS = {
    "patient_info",
    "presenting_symptoms",
    "known_history",
    "possible_concerns",
    "missing_info",
    "urgency",
}


def extract_json_block(text: str) -> str:
    text = text.strip()

    match = re.search(r"\{.*", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model output.")

    json_text = match.group(0).strip()
    return json_text


def repair_json_text(json_text: str) -> str:
    json_text = json_text.strip()

    # remove markdown fences if present
    json_text = json_text.replace("```json", "").replace("```", "").strip()

    # balance braces
    open_braces = json_text.count("{")
    close_braces = json_text.count("}")
    if close_braces < open_braces:
        json_text += "}" * (open_braces - close_braces)

    # remove trailing commas before } or ]
    json_text = re.sub(r",\s*}", "}", json_text)
    json_text = re.sub(r",\s*]", "]", json_text)

    return json_text


def parse_triage_output(raw_text: str) -> dict:
    json_text = extract_json_block(raw_text)
    json_text = repair_json_text(json_text)

    data = json.loads(json_text)

    missing_top = REQUIRED_TOP_KEYS - set(data.keys())
    if missing_top:
        raise ValueError(f"Missing top-level keys: {missing_top}")

    summary = data.get("summary", {})
    missing_summary = REQUIRED_SUMMARY_KEYS - set(summary.keys())
    if missing_summary:
        raise ValueError(f"Missing summary keys: {missing_summary}")

    return data


def safe_parse_triage_output(raw_text: str) -> dict:
    try:
        return {
            "ok": True,
            "data": parse_triage_output(raw_text),
            "error": None,
            "raw_text": raw_text,
        }
    except Exception as e:
        return {
            "ok": False,
            "data": None,
            "error": str(e),
            "raw_text": raw_text,
        }