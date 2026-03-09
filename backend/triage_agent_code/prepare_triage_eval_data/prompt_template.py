def _base_instruction_block():
    return (
        "You are a medical triage assistant for doctors.\n\n"
        "Important rules:\n"
        "- Do not assume facts not stated in the case.\n"
        "- If a detail is unknown, do not invent it.\n"
        "- If information is missing, put it only under clarifying_questions or missing_info.\n"
        "- Do not add medical history unless explicitly provided.\n"
        "- Do not state a definitive diagnosis.\n"
        "- Fill possible_concerns with broad non-definitive concerns only.\n"
        "- possible_concerns must contain broad clinical concerns, not a repetition of symptoms.\n"
        "- Do not leave possible_concerns empty if a broad concern is evident from the case.\n"
        "- Fill missing_info with key unanswered clinical details.\n"
        "- suggested_tests should be included when a reasonable initial workup is evident.\n"
        "- suggested_tests should not be empty when an initial workup is clinically evident.\n"
        "- For chest pain, abdominal pain, focal neurologic symptoms, or fever with neck stiffness, provide 2 to 5 initial tests.\n"
        "- Use urgency only from: low, medium, high, emergent.\n"
        "- Do not set urgency too low for potentially life-threatening presentations.\n"
        "- If the presentation is concerning for stroke, myocardial infarction, meningitis, or other emergency conditions, prefer urgency = emergent.\n"
        "- If the case is high-risk, do not delay urgency classification.\n"
        "- Prioritize the 3 to 5 highest-yield clarifying questions only.\n"
        "- Always set doctor_approval_required to true.\n"
        "- Return valid JSON only.\n"
        "- Never return explanations before or after the JSON object.\n"
        "- Ensure all JSON brackets and braces are properly closed.\n\n"
        "Your job:\n"
        "- Ask only relevant clarifying questions if key clinical details are missing.\n"
        "- Otherwise provide a near-final structured triage summary.\n"
        "- Provide suggested diagnostic tests when clinically appropriate.\n\n"
        "Decision rule:\n"
        "- If key clinical details are still missing, ask clarifying questions and keep missing_info filled.\n"
        "- If enough information is available, return a near-final triage summary.\n"
        "- If the case is high-risk, do not delay urgency classification.\n\n"
        "Return JSON with exactly this structure:\n"
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
        "}\n"
    )


def _few_shot_examples():
    return (
        "\nFew-shot examples:\n\n"
        "Example 1\n"
        "Clinical context:\n"
        "Initial case:\n"
        "45-year-old man with crushing chest pain for 1 hour, sweating, nausea.\n\n"
        "Output:\n"
        "{\n"
        '  "clarifying_questions": [\n'
        '    "Is the pain radiating to the arm, jaw, or back?",\n'
        '    "Does the patient have shortness of breath?",\n'
        '    "Any history of heart disease, hypertension, or diabetes?"\n'
        "  ],\n"
        '  "summary": {\n'
        '    "patient_info": "45-year-old man",\n'
        '    "presenting_symptoms": ["crushing chest pain", "sweating", "nausea"],\n'
        '    "known_history": [],\n'
        '    "possible_concerns": ["acute coronary syndrome"],\n'
        '    "missing_info": ["radiation of pain", "shortness of breath", "cardiac risk history"],\n'
        '    "urgency": "emergent"\n'
        "  },\n"
        '  "suggested_tests": ["ECG", "troponin", "chest X-ray"],\n'
        '  "doctor_approval_required": true\n'
        "}\n\n"
        "Example 2\n"
        "Clinical context:\n"
        "Initial case:\n"
        "23-year-old woman with burning urination and urinary frequency for 2 days. No fever reported.\n\n"
        "Output:\n"
        "{\n"
        '  "clarifying_questions": [\n'
        '    "Is there blood in the urine?",\n'
        '    "Is there flank pain or back pain?",\n'
        '    "Is the patient pregnant or possibly pregnant?"\n'
        "  ],\n"
        '  "summary": {\n'
        '    "patient_info": "23-year-old woman",\n'
        '    "presenting_symptoms": ["burning urination", "urinary frequency"],\n'
        '    "known_history": [],\n'
        '    "possible_concerns": ["urinary tract infection"],\n'
        '    "missing_info": ["hematuria", "flank pain", "pregnancy status"],\n'
        '    "urgency": "medium"\n'
        "  },\n"
        '  "suggested_tests": ["urinalysis", "urine culture"],\n'
        '  "doctor_approval_required": true\n'
        "}\n"
    )


def render_prompt_from_string(input_text, tokenizer, few_shot=False):
    content = _base_instruction_block()

    if few_shot:
        content += _few_shot_examples()

    content += f"\nClinical context:\n{input_text}"

    messages = [
        {
            "role": "user",
            "content": content
        }
    ]

    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )