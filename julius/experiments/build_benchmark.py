import duckdb
import json
import random
import uuid

def build_benchmark(db_path="data/pruned_safety.duckdb", sample_size=50):
    con = duckdb.connect(db_path)
    
    print(f"📊 Extracting {sample_size} Positive and {sample_size} Negative cases...")

    try:
        # --- 1. EXTRACT POSITIVE SAMPLES (True Warnings) ---
        # Using the correct concept name columns
        pos_query = f"""
            SELECT drug_1_concept_name, drug_2_concept_name, condition_concept_name
            FROM interactions
            WHERE PRR > 10.0
            ORDER BY random()
            LIMIT {sample_size}
        """
        pos_rows = con.execute(pos_query).fetchall()
        
        pos_cases = []
        for r in pos_rows:
            pos_cases.append({
                "uuid": str(uuid.uuid4())[:8],
                "medications": [r[0], r[1]],
                "expected_status": "WARNING",
                "clinical_reason": r[2],
                "label": 1
            })

        # --- 2. EXTRACT NEGATIVE SAMPLES (All Clear) ---
        # Get a pool of unique drugs to mix and match
        drug_pool_query = "SELECT DISTINCT drug_1_concept_name FROM interactions"
        all_drugs = [r[0] for r in con.execute(drug_pool_query).fetchall()]
        
        neg_cases = []
        while len(neg_cases) < sample_size:
            d1, d2 = random.sample(all_drugs, 2)
    
            # This query finds the MAXIMUM PRR for this specific pair.
            # If it's NULL (pair doesn't exist) or < 2.0, we call it safe.
            check_query = """
                SELECT MAX(PRR)
                FROM interactions 
                WHERE drug_1_concept_name = ? AND drug_2_concept_name = ?
            """
            max_prr = con.execute(check_query, [d1, d2]).fetchone()[0]
        
            # Logic: It's a 'Safe' case if the highest signal is very weak or non-existent
            if max_prr is None or max_prr < 2.0:
                neg_cases.append({
                    "uuid": str(uuid.uuid4())[:8],
                    "medications": [d1, d2],
                    "expected_status": "ALL_CLEAR",
                    "clinical_reason": "No statistically significant interaction (PRR < 2.0).",
                    "label": 0
                })
        # --- 3. SAVE ---
        benchmark = pos_cases + neg_cases
        random.shuffle(benchmark)
        
        with open("benchmark_data.json", "w") as f:
            json.dump(benchmark, f, indent=2)
        
        print(f"✅ Success! Generated benchmark_data.json with {len(benchmark)} cases.")

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
    finally:
        con.close()

if __name__ == "__main__":
    build_benchmark()
