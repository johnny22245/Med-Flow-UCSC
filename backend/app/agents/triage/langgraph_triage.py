from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from transformers import AutoTokenizer
from .distributed_LLM_call import DistributedModel
from .prompt_template import render_prompt_from_string
from .parser_utils import safe_parse_triage_output


MODEL_PATH = "/home/achowd10/MedFlow_244_project/models/Bio_mistral_7B_Dare"


class TriageState(TypedDict):
    initial_case: str
    qa_history: List[Dict[str, str]]
    round_count: int
    max_rounds: int
    latest_raw_output: str
    triage_output: Dict[str, Any]
    status: str
    doctor_approved: bool


# load once
model = DistributedModel(
    MODEL_PATH,
    temperature=0.0,
    top_p=1,
    max_new_tokens=1024,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, use_fast=True)


def build_context(state):
    lines = []
    lines.append(f"Initial case:\n{state['initial_case']}\n")

    if state["qa_history"]:
        lines.append("Clarification history:")
        for idx, qa in enumerate(state["qa_history"], start=1):
            lines.append(f"Q{idx}: {qa['question']}")
            lines.append(f"A{idx}: {qa['answer']}")
        lines.append("")

    lines.append("Return the required JSON object only.")
    return "\n".join(lines)


def triage_node(state):
    context_text = build_context(state)
    prompt = render_prompt_from_string(context_text, tokenizer)

    result = model.generate({"case": prompt})
    raw_text = result["case"]

    parsed = safe_parse_triage_output(raw_text)

    if not parsed["ok"]:
        repair_text = (
            "Return valid JSON only.\n"
            "Use this schema exactly:\n"
            "{\n"
            '  "clarifying_questions": [],\n'
            '  "summary": {\n'
            '    "patient_info": "",\n'
            '    "presenting_symptoms": [],\n'
            '    "known_history": [],\n'
            '    "possible_concerns": [],\n'
            '    "missing_info": [],\n'
            '    "urgency": ""\n'
            "  },\n"
            '  "suggested_tests": [],\n'
            '  "doctor_approval_required": true\n'
            "}\n\n"
            f"Clinical context:\n{context_text}\n\n"
            f"Previous invalid output:\n{raw_text}"
        )

        repair_prompt = render_prompt_from_string(repair_text, tokenizer)
        repair_result = model.generate({"case": repair_prompt})
        raw_text = repair_result["case"]
        parsed = safe_parse_triage_output(raw_text)

    state["latest_raw_output"] = raw_text
    state["triage_output"] = parsed
    state["round_count"] += 1

    if not parsed["ok"]:
        state["status"] = "error"
        return state

    triage_json = parsed["data"]
    missing_info = triage_json["summary"].get("missing_info", [])
    urgency = triage_json["summary"].get("urgency", "").lower()

    if urgency in {"high", "emergent"} and state["round_count"] >= 1:
        state["status"] = "ready_for_review"
    elif missing_info and state["round_count"] < state["max_rounds"]:
        state["status"] = "needs_more_info"
    else:
        state["status"] = "ready_for_review"

    return state


def decide_next(state: TriageState) -> str:
    return state["status"]


def doctor_review_node(state: TriageState) -> TriageState:
    # placeholder node
    if state["doctor_approved"]:
        state["status"] = "approved"
    else:
        state["status"] = "ready_for_review"
    return state


graph_builder = StateGraph(TriageState)

graph_builder.add_node("triage_node", triage_node)
graph_builder.add_node("doctor_review_node", doctor_review_node)

graph_builder.set_entry_point("triage_node")

graph_builder.add_conditional_edges(
    "triage_node",
    decide_next,
    {
        "needs_more_info": END,
        "ready_for_review": "doctor_review_node",
        "error": END,
    },
)

graph_builder.add_conditional_edges(
    "doctor_review_node",
    decide_next,
    {
        "approved": END,
        "ready_for_review": END,
    },
)

triage_graph = graph_builder.compile()