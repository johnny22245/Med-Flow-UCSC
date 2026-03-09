# save as: prepare_triage_eval_data.py

import os
import re
import json
import random
import argparse
from typing import Any, Dict, List, Optional

import pandas as pd
from datasets import load_dataset


def clean_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def is_clinical_vignette(question: str) -> bool:
    """
    Keep simple, high-recall rules for triage-like cases.
    We want patient-case style questions, not pure fact recall.
    """
    q = question.lower()

    strong_patterns = [
        r"\b\d{1,3}[- ]?year[- ]old\b",
        r"\bman\b",
        r"\bwoman\b",
        r"\bboy\b",
        r"\bgirl\b",
        r"\bpatient\b",
        r"\bpresents with\b",
        r"\bcomes to the\b",
        r"\barrives\b",
        r"\bhistory of\b",
        r"\bcomplains of\b",
        r"\breports\b",
        r"\bfever\b",
        r"\bpain\b",
        r"\bshortness of breath\b",
        r"\bnausea\b",
        r"\bvomiting\b",
        r"\bcough\b",
        r"\bchest pain\b",
        r"\bheadache\b",
        r"\babdominal pain\b",
    ]

    hits = 0
    for pat in strong_patterns:
        if re.search(pat, q):
            hits += 1

    # keep if clearly vignette-like
    if hits >= 2:
        return True

    # fallback: long enough and has some patient framing
    weak_patterns = [
        "examination",
        "diagnosis",
        "treatment",
        "management",
        "best next step",
        "most likely",
        "blood pressure",
        "heart rate",
        "temperature",
    ]
    weak_hits = sum(1 for w in weak_patterns if w in q)

    if len(q.split()) >= 18 and (hits >= 1 or weak_hits >= 2):
        return True

    return False


def extract_answer_from_index(options: List[str], answer_idx: Optional[int]) -> str:
    if answer_idx is None:
        return ""
    if 0 <= answer_idx < len(options):
        return options[answer_idx]
    return ""


def normalize_medmcqa_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Expected common fields for openlifescienceai/medmcqa:
    question, opa/opb/opc/opd, cop
    cop is often 0/1/2/3 for correct option.
    """
    question = clean_text(row.get("question"))
    options = [
        clean_text(row.get("opa")),
        clean_text(row.get("opb")),
        clean_text(row.get("opc")),
        clean_text(row.get("opd")),
    ]
    options = [x for x in options if x]

    cop = row.get("cop", None)
    answer_idx = None
    try:
        answer_idx = int(cop) if cop is not None else None
    except Exception:
        answer_idx = None

    answer_text = extract_answer_from_index(options, answer_idx)

    return {
        "source_dataset": "medmcqa",
        "source_id": clean_text(row.get("id")) or clean_text(row.get("index")) or "",
        "question": question,
        "options": options,
        "answer_text": clean_text(answer_text),
        "answer_index": answer_idx,
        "topic": clean_text(row.get("topic_name")),
        "subject": clean_text(row.get("subject_name")),
    }


def normalize_medqa_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Works for GBaker/MedQA-USMLE-4-options style rows:
    common fields are usually question, options, answer_idx
    but we guard against small schema differences.
    """
    question = clean_text(row.get("question"))

    raw_options = row.get("options", None)
    options: List[str] = []

    if isinstance(raw_options, list):
        options = [clean_text(x) for x in raw_options if clean_text(x)]
    elif isinstance(raw_options, dict):
        # handle {"A": "...", "B": "..."}
        for k in sorted(raw_options.keys()):
            val = clean_text(raw_options[k])
            if val:
                options.append(val)
    else:
        # fallback if separate fields exist
        for key in ["opa", "opb", "opc", "opd", "option_a", "option_b", "option_c", "option_d"]:
            val = clean_text(row.get(key))
            if val:
                options.append(val)

    answer_idx = None
    answer_text = ""

    # common variants
    for key in ["answer_idx", "answer_index", "label"]:
        if key in row and row[key] is not None:
            try:
                answer_idx = int(row[key])
                break
            except Exception:
                pass

    if not answer_text:
        for key in ["answer", "answer_text", "correct_answer"]:
            if key in row and row[key] is not None:
                answer_text = clean_text(row[key])
                break

    if not answer_text and answer_idx is not None and options:
        answer_text = extract_answer_from_index(options, answer_idx)

    return {
        "source_dataset": "medqa_usmle_4opt",
        "source_id": clean_text(row.get("id")) or clean_text(row.get("idx")) or "",
        "question": question,
        "options": options,
        "answer_text": clean_text(answer_text),
        "answer_index": answer_idx,
        "topic": clean_text(row.get("meta_info")) if "meta_info" in row else "",
        "subject": "",
    }


def load_and_normalize_medmcqa() -> List[Dict[str, Any]]:
    ds = load_dataset("openlifescienceai/medmcqa")
    rows: List[Dict[str, Any]] = []

    for split_name in ds.keys():
        for row in ds[split_name]:
            item = normalize_medmcqa_row(row)
            if item["question"]:
                rows.append(item)

    return rows


