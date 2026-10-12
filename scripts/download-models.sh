#!/usr/bin/env bash
# Download the Qwen-Image-2.1-Turbo model set for stable-diffusion.cpp.
#
# Produces, in ./models (override with MODELS_DIR):
#   - denoiser  : AtomicChat Turbo GGUF            (Q8_0 by default)
#   - encoder   : AtomicChat abliterated Qwen3-VL  (Q8_0 by default)
#   - mmproj    : vision projector for editing     (F16)
#   - vae       : Comfy-Org qwen_image_2.1 VAE     (bf16)
#
# Usage:
#   ./scripts/download-models.sh                 # Q8_0 denoiser + encoder
#   DENOISER=AD-Q4_K ./scripts/download-models.sh  # smaller quant
#   MODELS_DIR=/path/to/models ./scripts/download-models.sh
set -euo pipefail

MODELS_DIR="${MODELS_DIR:-models}"
DENOISER_QUANT="${DENOISER_QUANT:-Q8_0}"        # Q8_0 | AD-Q4_K | AD-Q5_K | AD-Q6_K | BF16
ENCODER_QUANT="${ENCODER_QUANT:-Q8_0}"          # Q8_0 | AD-Q4_K | ...

HF="https://huggingface.co"
DENOISER_REPO="AtomicChat/Qwen-Image-2.1-Turbo-GGUF"
ENCODER_REPO="AtomicChat/Qwen-Image-2.1-Turbo-Uncensored-GGUF"
VAE_REPO="Comfy-Org/Qwen-Image-2.1"

mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

fetch() { # fetch <url> <outfile>  — resumes, and verifies size against the server's Content-Length
  local url="$1" out="$2" expected actual
  expected=$(curl -sIL "$url" | grep -i '^content-length:' | tail -1 | tr -dc '0-9')
  if [[ -n "${expected:-}" && -f "$out" ]]; then
    actual=$(wc -c < "$out")
    if [[ "$actual" == "$expected" ]]; then
      echo "  [skip] $out (complete, $actual bytes)"
      return
    fi
    echo "  [resume] $out ($actual/$expected bytes)"
  else
    echo "  [get ] $out"
  fi
  curl -L --fail --retry 5 --retry-delay 3 -C - -o "$out" "$url"
  if [[ -n "${expected:-}" ]]; then
    actual=$(wc -c < "$out")
    [[ "$actual" == "$expected" ]] || { echo "  [FAIL] $out incomplete ($actual/$expected)" >&2; exit 1; }
  fi
}

echo "Denoiser : ${DENOISER_QUANT}"
fetch "$HF/$DENOISER_REPO/resolve/main/Qwen-Image-2.1-Turbo-${DENOISER_QUANT}.gguf" \
      "Qwen-Image-2.1-Turbo-${DENOISER_QUANT}.gguf"

echo "Encoder  : ${ENCODER_QUANT}"
fetch "$HF/$ENCODER_REPO/resolve/main/Qwen-Image-2.1-Turbo-Abliterated-Uncensored-${ENCODER_QUANT}.gguf" \
      "Qwen-Image-2.1-Turbo-Abliterated-Uncensored-${ENCODER_QUANT}.gguf"

echo "mmproj   : F16"
fetch "$HF/$ENCODER_REPO/resolve/main/mmproj-Qwen-Image-2.1-Turbo-Abliterated-Uncensored-F16.gguf" \
      "mmproj-Qwen-Image-2.1-Turbo-Abliterated-Uncensored-F16.gguf"

echo "VAE      : bf16"
fetch "$HF/$VAE_REPO/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors" \
      "qwen_image_2.1_vae_bf16.safetensors"

echo
echo "Done. Files in $MODELS_DIR:"
ls -lh *.gguf *.safetensors 2>/dev/null || true
