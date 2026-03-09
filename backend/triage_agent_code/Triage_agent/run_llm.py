"""
Experiment code or details

"""

# Comment out below variable for each time of inference.
#exp_var = "Few-Shot-prompts_128" 
exp_var = "Few-Shot-prompts_test"

temperature = 0.0
top_p = 1
max_new_tokens = 1024

## DO NOT CHANGE CODE BELOW
import json
from distributed_LLM_call import DistributedModel
from prompt_template import render_prompt_from_string

import getpass
alias = getpass.getuser()

#change the paths for your local datset paths
val_data = f"test_data.json"

data_to_run = {
    "val": val_data
    }

#load Model first to save time:
model_path_dict =  {
        "bio_mistral_7B": "/home/achowd10/MedFlow_244_project/models/Bio_mistral_7B_Dare",
        "mistral_7B": "/home/achowd10/MedFlow_244_project/models/Mistral_7B_inst",
        }

#load Model first to save time:
model_path_dict_FT =  {
        }

if "Few-Shot-prompts" in exp_var:
    model_dict = model_path_dict
    few_shot_flag = True
else:
    model_dict = model_path_dict_FT
    few_shot_flag = False
    
for model_name, model_path in model_dict.items():
    model = DistributedModel(model_path, temperature=temperature, top_p=top_p, max_new_tokens=max_new_tokens)
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_path, use_fast=True)
    
    for key, data_path in data_to_run.items():
        
        #construction of prompts
        prompts = {}
        with open(data_path, 'r') as f:
            data = json.load(f)
            expected_len = {}
            
            
            for k, v in data.items():
                tokens = v
                key_prompt = f"{k}"
                prompts[key_prompt] = render_prompt_from_string(tokens, tokenizer)
                        
        # Generate model/LLMs output
        results = model.generate(prompts)
        
        # clean data
        results_cleaned = results #model.output_parser(results, expected_len)
        
        # write to path
        write_path = f"./results/{key}_{model_name}_{exp_var}.json"
        
        try:
            with open(write_path, 'w') as f:
                json.dump(results_cleaned, f, indent = 4)
        except:
            continue
    # clean up model variable to free GPU memory for next process
    del model
    
    