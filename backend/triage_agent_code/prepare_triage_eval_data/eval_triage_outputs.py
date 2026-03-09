import json
from collections import Counter


#pred_path = "./results/bio_mistral_7B_zero_shot_parsed.json"
#pred_path = "./results/bio_mistral_7B_few_shot_parsed.json"
pred_path = "./results/bio_mistral_7B_agentic_1round.json"


def main():
    with open(pred_path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    total = len(rows)
    parse_ok = 0
    urgency_counter = Counter()
    with_tests = 0
    with_questions = 0
    symptom_counts = []
    missing_info_counts = []
    test_counts = []

    for row in rows:
        ok = row.get("parse_ok", False)
        if not ok:
            continue

        parse_ok += 1
        data = row.get("parsed_output", {})
        if not data:
            continue

        summary = data.get("summary", {})
        urgency = summary.get("urgency", "").strip().lower()
        if urgency:
            urgency_counter[urgency] += 1

        symptoms = summary.get("presenting_symptoms", [])
        missing_info = summary.get("missing_info", [])
        suggested_tests = data.get("suggested_tests", [])
        clarifying_questions = data.get("clarifying_questions", [])

        symptom_counts.append(len(symptoms))
        missing_info_counts.append(len(missing_info))
        test_counts.append(len(suggested_tests))

        if suggested_tests:
            with_tests += 1
        if clarifying_questions:
            with_questions += 1

    print("\n" + "=" * 60)
    print("TRIAGE EVAL SUMMARY")
    print("=" * 60)
    print(f"Total cases: {total}")
    print(f"Parse success: {parse_ok}/{total} = {round(parse_ok / total * 100, 2) if total else 0}%")

    if parse_ok > 0:
        print(f"Cases with suggested tests: {with_tests}/{parse_ok} = {round(with_tests / parse_ok * 100, 2)}%")
        print(f"Cases with clarifying questions: {with_questions}/{parse_ok} = {round(with_questions / parse_ok * 100, 2)}%")
        print(f"Average symptom count: {round(sum(symptom_counts) / len(symptom_counts), 2)}")
        print(f"Average missing-info count: {round(sum(missing_info_counts) / len(missing_info_counts), 2)}")
        print(f"Average suggested-test count: {round(sum(test_counts) / len(test_counts), 2)}")

    print("\nUrgency distribution:")
    for k, v in urgency_counter.items():
        print(f"  {k}: {v}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()