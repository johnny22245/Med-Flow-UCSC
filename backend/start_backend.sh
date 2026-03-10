export MEDFLOW_LLAVA_ENV=llava_med
export MEDFLOW_LLAVA_RUNNER=/home/achowd10/MedFlow-244-Project/Med-Flow-UCSC/backend/LlavaMed-Unet/run_llava_med_summary.py

VLLM_WORKER_MULTIPROC_METHOD=spawn uvicorn app.main:app --host 0.0.0.0 --port 24400