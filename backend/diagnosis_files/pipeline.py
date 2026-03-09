import os
# ==========================================
# 0. ENVIRONMENT SETUP (MUST BE AT THE ABSOLUTE TOP)
# ==========================================
# Secure the GPU bag
os.environ["CUDA_VISIBLE_DEVICES"] = "3,4,5"
os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")

import torch
import requests
from bs4 import BeautifulSoup
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel

# RAG imports
from langchain_community.vectorstores import FAISS
from langchain_huggingface.embeddings import HuggingFaceEmbeddings

# Agent imports
from langchain_groq import ChatGroq
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

# ==========================================
# 1. BRAIN 1: THE LOCAL RAG DIAGNOSTICIAN (BioMistral)
# ==========================================
print("Loading Local BioMistral Brain for RAG...")

# Load fine-tuned model from backup folder
model_path = "/backup/abborra/medflow_models/biomistral-medical-lora.v4"
tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Assuming weights are fully merged into the base model!
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    dtype=torch.float16,  
    device_map="auto",
    local_files_only=True,
    low_cpu_mem_usage=True
)

# Strict text pipe to prevent yapping
text_pipe = pipeline(
    "text-generation", 
    model=model, 
    tokenizer=tokenizer, 
    max_new_tokens=100,
    max_length=None,
    do_sample=False,
    return_full_text=False
)

# ==========================================
# 2. LOAD VECTOR DATABASE FOR RAG
# ==========================================
print("Loading FAISS Vector Database...")
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)

# Load vector database from backup folder
vector_db = FAISS.load_local(
    "/backup/abborra/medflow_models/medical_vectordb",
    embedding_model,
    allow_dangerous_deserialization=True
)

retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# ==========================================
# 3. RAG DIAGNOSIS FUNCTION
# ==========================================
def diagnose_with_rag(patient_case: str) -> str:
    """Use Local BioMistral RAG to identify diagnosis from patient case."""
    print("\n[*] Brain 1 (BioMistral) is analyzing the symptoms...")
    
    try:
        docs = retriever.invoke(patient_case)
        context = "\n\n".join([d.page_content for d in docs])
        
        prompt = f"""<s>[INST] You are an elite clinical diagnosis assistant.

Patient case:
{patient_case}

Relevant medical history database:
{context}

Based on the symptoms and database, determine the most likely diagnosis. Provide ONLY the primary diagnosis name. [/INST]
"""

        result = text_pipe(prompt)
        diagnosis = result[0]["generated_text"].strip()
        return diagnosis
    except Exception as e:
        print(f"❌ RAG Diagnosis Error: {e}")
        return "Unknown diagnosis"

# ==========================================
# 4. BRAIN 2: THE GROQ TOOL-CALLING AGENT 
# ==========================================
print("Loading Groq API Brain for Tool Calling...")

@tool
def search_drugs_com(diagnosis: str) -> str:
    """Use this tool to search drugs.com for medical facts and medications."""
    print(f"\n🚨 [TOOL ACTIVATED] Groq is searching Drugs.com for: {diagnosis} 🚨")
    search_url = "https://www.drugs.com/search.php"
    params = {"searchterm": diagnosis + " medication"} 
    
    # The fucking fix: Add a browser User-Agent
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Pass the headers into the get request
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            clean_text = soup.get_text(separator=' ', strip=True)
            return clean_text[:2000] 
        else:
            return f"Tool failed. The website blocked the request. Status code: {response.status_code}"
    except Exception as e:
        return f"Tool crashed with error: {str(e)}"

# Initialize the Sigma Tool Caller
groq_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# The native tool-calling prompt
agent_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert medical assistant. Use your tools to find standard treatments. Return a clean list of top medications."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(groq_llm, [search_drugs_com], agent_prompt)
agent_executor = AgentExecutor(agent=agent, tools=[search_drugs_com], verbose=True)

# ==========================================
# 5. THE MASTER PIPELINE EXECUTION
# ==========================================
def run_med_flow_pipeline(patient_case: str):
    print("\n" + "="*50)
    print("MED-FLOW: TWO-BRAIN ARCHITECTURE INITIATED")
    print("="*50)
    print(f"Patient Symptoms:\n{patient_case}")
    
    # Phase 1: Local Model Diagnosis
    diagnosis = diagnose_with_rag(patient_case)
    print(f"\n[+] BioMistral Diagnosis Secured: {diagnosis.upper()}")
    
    # Phase 2: Cloud Agent Treatment Research
    print("\n[*] Handing off to Brain 2 (Groq) for treatment research...")
    
    try:
        treatment_response = agent_executor.invoke({
            "input": f"The patient was just diagnosed with '{diagnosis}'. Search the database and list the top 3-5 standard medications prescribed for this."
        })
        
        print("\n" + "="*50)
        print("FINAL CLINICAL OUTPUT")
        print("="*50)
        print(f"Diagnosis: {diagnosis.upper()}")
        print(f"\nTreatment Plan:\n{treatment_response['output']}")
        print("="*50)
        
        return {
            "diagnosis": diagnosis,
            "treatment": treatment_response['output']
        }
    except Exception as e:
        print(f"❌ Treatment search error: {e}")
        print(f"\n[FALLBACK] Diagnosis: {diagnosis.upper()}")
        return {"diagnosis": diagnosis, "treatment": f"Error retrieving treatment: {e}"}

if __name__ == "__main__":
    test_cases = [
        """Patient: 67M
Symptoms: cough, fever, shortness of breath, chest pain
Known history: hypertension""",
        
        """Patient: 25M
Symptoms: sharp pain in right lower abdomen, nausea, low fever
Known history: none""",
        
        """Patient: 45F
Symptoms: chest pain, sweating, shortness of breath
Known history: diabetes"""
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🧪 TEST CASE {i}")
        result = run_med_flow_pipeline(test_case)
        print(f"✅ Case {i} completed\n")