# SPEC.md — acceptance criteria by phase

Each criterion must have independent evidence before its task is marked Done (ADR-0001). Evidence goes in PROGRESS.md.

## Phase 1 — single-GPU baseline ✅ (evidence in PROGRESS.md)

- **S1.1** `sd-cli` builds from `Dockerfile.cuda` with CUDA 12.8 + arch 120 and loads the Qwen-Image-2.1-Turbo Q8_0 denoiser without libcuda errors.
- **S1.2** A 1024×1024 text-to-image generation completes end-to-end (encode → 8-step sample → VAE decode) producing a valid PNG.
- **S1.3** All four model files present in `models/` at their authoritative HF sizes: denoiser 7,591,554,784 B; encoder 8,709,520,096 B; mmproj F16 1,159,029,984 B; VAE bf16 675,509,688 B.
- **S1.4** Image edit path (input image + instruction via `--llm_vision` mmproj) produces a valid PNG. *(Not yet exercised — carried into Phase 2.)*

## Phase 2 — docker-compose product ✅ (evidence in PROGRESS.md)

- **S2.1** `docker compose up -d --build` brings up sd-server (:8080) and api-gateway (:3000) from a fresh clone + downloader run.
- **S2.2** Gateway `/api/generate` returns a job_id; polling `/api/jobs/{id}` reaches `completed`; the output PNG is valid 1024×1024 RGBA and retrievable.
- **S2.3** Web frontend loads at :3000 (index, css, js all served) with Generate/Edit tabs and live job progress.
- **S2.4** `/api/edit` accepts a multipart image + prompt and returns a completed job with a valid PNG. *(Carried: endpoint exists; end-to-end not yet exercised.)*
- **S2.5** Repo is public on GitHub (SPhillips1337/qwen-image2.1), MIT-licensed, with .gitignore excluding models/output/.env and sd-cpp as a pinned submodule at 792bcd3.

## Phase 3 — distributed text-encoder offload (experimental)

- **S3.1** A worker container on a remote box serves the identical abliterated encoder GGUF via llama.cpp with an endpoint returning the `[n_token, hidden_size]` float tensor for a given prompt.
- **S3.2** Parity proof: for ≥3 fixed prompts, local `--llm` encoding and remote-encoded embeddings are numerically equal (max abs diff < 1e-4 in fp32) — the same GGUF must be on both ends.
- **S3.3** Gateway routes encoding to a healthy worker when `OFFLOAD_WORKERS` is set, falls back to local encoding when no worker responds within timeout, and the generated image is visually identical (same seed) to the fully-local run.
- **S3.4** Benchmark table: local vs offloaded total latency and 5090 peak VRAM for a 1024×1024 generation; offload must not regress wall-clock time beyond LAN RTT + encode transfer.

## Phase 4 — polish, assistant, GitHub-ready

- **S4.1** `/api/prompt-assist` expands a rough prompt via gemma-4-e2b (192.168.5.229:1234) with graceful degradation when the host is unreachable.
- **S4.2** Unsloth INT8 vs Q8_0 benchmark on identical prompts (LPIPS/SSIM or perceptual check) recorded in research/.
- **S4.3** README quick start verified from a clean machine (fresh clone → downloader → compose up → image generated).
- **S4.4** Truth Audit: LTM entries cross-checked against current code; stale entries removed (AGENTS.md §2 rule 3).
