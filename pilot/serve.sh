#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_MODELS="$PWD/.local/models"
if [ "${1:-}" = '--cpu' ]; then
  export LLAMA_ARG_DEVICE=none LLAMA_ARG_N_GPU_LAYERS=0 LLAMA_ARG_KV_OFFLOAD=0
fi
if [ -x .local/ollama/ollama ]; then
  exec .local/ollama/ollama serve
else
  exec ollama serve
fi
