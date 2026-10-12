# Codebase insights — qwen-image2.1

## gateway/main.py (FastAPI)
- Proxies sd-server's native async job API (`/sdcpp/v1/img_gen`) rather than the OpenAI-compatible endpoints, because the async API gives live progress previews and cancel — clients poll `/api/jobs/{id}` on a 3 s cadence.
- The Turbo sigma schedule `1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0` is baked in as a constant with 8 steps / CFG 1.0 / euler — do not parameterize it casually (see CONTEXT.md rules).
- `/api/edit` is multipart (`UploadFile`) → requires `python-multipart`; forgetting it crashes the whole app at import time, not at request time. It calls `_image_dims()` (stdlib PNG IHDR / JPEG SOF reader) and forwards the upload's real width/height — without that sd-server silently falls back to 512×512 and edits get downscaled. `import struct` must sit at the TOP of `_image_dims()`, not inside one branch: a branch-local import makes the name unbound in the other branch (`UnboundLocalError` → 500 on every JPEG upload).
- API-only: no frontend of its own (the `web/` directory was removed). The web UI is sd-server's native embedded sdcpp-webui on :8080 — it has a **Reference Images** section that maps to `ref_images[]`, which is the field that triggers EDIT mode for Qwen-Image 2.1 ("Init Image" is the img2img-denoise control and is ignored by this model family). The gateway's `/` route just returns a JSON pointer to :8080.
- `GEMMA_URL` env (default `http://host.docker.internal:1234/v1`) backs `/api/prompt-assist`; `OFFLOAD_WORKERS` env is read but Phase 3 routing is not implemented yet.

## sd-server container (sdcpp-cuda:5090)
- Built from `sd-cpp/docker/Dockerfile.cuda` @ submodule commit 792bcd3 with CUDA 12.8 / arch 120 build args. The image ENTRYPOINT conflicts with direct binary invocation — every call needs `--entrypoint ""` (compose sets `entrypoint: ""`).
- All four models are mounted read-only at `/models`; the server loads denoiser + abliterated encoder + VAE + mmproj (`--llm_vision`) at boot. Capabilities endpoint reports mode `img_gen`.
- Port 8080 exposes three API families: OpenAI-compatible (`/v1/images/generations`, `/v1/images/edits`), A1111 sdapi, and the native async job API (`/sdcpp/v1/img_gen`) — the gateway uses only the last.

## scripts/download-models.sh
- Resumable downloader with `DENOISER_QUANT` / `ENCODER_QUANT` env selection. Completeness is checked against Content-Length fetched via `curl -sIL`, NOT file non-emptiness (that bug caused a phantom "incomplete encoder" chase).
- HF xet storage rejects Range resume → on truncation the script deletes and re-downloads fresh; auth token from `.env` (`HUGGING_FACE_HUB_TOKEN`) when a repo requires it.

## models/ sizes (authoritative, verified against HF API 2026-10-12)
- denoiser Q8_0: 7,591,554,784 B · encoder Q8_0: 8,709,520,096 B · mmproj F16: 1,159,029,984 B · VAE bf16: 675,509,688 B. README scrapes have been wrong twice — trust the API.

## Offload seam (upstream sd.cpp) — CORRECTED 2026-10-12
- `token_embed_custom` is the CLIP conditioner's A1111 custom-words path only, NOT an LLM injection point. The Qwen LLM conditioner's `encode_prompt()` unconditionally calls `llm->compute()` — no CLI flag, endpoint, or file-load path accepts precomputed hidden states (AD-03 superseded). Offload requires a maintained sd.cpp patch (encode-only dump + inject), deferred by user. See patterns_and_lessons.md and decisions.md.
