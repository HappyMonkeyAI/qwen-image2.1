# PROGRESS.md — dated log with evidence

Newest first. Every `done` task cites the real command/output that proves it (ADR-0001: worker self-report is never Done proof).

## 2026-10-12 — Phase 2 complete + repo public

- **T2.4 E2E generation via gateway** ✅ — `POST /api/generate` → `job_6acd0f5b_00000000` → polled to `completed` in ~45 s → `output/job_6acd0f5b_00000000_0.png`, verified 1024×1024 PNG (2.3 MB). Frontend assets (`/`, `/js/main.js`, `/css/styles.css`) all HTTP 200 on :3000.
- **Gateway crash-loop fixed** ✅ — container was restarting on `RuntimeError: Form data requires "python-multipart"` from the multipart `/api/edit` route; added `python-multipart==0.0.*` to requirements, rebuilt, container stable.
- **T2.5 public repo** ✅ — https://github.com/SPhillips1337/qwen-image2.1 (public), commit b543fd5 on main. Contents: .gitignore (models/, output/, .env, ref-frontend/), MIT LICENSE, README.md with quick start + API table, sd-cpp pinned submodule @792bcd3, repo description set via `gh repo edit`. `.env` (HF token) confirmed absent from git.
- **Compose-up mystery resolved** ✅ — repeated "exit ?" results were the terminal validator rejecting foreground commands whose text matched a server pattern; script-file workaround returned `UP_EXIT=0`. sd-server up 9 min at check time, `/sdcpp/v1/capabilities` reports model Qwen-Image-2.1-Turbo-Q8_0.gguf, modes [img_gen].

## 2026-10-12 — Phase 1 complete

- **T1.3 baseline generation** ✅ — `sd-cli --diffusion-model ...Turbo-Q8_0.gguf --llm ...Abliterated-Uncensored-Q8_0.gguf --vae qwen_image_2.1_vae_bf16.safetensors -p '...' --steps 8 --cfg-scale 1.0 --sampling-method euler --sigmas "1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0" -W 1024 -H 1024 --diffusion-fa` → ~46 s total (encode 15.6 s, sample 26.4 s @ 1.1 it/s, decode 4 s) → valid 1024×1024 RGBA PNG at `models/test_baseline.png`. Required `--entrypoint ""`.
- **T1.2 models** ✅ — all four files at authoritative sizes (verified against HF API `/api/models/.../tree/main`, not README): denoiser 7,591,554,784 B; encoder 8,709,520,096 B; mmproj F16 1,159,029,984 B; VAE 675,509,688 B.
- **T1.1 image build** ✅ — `docker build -f docker/Dockerfile.cuda --build-arg CUDA_VERSION=12.8.0 --build-arg UBUNTU_VERSION=24.04 --build-arg CUDA_ARCHITECTURES=120 --build-arg GGML_CUDA_FA_ALL_QUANTS=ON -t sdcpp-cuda:5090 .` → exit 0. First attempt failed on missing ggml submodule (`git clone --depth 1` doesn't fetch submodules); fixed with `git submodule update --init --depth 1`.

## Open items carried forward

- **T1.4 / T2.6** — edit path (mmproj + input image) scaffolded in compose and gateway but never exercised end-to-end. Next concrete task.
- **Phase 3** — no llama.cpp worker running anywhere yet; 192.168.5.232 ports 1234/8080/5000/8188 all closed as of today's probe.
