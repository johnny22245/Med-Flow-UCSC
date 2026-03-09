"""
Batch inference for triage evaluation.
Supports zero-shot and few-shot modes.
"""

#exp_var = "zero_shot"
exp_var = "few_shot"

temperature = 0.0
top_p = 1
max_new_tokens = 1024

import os
import json
from distributed_LLM_call import DistributedModel
from prompt_template import render_prompt_from_string
from parser_utils import safe_parse_triage_output

from transformers import AutoTokenizer

# -------------------------
# paths
# -------------------------
input_path = "/home/achowd10/MedFlow_244_project/prepare_triage_eval_data/data/test.jsonl"
results_dir = "./results"
os.makedirs(results_dir, exist_ok=True)

# -------------------------
# models
# -------------------------
model_path_dict = {
    "bio_mistral_7B": "/home/achowd10/MedFlow_244_project/models/Bio_mistral_7B_Dare",
    # "mistral_7B": "/home/achowd10/MedFlow_244_project/models/Mistral_7B_inst",
}

few_shot_flag = exp_var.lower() == "few_shot"


def load_cases(path):
    if path.endswith(".jsonl"):
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    elif path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data

        if isinstance(data, dict):
            rows = []
            for k, v in data.items():
                if isinstance(v, dict):
                    v["case_id"] = v.get("case_id", k)
                    rows.append(v)
            return rows

    raise ValueError(f"Unsupported input format: {path}")


for model_name, model_path in model_path_dict.items():
    print(f"\nLoading model: {model_name}")
    model = DistributedModel(
        model_path,
        temperature=temperature,
        top_p=top_p,
        max_new_tokens=max_new_tokens
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)

    cases = load_cases(input_path)
    prompts = {}

    for row in cases:
        case_id = row["case_id"]
        initial_case = row["initial_case"]

        prompt_text = render_prompt_from_string(
            initial_case,
            tokenizer,
            few_shot=few_shot_flag
        )
        prompts[case_id] = prompt_text

    print(f"Running {len(prompts)} cases...")
    raw_results = model.generate(prompts)

    parsed_results = []
    for row in cases:
        case_id = row["case_id"]
        raw_text = raw_results.get(case_id, "")
        parsed = safe_parse_triage_output(raw_text)

        parsed_results.append({
            "case_id": case_id,
            "source_dataset": row.get("source_dataset", ""),
            "initial_case": row.get("initial_case", ""),
            "gold_answer_text": row.get("gold_answer_text", ""),
            "raw_output": raw_text,
            "parse_ok": parsed["ok"],
            "parsed_output": parsed["data"],
            "parse_error": parsed["error"],
        })

    write_path = os.path.join(results_dir, f"{model_name}_{exp_var}_parsed.json")
    with open(write_path, "w", encoding="utf-8") as f:
        json.dump(parsed_results, f, indent=4, ensure_ascii=False)

    print(f"Saved results to: {write_path}")

    del model