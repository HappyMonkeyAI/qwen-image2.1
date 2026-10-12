# Codebase insights — qwen-image2.1

## gateway/main.py (FastAPI)
- Proxies sd-server's native async job API (`/sdcpp/v1/img_gen`) rather than the OpenAI-compatible endpoints, because the async API gives live progress previews and cancel — the frontend polls `/api/jobs/{id}` on a 3 s cadence.
- The Turbo sigma schedule `1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0` is baked in as a constant with 8 steps / CFG 1.0 / euler — do not parameterize it casually (see CONTEXT.md rules).
- `/api/edit` is multipart (`UploadFile`) → requires `python-multipart`; forgetting it crashes the whole app at import time, not at request time.
- `GEMMA_URL` env (default `http://host.docker.internal:1234/v1`) backs `/api/prompt-assist`; `OFFLOAD_WORKERS` env is read but Phase 3 routing is not implemented yet.
- Static frontend served from `/app/web` (copied at image build from the project-root context — the Dockerfile's build context is the repo root, NOT `gateway/`).

## sd-server container (sdcpp-cuda:5090)
- Built from `sd-cpp/docker/Dockerfile.cuda` @ submodule commit 792bcd3 with CUDA 12.8 / arch 120 build args. The image ENTRYPOINT conflicts with direct binary invocation — every call needs `--entrypoint ""` (compose sets `entrypoint: ""`).
- All four models are mounted read-only at `/models`; the server loads denoiser + abliterated encoder + VAE + mmproj (`--llm_vision`) at boot. Capabilities endpoint reports mode `img_gen`.
- Port 8080 exposes three API families: OpenAI-compatible (`/v1/images/generations`, `/v1/images/edits`), A1111 sdapi, and the native async job API (`/sdcpp/v1/img_gen`) — the gateway uses only the last.

## web/ (vanilla JS frontend)
- No build step, no CDN, no jQuery: `index.html` + `css/styles.css` + `js/main.js`. Generate/Edit tabs; edit tab uploads via FormData to `/api/edit`.
- Job polling loop with a live progress bar driven by the gateway's job status endpoint.

## scripts/download-models.sh
- Resumable downloader with `DENOISER_QUANT` / `ENCODER_QUANT` env selection. Completeness is checked against Content-Length fetched via `curl -sIL`, NOT file non-emptiness (that bug caused a phantom "incomplete encoder" chase).
- HF xet storage rejects Range resume → on truncation the script deletes and re-downloads fresh; auth token from `.env` (`HUGGING_FACE_HUB_TOKEN`) when a repo requires it.

## models/ sizes (authoritative, verified against HF API 2026-10-12)
- denoiser Q8_0: 7,591,554,784 B · encoder Q8_0: 8,709,520,096 B · mmproj F16: 1,159,029,984 B · VAE bf16: 675,509,688 B. README scrapes have been wrong twice — trust the API.

## Offload seam (upstream sd.cpp)
- `sd-cpp/src/conditioning/conditioner.hpp`: LLM output = float tensor `[n_token, hidden_size]` in `c_crossattn`; the `token_embed_custom` path injects precomputed embeddings and skips the local LLM. Phase 3 needs no C++ changes — only a llama.cpp worker returning that tensor and gateway routing.
