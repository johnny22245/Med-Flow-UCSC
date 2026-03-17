"""
Using this module we will pass any path for LLM artifacts.
This uses the GPUs wisely and allocates available memory to host the models and run inference.
"""

## DO NOT CHANGE ANY CODE HERE.


from vllm import LLM, SamplingParams
from collections import defaultdict
import re
import json
import os
import ast
os.environ["CUDA_VISIBLE_DEVICES"] = "2,3" 
# decoding strategy

from vllm.sampling_params import GuidedDecodingParams
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, conint, ValidationError


class DistributedModel():
    # default set to run for zero-shot as per industry and research standard
    # for Ablation study make sure to change (temperature, top_p & random seed) this randomly (discuss to find how to change.)
    def __init__(self, model_artifacts, temperature = 0.0, top_p = 1, max_new_tokens=1024, gpu_memory_utilization = 0.9):
        # Define sampling parameters
        self.sampling_params = SamplingParams(temperature=temperature, top_p=top_p, max_tokens=max_new_tokens)
        self.parallel_processes = 2
        self.llm = LLM(model = model_artifacts,
                       tensor_parallel_size = self.parallel_processes,
                       gpu_memory_utilization = gpu_memory_utilization
                       )
    
    # generate output
    def generate(self, prompt_dictionary):
        result_dict = {}
        key_list = list(prompt_dictionary.keys())
        prompt_list = list(prompt_dictionary.values())
        result_list = self.llm.generate(prompt_list, self.sampling_params)
        for i, output in enumerate(result_list):
            result_dict[key_list[i]] = output.outputs[0].text
        return result_dict
    
    