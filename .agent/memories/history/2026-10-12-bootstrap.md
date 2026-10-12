# 2026-10-12 — Project bootstrap: single-GPU product + public repo

## What happened
Full Phase 1 (build, models, baseline generation) and Phase 2 (docker-compose stack, gateway, web UI, public GitHub repo) completed in one session.

## Key events
1. Chose Path B (stable-diffusion.cpp directly) over a ComfyUI port after confirming the HF GGUFs are sd.cpp-format only.
2. Built `sdcpp-cuda:5090` from the official Dockerfile with CUDA 12.8 / arch 120 overrides; first build failed on missing ggml submodule (shallow clone), fixed with `git submodule update --init --depth 1`.
3. Downloaded all four models; chased a phantom encoder gap caused by stale README sizes — resolved by querying the HF API for authoritative sizes.
4. Baseline 1024×1024 generation: ~46 s end-to-end (encode 15.6 s, sample 26.4 s @ 1.1 it/s, decode 4 s).
5. Wrote docker-compose.yml + FastAPI gateway + vanilla-JS frontend; gateway crash-looped on missing python-multipart for the multipart edit route — fixed and rebuilt.
6. E2E generation through the gateway: job submitted, polled to completed in ~45 s, valid 1024×1024 PNG in output/.
7. Pushed public repo SPhillips1337/qwen-image2.1 with MIT license, .gitignore, sd-cpp pinned submodule @792bcd3, README, and repo description.

## Outcomes / next
- Product works on a single 5090 with zero offload — the base value proposition is proven.
- Next: T1.4/T2.6 (edit path E2E), then Phase 3 distributed encoder offload (the experimental core).