def load_and_normalize_medqa() -> List[Dict[str, Any]]:
    # this dataset is a simple English 4-option MedQA version
    ds = load_dataset("GBaker/MedQA-USMLE-4-options")
    rows: List[Dict[str, Any]] = []

    for split_name in ds.keys():
        for row in ds[split_name]:
            item = normalize_medqa_row(row)
            if item["question"]:
                rows.append(item)

    return rows


def filter_vignettes(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    kept = []
    seen = set()

    for row in rows:
        q = row["question"]
        if not is_clinical_vignette(q):
            continue

        key = q.lower()
        if key in seen:
            continue
        seen.add(key)

        kept.append(row)

    return kept


def to_triage_record(row: Dict[str, Any], new_id: int) -> Dict[str, Any]:
    """
    Keep the output simple for now.
    Gold labels for triage are not created here yet.
    This file is just the fixed dataset split to use later
    for zero-shot / few-shot / agentic evaluation prep.
    """
    return {
        "case_id": f"triage_case_{new_id:04d}",
        "source_dataset": row["source_dataset"],
        "source_id": row["source_id"],
        "initial_case": row["question"],
        "mcq_options": row["options"],
        "gold_answer_text": row["answer_text"],
        "gold_answer_index": row["answer_index"],
        "subject": row["subject"],
        "topic": row["topic"],
        # placeholders for later manual / semi-auto annotation
        "gold_summary": None,
        "gold_followup_answers": None,
        "notes": "",
    }


def save_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=str, default="triage_eval_data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--total_samples", type=int, default=1200)
    parser.add_argument("--train_size", type=int, default=1000)
    parser.add_argument("--val_size", type=int, default=100)
    parser.add_argument("--test_size", type=int, default=100)
    args = parser.parse_args()

    assert args.train_size + args.val_size + args.test_size == args.total_samples, \
        "train + val + test must equal total_samples"

    os.makedirs(args.output_dir, exist_ok=True)
    random.seed(args.seed)

    print("Loading MedMCQA...")
    medmcqa_rows = load_and_normalize_medmcqa()
    print(f"Raw MedMCQA rows: {len(medmcqa_rows)}")

    print("Loading MedQA...")
    medqa_rows = load_and_normalize_medqa()
    print(f"Raw MedQA rows: {len(medqa_rows)}")

    all_rows = medmcqa_rows + medqa_rows
    print(f"Combined raw rows: {len(all_rows)}")

    filtered_rows = filter_vignettes(all_rows)
    print(f"Filtered clinical-vignette rows: {len(filtered_rows)}")

    if len(filtered_rows) < args.total_samples:
        raise ValueError(
            f"Not enough filtered rows: found {len(filtered_rows)}, "
            f"need at least {args.total_samples}"
        )

    random.shuffle(filtered_rows)
    sampled_rows = filtered_rows[: args.total_samples]

    triage_rows = [
        to_triage_record(row, i + 1)
        for i, row in enumerate(sampled_rows)
    ]

    train_rows = triage_rows[: args.train_size]
    val_rows = triage_rows[args.train_size : args.train_size + args.val_size]
    test_rows = triage_rows[args.train_size + args.val_size :]

    print(f"Train: {len(train_rows)}")
    print(f"Val:   {len(val_rows)}")
    print(f"Test:  {len(test_rows)}")

    # save jsonl
    save_jsonl(os.path.join(args.output_dir, "train.jsonl"), train_rows)
    save_jsonl(os.path.join(args.output_dir, "val.jsonl"), val_rows)
    save_jsonl(os.path.join(args.output_dir, "test.jsonl"), test_rows)

    # save csv too
    pd.DataFrame(train_rows).to_csv(os.path.join(args.output_dir, "train.csv"), index=False)
    pd.DataFrame(val_rows).to_csv(os.path.join(args.output_dir, "val.csv"), index=False)
    pd.DataFrame(test_rows).to_csv(os.path.join(args.output_dir, "test.csv"), index=False)

    # save small stats
    stats = {
        "seed": args.seed,
        "total_samples": args.total_samples,
        "train_size": len(train_rows),
        "val_size": len(val_rows),
        "test_size": len(test_rows),
        "raw_medmcqa": len(medmcqa_rows),
        "raw_medqa": len(medqa_rows),
        "raw_total": len(all_rows),
        "filtered_total": len(filtered_rows),
        "train_dataset_counts": pd.DataFrame(train_rows)["source_dataset"].value_counts().to_dict(),
        "val_dataset_counts": pd.DataFrame(val_rows)["source_dataset"].value_counts().to_dict(),
        "test_dataset_counts": pd.DataFrame(test_rows)["source_dataset"].value_counts().to_dict(),
    }

    with open(os.path.join(args.output_dir, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"\nSaved outputs to: {args.output_dir}")


if __name__ == "__main__":
    main()