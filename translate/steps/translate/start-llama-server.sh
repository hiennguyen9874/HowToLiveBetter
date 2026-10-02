#!/usr/bin/env bash
# Hy-MT2 Q8 llama-server for sequential unit translation (CUDA or Metal).
# One slot avoids splitting the context budget between concurrent requests.
set -euo pipefail

MODEL="${HTLB_LLAMA_MODEL:-$HOME/models/Hy-MT2-30B-A3B-GGUF/Hy-MT2-30B-A3B-Q8_0.gguf}"
LLAMA_CPP="${HTLB_LLAMA_CPP:-$HOME/llama.cpp}"
HOST="${HTLB_LLAMA_HOST:-127.0.0.1}"
PORT="${HTLB_LLAMA_PORT:-8080}"
# Locked default — override only with HTLB_LLAMA_CTX if experimenting
CTX="${HTLB_LLAMA_CTX:-16384}"
SLOTS="${HTLB_LLAMA_SLOTS:-1}"

if [[ -x "$LLAMA_CPP/build/bin/llama-server" ]]; then
  SERVER=("$LLAMA_CPP/build/bin/llama-server")
elif command -v llama >/dev/null 2>&1; then
  SERVER=(llama server)
else
  echo "llama-server not found under $LLAMA_CPP or via llama on PATH" >&2
  exit 1
fi
if [[ ! -f "$MODEL" ]]; then
  echo "model not found: $MODEL" >&2
  exit 1
fi

if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "port $PORT busy — kill existing listener first" >&2
  exit 1
fi

exec "${SERVER[@]}" \
  -m "$MODEL" \
  --host "$HOST" --port "$PORT" \
  -ngl 99 \
  -fa on \
  -c "$CTX" \
  -b 512 -ub 512 \
  -np "$SLOTS" \
  --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja
