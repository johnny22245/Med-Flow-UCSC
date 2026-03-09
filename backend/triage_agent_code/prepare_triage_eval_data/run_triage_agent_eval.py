import os
import json
from langgraph_triage import triage_graph

input_path = "/home/achowd10/MedFlow_244_project/prepare_triage_eval_data/data/test.jsonl"
output_path = "./results/bio_mistral_7B_agentic_1round.json"
os.makedirs("./results", exist_ok=True)


def load_cases(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def get_answer_for_question(question, gold_answers):
    if not gold_answers:
        return "Not provided."

    q_norm = question.strip().lower()

    for k, v in gold_answers.items():
        if k.strip().lower() == q_norm:
            return v

    for k, v in gold_answers.items():
        if q_norm in k.strip().lower() or k.strip().lower() in q_norm:
            return v

    return "Not provided."


def run_case(case_row):
    state = {
        "initial_case": case_row["initial_case"],
        "qa_history": [],
        "round_count": 0,
        "max_rounds": 2,
        "latest_raw_output": "",
        "triage_output": {},
        "status": "start",
        "doctor_approved": False,
    }

    # round 1
    state = triage_graph.invoke(state)

    first_output = state["triage_output"]
    if not first_output["ok"]:
        return {
            "case_id": case_row["case_id"],
            "parse_ok": False,
            "final_status": "error",
            "round_count": state["round_count"],
            "raw_output": state["latest_raw_output"],
            "parsed_output": None,
        }

    first_data = first_output["data"]

    # optional round 2
    if state["status"] == "needs_more_info":
        questions = first_data.get("clarifying_questions", [])
        gold_answers = case_row.get("gold_followup_answers", {}) or {}

        for item in questions:
            q = item.get("question", "") if isinstance(item, dict) else str(item)
            a = get_answer_for_question(q, gold_answers)
            state["qa_history"].append({"question": q, "answer": a})

        state = triage_graph.invoke(state)

    final_output = state["triage_output"]

    return {
        "case_id": case_row["case_id"],
        "parse_ok": final_output["ok"],
        "final_status": state["status"],
        "round_count": state["round_count"],
        "raw_output": state["latest_raw_output"],
        "parsed_output": final_output["data"] if final_output["ok"] else None,
        "parse_error": final_output["error"],
        "qa_history": state["qa_history"],
    }


def main():
    cases = load_cases(input_path)
    results = []

    for idx, row in enumerate(cases, start=1):
        print(f"Running case {idx}/{len(cases)} : {row['case_id']}")
        results.append(run_case(row))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

    print(f"Saved results to: {output_path}")


if __name__ == "__main__":
    main()