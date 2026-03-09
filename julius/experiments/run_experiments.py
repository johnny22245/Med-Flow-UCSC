import json
import csv
import duckdb
import os
from openai import OpenAI
from sklearn.metrics import precision_score, recall_score, f1_score, classification_report
import datetime
# Setup Client
client = OpenAI(base_url="http://localhost:8001/v1", api_key="EMPTY")
MODEL_NAME = "BioMistral/BioMistral-7B-DARE"
DB_PATH = "data/pruned_safety.duckdb"

# --- PROMPT TEMPLATES ---
FEW_SHOT_EXAMPLES = """
### Reference Case 1:
- Drugs: ["Aspirin", "Warfarin"]
- Result: {"status": "WARNING"}

### Reference Case 2:
- Drugs: ["Amoxicillin", "Vitamin C"]
- Result: {"status": "ALL_CLEAR"}

### Reference Case 3:
- Drugs: ["Lisinopril", "Potassium Supplement"]
- Result: {"status": "WARNING"}
"""

def get_duckdb_context(meds):
    if not os.path.exists(DB_PATH):
        return "DATABASE_STATUS: Offline. No external safety data available."
    
    try:
        # Use a context manager to ensure the connection closes even if it fails
        with duckdb.connect(DB_PATH, read_only=True) as con:
            meds_clean = [m.strip().lower() for m in meds]
            
            # Use a more robust way to format the IN clause
            # This prevents the ('drug',) trailing comma bug
            placeholders = ', '.join(['?'] * len(meds_clean))
            
            query = f"""
                SELECT condition_concept_name, PRR
                FROM interactions
                WHERE LOWER(drug_1_concept_name) IN ({placeholders})
                  AND LOWER(drug_2_concept_name) IN ({placeholders})
                  AND PRR >= 5.0
            """
            
            # Pass meds_clean twice because we use placeholders twice
            results = con.execute(query, meds_clean + meds_clean).fetchall()

        if not results:
            return "DATABASE_REPORT: No statistically significant interactions (PRR >= 5.0) detected."
        
        context = "DATABASE_REPORT: SIGNIFICANT ADVERSE INTERACTIONS DETECTED\n"
        # Limit results to top 5 to prevent prompt overflow/freezing
        for r in results[:5]: 
            context += f"- Effect: {r[0]} (PRR: {r[1]:.2f})\n"
        return context

    except Exception as e:
        return f"DATABASE_ERROR: {str(e)}"

def get_prediction(meds, strategy="zero_shot", use_rag=False):
    # Updated Instruction: Focus on Accuracy to boost Precision
    instruction = (
        "You are a Clinical Safety Analyst. Your goal is maximum ACCURACY. "
        "Issue a WARNING only if there is clear evidence of risk. "
        "If no significant interactions are found, return ALL_CLEAR."
    )
    
    components = [instruction]
    
    if strategy == "few_shot":
        components.append(f"REFERENCE GUIDELINES:\n{FEW_SHOT_EXAMPLES}")
    
    # We always include a Database section if RAG is on
    if use_rag:
        rag_context = get_duckdb_context(meds)
        components.append(f"CLINICAL DATABASE CONTEXT:\n{rag_context}")
    else:
        components.append("CLINICAL DATABASE CONTEXT:\nNo external database search was performed for this test.")

    components.append(f"PATIENT CASE: Evaluate {meds}")
    
    # Forcing a 'reason' field helps the model think before it commits to a status
    components.append(
        "Return ONLY a JSON object with 'status' and 'reason'.\n"
        "Format: {\"status\": \"WARNING\", \"reason\": \"...\"} or {\"status\": \"ALL_CLEAR\", \"reason\": \"...\"}\n"
        "Response:"
    )

    user_content = "\n\n".join(components)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": user_content}],
            temperature=0.0
        )
        raw = response.choices[0].message.content.strip()
        
        # Binary mapping: 1 for WARNING, 0 for ALL_CLEAR
        return 1 if '"STATUS": "WARNING"' in raw.upper() else 0
    except Exception as e:
        print(f"Error: {e}")
        return 0
def run_benchmark():
    with open("benchmark_data.json", "r") as f:
        test_set = json.load(f)

    results = []
    # Ground Truth and Predictions
    y_true = []
    preds = {
        "zs": [],
        "fs": [],
        "rag_zs": [],
        "rag_fs": []
    }

    print(f"🚀 Running benchmark on {len(test_set)} cases (4 configurations)...")

    for case in test_set:
        meds = case["medications"]
        label = case["label"]
        y_true.append(label)

        # Execute all 4 strategies
        p_zs = get_prediction(meds, "zero_shot", use_rag=False)
        p_fs = get_prediction(meds, "few_shot", use_rag=False)
        p_rag_zs = get_prediction(meds, "zero_shot", use_rag=True)
        p_rag_fs = get_prediction(meds, "few_shot", use_rag=True)

        preds["zs"].append(p_zs)
        preds["fs"].append(p_fs)
        preds["rag_zs"].append(p_rag_zs)
        preds["rag_fs"].append(p_rag_fs)

        results.append({
            "uuid": case.get("uuid", case.get("case_id")), # Handle either key
            "meds": str(meds),
            "true_label": label,
            "zs_pred": p_zs,
            "fs_pred": p_fs,
            "rag_zs_pred": p_rag_zs,
            "rag_fs_pred": p_rag_fs
        })

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"experiment_results_{timestamp}.csv"

    # Save to the unique CSV
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
 
    # --- FINAL METRICS PRINTING ---
    configs = [
        ("Zero-Shot (No RAG)", preds["zs"]),
        ("Few-Shot (No RAG)", preds["fs"]),
        ("RAG + Zero-Shot", preds["rag_zs"]),
        ("RAG + Few-Shot", preds["rag_fs"])
    ]
    
    print("\n" + "="*50)
    print("      FINAL COMPARATIVE EVALUATION METRICS")
    print("="*50)

    for name, y_pred in configs:
        p = precision_score(y_true, y_pred, zero_division=0)
        r = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        
        print(f"\nSTRATEGY: {name}")
        print(f"Precision: {p:.4f} | Recall: {r:.4f} | F1 Score: {f1:.4f}")
        print("-" * 30)

if __name__ == "__main__":
    run_benchmark()
