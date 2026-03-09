import json
from langgraph_triage import triage_graph


def print_triage_result(data: dict):
    summary = data["summary"]

    print("\n" + "=" * 60)
    print("TRIAGE RESULT")
    print("=" * 60)
    print(f"Patient: {summary['patient_info']}")
    print(f"Symptoms: {', '.join(summary['presenting_symptoms'])}")
    print(f"Known history: {', '.join(summary['known_history']) if summary['known_history'] else 'None'}")
    print(f"Concerns: {', '.join(summary['possible_concerns']) if summary['possible_concerns'] else 'None'}")
    print(f"Missing info: {', '.join(summary['missing_info']) if summary['missing_info'] else 'None'}")
    print(f"Urgency: {summary['urgency']}")
    print(f"Suggested tests: {', '.join(data['suggested_tests']) if data['suggested_tests'] else 'None'}")
    print(f"Doctor approval required: {data['doctor_approval_required']}")
    print("=" * 60 + "\n")


def main():
    initial_case = input("Enter initial case: ").strip()

    state = {
        "initial_case": initial_case,
        "qa_history": [],
        "round_count": 0,
        "max_rounds": 2,
        "latest_raw_output": "",
        "triage_output": {},
        "status": "start",
        "doctor_approved": False,
    }

    while True:
        state = triage_graph.invoke(state)

        parsed = state["triage_output"]
        if not parsed["ok"]:
            print("Model output parse failed.")
            print(parsed["error"])
            print(parsed["raw_text"])
            break

        data = parsed["data"]
        print_triage_result(data)

        if state["status"] == "needs_more_info":
            questions = data.get("clarifying_questions", [])
            if not questions:
                print("No clarifying questions returned. Stopping.")
                break

            print("Please answer the clarifying questions:")
            for item in questions:
                if isinstance(item, dict):
                    q = item.get("question", "")
                else:
                    q = str(item)

                ans = input(f"- {q}\n> ").strip()
                state["qa_history"].append({"question": q, "answer": ans})

            continue

        if state["status"] in {"ready_for_review", "approved"}:
            doctor_input = input("Approve this triage result? (yes/no): ").strip().lower()
            state["doctor_approved"] = doctor_input == "yes"

            if state["doctor_approved"]:
                print("Triage approved. Ready for next stage.")
                break
            else:
                print("Triage not approved. You can restart or refine.")
                break

        break


if __name__ == "__main__":
    main()