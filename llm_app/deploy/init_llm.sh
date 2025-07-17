#!/bin/bash

pip install --timeout=50 --retries=20 --break-system-packages vllm==0.6.4.post1
vllm serve models/Vikhr/Vikhr-Llama3.1-8B-Instruct-R-21-09-24.Q5_K_M.gguf --max_model_len="${MAX_MODEL_LEN}" --port 8001 --tokenizer models/Vikhr &
vllm serve models/ai-forever/ --port 8002 --task embedding &
wait
