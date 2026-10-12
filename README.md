# Qwen-Image-2.1-Turbo on stable-diffusion.cpp

Self-contained docker-compose stack for running [Qwen-Image-2.1-Turbo](https://huggingface.co/AtomicChat/Qwen-Image-2.1-Turbo-GGUF) (uncensored / abliterated GGUFs) with [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp) — image generation **and** editing from a single GPU, plus an experimental feature to offload the text encoder to a second machine over your LAN.

```
web frontend (vanilla JS, no CDN)
        |
api-gateway  :3000   FastAPI proxy + prompt-assist + job polling
        |
sd-server    :8080   stable-diffusion.cpp HTTP server (CUDA, 1 GPU)
        |            denoiser Q8_0 + abliterated encoder Q8_0 + VAE bf16
        |
encoder-worker :8081  [optional] llama.cpp on a remote 8GB box
```

## Requirements

- Docker with the NVIDIA Container Toolkit (`docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi` must work)
- One CUDA GPU with ≥ 24 GB VRAM for full local mode (Q8_0 denoiser + Q8_0 encoder + VAE fit in ~17 GB). The `sm_120` build args target Blackwell (RTX 5090); adjust `CUDA_ARCHITECTURES` in `docker-compose.yml` for other cards.
- ~17 GB of free disk for the model weights.

## Quick start

```bash
git clone --recurse-submodules https://github.com/SPhillips1337/qwen-image2.1.git
cd qwen-image2.1
./scripts/download-models.sh          # fetches all 4 GGUFs into models/ (resumable)
docker compose up -d --build
```

Then open **http://localhost:3000** for the web UI, or hit the API directly:

```bash
curl -X POST http://localhost:3000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"a red panda drinking tea at a tiny wooden cafe","width":1024,"height":1024}'
# -> {"job_id":"job_...","poll_url":"/api/jobs/job_..."}

curl http://localhost:3000/api/jobs/<job_id>   # status / progress / image URL
```

Images land in `output/`. The Turbo schedule (8 steps, CFG 1.0, euler, the fixed sigma list) is baked into the gateway — no need to pass sampler flags. On a 5090 Laptop expect ~45 s per 1024×1024 image end-to-end.

### API surface

| Endpoint | Purpose |
|---|---|
| `POST /api/generate` | Text-to-image job (async, poll for result) |
| `POST /api/edit` | Image edit: multipart upload + instruction prompt |
| `GET  /api/jobs/{id}` | Job status, live progress, output URL |
| `POST /api/prompt-assist` | Expand a rough idea into a detailed prompt via gemma-4-e2b (optional) |
| `GET  /api/capabilities` | Model + sampler info from sd-server |

sd-server itself also exposes the full OpenAI-compatible API (`/v1/images/generations`, `/v1/images/edits`) and its native job API on port 8080 if you want to skip the gateway.

## Models

Downloaded by `scripts/download-models.sh` into `models/`:

| File | Source | Size |
|---|---|---|
| `Qwen-Image-2.1-Turbo-Q8_0.gguf` (denoiser) | AtomicChat/Qwen-Image-2.1-Turbo-GGUF | 7.6 GB |
| `Qwen-Image-2.1-Turbo-Abliterated-Uncensored-Q8_0.gguf` (text encoder) | AtomicChat/Qwen-Image-2.1-Turbo-Uncensored-GGUF | 8.7 GB |
| `mmproj-...-F16.gguf` (vision projector, for edits) | same repo | 1.2 GB |
| `qwen_image_2.1_vae_bf16.safetensors` | Comfy-Org/Qwen-Image-2.1 | 0.7 GB |

The script is resumable and verifies every file against its Content-Length before declaring success. Set `HUGGING_FACE_HUB_TOKEN` in `.env` if a repo requires auth.

## Offloading the text encoder (experimental)

The encoder runs once per generation (~16 s on the 5090). If you have an idle GPU box, you can run it there via llama.cpp and ship only the ~few-MB hidden-state tensor back over LAN. The denoiser always stays local: per-step activations over a network would kill the sampling loop.

Status (2026-10-12): **deferred**. A source trace showed stock stable-diffusion.cpp has no way to inject precomputed LLM hidden states for Qwen-Image-2.1 — `token_embed_custom` is the CLIP conditioner's custom-words path only, and the LLM conditioner always runs its own encoder. Offload therefore needs a small maintained patch to sd.cpp (encode-only dump + inject of the post-processed conditioning tensor), which keeps parity by construction. The design is documented in ROADMAP.md; the single-5090 product above works without it.

The `encoder-worker` service in `docker-compose.yml` is stubbed out (commented). To try it: run a worker on the remote box with the **identical** encoder GGUF (parity matters — different quants give different hidden states and drifted images), then set `OFFLOAD_WORKERS=http://<host>:8081` in `.env` before `docker compose up`.

## Project layout

```
sd-cpp/    stable-diffusion.cpp submodule (pinned commit; the Dockerfile.cuda is built with Blackwell args)
gateway/   FastAPI gateway (Dockerfile, main.py, requirements.txt)
web/       frontend: index.html, css/, js/ — no build step, no CDN
scripts/   download-models.sh
models/    weights (gitignored, populated by the downloader)
output/    generated images (gitignored)
```

## License

MIT — see [LICENSE](LICENSE). Model weights are governed by their respective upstream repos.
