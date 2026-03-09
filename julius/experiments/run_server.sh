#!/bin/bash
python3 -m vllm.entrypoints.openai.api_server \
    --model BioMistral/BioMistral-7B-DARE \
    --port 8001 \
    --trust-remote-code \
    --gpu-memory-utilization 0.9 \
    --dtype float16
