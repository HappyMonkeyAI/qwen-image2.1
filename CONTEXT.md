# CONTEXT.md — qwen-image2.1

## Stack / nature

Docker-compose product for running **Qwen-Image-2.1-Turbo** (uncensored/abliterated GGUFs) via **stable-diffusion.cpp** on a single RTX 5090 (Blackwell, sm_120), with an optional experimental feature to offload the text encoder to a second machine over LAN. Not a ComfyUI port — Path B was chosen deliberately for self-containment and shareability.

Services:

| Service | Image | Port | Role |
|---|---|---|---|
| `sd-server` | built from `sd-cpp/docker/Dockerfile.cuda` (CUDA 12.8, arch 120) | 8080 | stable-diffusion.cpp HTTP server: OpenAI-compatible + native async job API + embedded UI |
| `api-gateway` | `gateway/Dockerfile` (python:3.12-slim, FastAPI) | 3000 | **API-only** proxy for sd-server async API, bakes in Turbo schedule, prompt-assist via gemma-4-e2b — no frontend of its own; the web UI is sd-server's native embedded sdcpp-webui on :8080 |
| `encoder-worker` | llama.cpp (stubbed, commented out) | 8081 | optional remote text encoder for offload experiment |

Models live in `models/` (gitignored; ~17 GB, fetched by `scripts/download-models.sh`). Generated images land in `output/`.

## Architecture decisions

| ADR | Summary |
|-----|---------|
| [ADR-0001](docs/adr/0001-verification-ladder-and-owner-adversary.md) | Verification Ladder V0–V4 + Owner-as-Adversary before Done/Ratchet. Worker self-report ≠ proof. |
| [ADR-0002](docs/adr/0002-isolated-worktrees-and-evidence-handoffs.md) | Branch/worktree mode for parallel work; context packs; evidence handoffs. |
| [ADR-0003](docs/adr/0003-mcp-intent-map-and-bootstrap-discovery.md) | `MCP.md` intent routing + bootstrap discovery → `MCP.local.md`. Listed ≠ mounted. |
| [ADR-0004](docs/adr/0004-adaptive-model-escalation.md) | Provider-neutral model escalation after evidence of structural failure; Pulse is the stop/replan boundary. |

Project-specific decisions (full rationale in `.agent/memories/architectural_decisions/`):

- **Path B: stable-diffusion.cpp directly, not ComfyUI.** The HF repo ships GGUFs for sd.cpp, not safetensors; Stability Matrix packages are Python A1111 forks that can't load them. One binary + 4 model files = a shareable docker-compose package.
- **Offload is a feature, not a requirement.** Single 5090 runs everything locally (Q8_0 denoiser 7.6 GB + Q8_0 encoder 8.7 GB + VAE 0.7 GB fit in 24 GB). Offloading the *text encoder only* (one-shot, ~few-MB hidden-state tensor over LAN) is the experiment; the denoiser always stays local because per-step activation shipping would kill sampling latency.
- **Offload needs a maintained sd.cpp patch (Phase 3, deferred by user).** Source trace 2026-10-12: stock sd.cpp has *no* LLM hidden-state injection — `token_embed_custom`/`--embd-dir` are the CLIP conditioner's A1111 custom-words path (SD1/2/SDXL only), and the Qwen LLM conditioner unconditionally runs `llm->compute()`. The viable design is a small patch branch adding encode-only dump + inject of the post-processed `c_crossattn` tensor, keeping parity *by construction*. Parity requirement: remote worker must run the *identical* encoder GGUF or images drift.
- **Build inside Docker.** No MSVC C++ workload or CUDA toolkit on the Windows laptop; the same `Dockerfile.cuda` with `--build-arg CUDA_VERSION=12.8.0 --build-arg CUDA_ARCHITECTURES=120` is the shareable artifact.
- **sd-cpp pinned as a git submodule** at commit 792bcd3 (the exact revision our verified image was built from), not vendored into this repo.

## Rules (high signal)

- Turbo schedule is fixed and baked into the gateway: 8 steps, CFG 1.0, euler, sigmas `1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0`. Do not "improve" it per-request without an ADR.
- `--entrypoint ""` is mandatory when invoking `/sd-cli` or `/sd-server` directly in the image — the ENTRYPOINT conflicts with the wrapper script.
- Q8_0 for both denoiser and encoder (picture fidelity; fits 24 GB). AD-Q4_K (5.3 GB) is the fallback quant for 8 GB remote workers.
- Unsloth's clean-base Dynamic GGUFs are NOT drop-in replacements for AtomicChat's Turbo/abliterated quants — they lack distillation and the abliterated behavior. Phase-4 benchmark material only.
- HF xet storage rejects `Range` resume headers: on truncation, delete and re-download fresh (with auth token if needed) rather than resuming.
- Verify model file sizes against the HF API (`/api/models/<repo>/tree/main`) — README scrapes have gone stale twice in this project.

## What not to do

- Don't commit `models/`, `output/`, `.env` (HF token), or `ref-frontend/`.
- Don't attempt layer-level denoiser splitting across machines — the KSampler loop is a tight per-step dependency chain; LAN round-trips swamp any VRAM saving.
- Don't point the gateway at a worker running a different encoder quant and expect parity.
- Don't use Stability Matrix / SD WebUI forks for this model — wrong weight format.
- Don't skip V0 (docker build + smoke generation) before claiming a stack change works.

## Research

- `research/LINKS.md` — upstream repos, HF model pages, Unsloth docs.
