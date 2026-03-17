import json
import re
from collections import Counter

#pred_path = "./results/bio_mistral_7B_zero_shot_parsed.json"
#pred_path = "./results/bio_mistral_7B_few_shot_parsed.json"
pred_path = "./results/llama_8B_few_shot_parsed.json"


def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def token_set(text):
    return set(normalize_text(text).split())


def token_overlap_score(a, b):
    a_set = token_set(a)
    b_set = token_set(b)
    if not a_set or not b_set:
        return 0.0
    inter = len(a_set & b_set)
    union = len(a_set | b_set)
    return inter / union


def concern_hit(pred_concerns, gold_answer_text):
    """
    Weak correctness:
    - exact normalized match
    - substring match
    - token overlap >= threshold
    """
    gold = normalize_text(gold_answer_text)
    if not gold:
        return 0

    for concern in pred_concerns:
        pred = normalize_text(concern)
        if not pred:
            continue

        if pred == gold:
            return 1
        if pred in gold or gold in pred:
            return 1
        if token_overlap_score(pred, gold) >= 0.4:
            return 1

    return 0


def derive_expected_urgency(case_text):
    text = normalize_text(case_text)

    emergent_keywords = [
        "chest pain", "radiating", "left arm", "diaphoresis", "slurred speech",
        "facial droop", "weakness", "seizure", "neck stiffness", "confusion",
        "shortness of breath", "hematemesis", "melena", "syncope"
    ]
    high_keywords = [
        "high fever", "severe abdominal pain", "flank pain", "pregnant with bleeding",
        "tachycardia", "hypotension"
    ]
    medium_keywords = [
        "fever", "cough", "vomiting", "dysuria", "urinary frequency",
        "headache", "abdominal pain", "rash"
    ]

    if any(k in text for k in emergent_keywords):
        return "emergent"
    if any(k in text for k in high_keywords):
        return "high"
    if any(k in text for k in medium_keywords):
        return "medium"
    return "low"


def urgency_score(pred_urgency, gold_urgency):
    pred = normalize_text(pred_urgency)
    gold = normalize_text(gold_urgency)

    if pred == gold:
        return "exact"

    near_pairs = {
        ("emergent", "high"),
        ("high", "emergent"),
        ("medium", "low"),
        ("low", "medium"),
        ("medium", "high"),
        ("high", "medium"),
    }

    if (pred, gold) in near_pairs:
        return "near"

    return "wrong"


def expected_tests_from_case(case_text):
    text = normalize_text(case_text)

    mapping = []

    if "chest pain" in text:
        mapping.extend(["ecg", "troponin", "chest x ray"])
    if "slurred speech" in text or "facial droop" in text or "weakness" in text:
        mapping.extend(["ct head", "glucose"])
    if "dysuria" in text or "urinary frequency" in text:
        mapping.extend(["urinalysis", "urine culture"])
    if "abdominal pain" in text:
        mapping.extend(["cbc", "cmp", "lipase"])
    if "shortness of breath" in text:
        mapping.extend(["chest x ray", "ecg", "pulse oximetry"])
    if "fever" in text and "neck stiffness" in text:
        mapping.extend(["cbc", "blood cultures", "lumbar puncture", "ct head"])

    return list(sorted(set(mapping)))


def normalize_test_name(test_name):
    text = normalize_text(test_name)
    text = text.replace("xray", "x ray")
    text = text.replace("ct scan head", "ct head")
    text = text.replace("head ct", "ct head")
    return text


def test_match(predicted_tests, expected_tests):
    pred = [normalize_test_name(x) for x in predicted_tests]
    exp = [normalize_test_name(x) for x in expected_tests]

    if not exp:
        return None

    hit = 0
    for e in exp:
        found = False
        for p in pred:
            if p == e or p in e or e in p or token_overlap_score(p, e) >= 0.5:
                found = True
                break
        if found:
            hit += 1

    recall = hit / len(exp) if exp else 0.0
    precision = hit / len(pred) if pred else 0.0
    return {"hit": hit, "expected": len(exp), "precision": precision, "recall": recall}


def main():
    with open(pred_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    total = len(rows)
    parse_ok = 0

    concern_hits = 0

    urgency_exact = 0
    urgency_near = 0
    urgency_wrong = 0

    test_eval_count = 0
    test_precision_sum = 0.0
    test_recall_sum = 0.0

    bad_cases = []

    for row in rows:
        if not row.get("parse_ok", False):
            continue

        parse_ok += 1
        data = row.get("parsed_output", {})
        if not data:
            continue

        summary = data.get("summary", {})
        pred_concerns = summary.get("possible_concerns", [])
        pred_urgency = summary.get("urgency", "")
        pred_tests = data.get("suggested_tests", [])

        case_text = row.get("initial_case", "")
        gold_answer_text = row.get("gold_answer_text", "")

        # concern correctness
        c_hit = concern_hit(pred_concerns, gold_answer_text)
        concern_hits += c_hit

        # urgency correctness
        gold_urgency = derive_expected_urgency(case_text)
        u_score = urgency_score(pred_urgency, gold_urgency)
        if u_score == "exact":
            urgency_exact += 1
        elif u_score == "near":
            urgency_near += 1
        else:
            urgency_wrong += 1

        # suggested test correctness
        exp_tests = expected_tests_from_case(case_text)
        t_score = test_match(pred_tests, exp_tests)
        if t_score is not None:
            test_eval_count += 1
            test_precision_sum += t_score["precision"]
            test_recall_sum += t_score["recall"]

        # save bad examples
        if c_hit == 0 or u_score == "wrong":
            bad_cases.append({
                "case_id": row.get("case_id", ""),
                "initial_case": case_text,
                "gold_answer_text": gold_answer_text,
                "pred_concerns": pred_concerns,
                "pred_urgency": pred_urgency,
                "gold_urgency": gold_urgency,
                "pred_tests": pred_tests,
            })

    print("\n" + "=" * 60)
    print("TRIAGE CORRECTNESS EVAL")
    print("=" * 60)
    print(f"Total cases: {total}")
    print(f"Parse success: {parse_ok}/{total} = {round(100 * parse_ok / total, 2) if total else 0}%")

    if parse_ok > 0:
        print(f"Concern hit rate: {concern_hits}/{parse_ok} = {round(100 * concern_hits / parse_ok, 2)}%")
        print(
            f"Urgency exact / near / wrong: "
            f"{urgency_exact} / {urgency_near} / {urgency_wrong}"
        )
        print(
            f"Urgency relaxed accuracy (exact+near): "
            f"{round(100 * (urgency_exact + urgency_near) / parse_ok, 2)}%"
        )

    print("=" * 60)

    with open("triage_bad_cases.json", "w", encoding="utf-8") as f:
        json.dump(bad_cases[:50], f, indent=2, ensure_ascii=False)

    print("Saved sample bad cases to triage_bad_cases.json\n")


if __name__ == "__main__":
    main()