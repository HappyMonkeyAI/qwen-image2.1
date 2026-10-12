# Architectural decisions — qwen-image2.1

## AD-01: Path B — stable-diffusion.cpp directly, not ComfyUI
- **Date:** 2026-10-12 · **Status:** Active
- **Context:** User had ComfyUI workflows for an older Qwen Image model and asked whether a ComfyUI port was viable for the new Qwen-Image-2.1-Turbo GGUFs.
- **Decision:** Run stable-diffusion.cpp directly (one binary + 4 model files) inside docker-compose, with a FastAPI gateway and vanilla-JS frontend.
- **Rationale:** The HF repo ships GGUFs for sd.cpp, not safetensors — ComfyUI's UNETLoader/CLIPLoader node graph cannot load them without re-exporting original weights. Stability Matrix packages (SD WebUI/Forge/Neo) are Python A1111 forks with the same limitation. sd.cpp had day-0 Qwen-Image-2.1 support (landed 2026-09-20) including a built-in HTTP server (OpenAI-compatible + native async job API) and embedded UI, so Path B is both the only clean loader and the most self-contained shareable artifact.
- **Consequences:** Turbo schedule (8 steps, CFG 1.0, euler, fixed sigmas) must be reproduced by hand in the gateway since there is no ComfyUI workflow JSON to translate. The old workflow JSONs (`image_qwen_image.json`, `image_qwen_image_edit_2509.json`) are reference-only.

## AD-02: Offload the text encoder only; denoiser stays local
- **Date:** 2026-10-12 · **Status:** Active (experimental)
- **Context:** User wanted to use idle 8 GB boxes (192.168.5.229 AMD 5700XT, 192.168.5.232 RTX 1070 FE) alongside the laptop's RTX 5090.
- **Decision:** Ship only the one-shot text-encoder step to a remote llama.cpp worker; return the `[n_token, hidden_size]` hidden-state tensor (a few MB) over LAN. The denoiser never leaves the 5090.
- **Rationale:** The KSampler loop is ~95% of compute as a tight per-step dependency chain — shipping activations per layer per step over LAN would swamp any VRAM saving. Text encoding runs once per generation (~16 s on the 5090) and its output is a small tensor, making it the only viable offload unit.
- **Consequences:** Parity is mandatory — the worker must run the *identical* abliterated encoder GGUF or hidden states drift and images change. AD-Q4_K (5.3 GB) is the fallback quant for 8 GB boxes but breaks strict parity with a Q8_0 local baseline, so benchmarks must note which quant pair was used.

## AD-03: Use sd.cpp's `token_embed_custom` path; no fork
- **Date:** 2026-10-12 · **Status:** SUPERSEDED — corrected same day after source trace. `token_embed_custom` is the CLIP conditioner's A1111 custom-words mechanism (SD1/2/SDXL only); the Qwen LLM conditioner has no injection point. Offload requires patching sd.cpp (encode-dump + inject). New design pending user approval — see PROGRESS.md 2026-10-12 Phase 3 entry.
- **Context:** Offloading required injecting precomputed embeddings into the diffusion pipeline.
- **Decision:** Consume the existing `token_embed_custom` injection path in `src/conditioning/conditioner.hpp` (LLM output is a float tensor `[n_token, hidden_size]` in `c_crossattn`; the custom path skips the local LLM). Orchestrate from the Python gateway layer instead of forking stable-diffusion.cpp.
- **Rationale:** Forking a fast-moving upstream to add a feature that already exists as an injection point creates permanent merge debt. The gateway already proxies sd-server's async job API, so it is the natural place to intercept between encoding and denoising.
- **Consequences:** Phase 3 work is: llama.cpp worker image with an embedding endpoint + parity harness + gateway routing with health-check fallback. No C++ changes expected.

## AD-04: Build inside Docker; pin sd-cpp as submodule at 792bcd3
- **Date:** 2026-10-12 · **Status:** Active
- **Context:** The Windows laptop has no MSVC C++ workload and no CUDA toolkit (driver 617.14 only); Docker Desktop with verified GPU passthrough is the only build path.
- **Decision:** Build the sd-server image from `sd-cpp/docker/Dockerfile.cuda` with `CUDA_VERSION=12.8.0`, `UBUNTU_VERSION=24.04`, `CUDA_ARCHITECTURES=120`, `GGML_CUDA_FA_ALL_QUANTS=ON`. Keep stable-diffusion.cpp as a git submodule pinned at 792bcd3 rather than vendoring its tree.
- **Rationale:** The same Dockerfile + build args become the shareable artifact for other GPU owners. sm_120 (Blackwell) requires CUDA ≥ 12.8; the official default of 12.6.3 silently produces an image that cannot run on a 5090. Submodule pinning gives fresh clones the exact revision our verified image was built from without committing 425 MB of third-party code.
- **Consequences:** `git clone --recurse-submodules` is mandatory; CONTEXT.md records the pinned commit so image provenance is auditable.

## AD-05: Q8_0 quantization for both denoiser and encoder on the 5090
- **Date:** 2026-10-12 · **Status:** Active
- **Context:** 24 GB VRAM must hold denoiser + encoder + VAE plus activations for 1024×1024 (up to 2K).
- **Decision:** Q8_0 for both the Turbo denoiser (7.6 GB) and the abliterated encoder (8.7 GB); bf16 VAE (0.7 GB). Total ~17 GB leaves headroom.
- **Rationale:** Best picture fidelity that still fits; verified working end-to-end in ~46 s per image. Unsloth's INT8 claim (LPIPS 0.064/SSIM 0.936) is noted for a Phase 4 benchmark but their clean-base Dynamic GGUFs lack Turbo distillation and abliterated behavior, so they are not drop-in replacements.
- **Consequences:** 8 GB remote workers cannot run Q8_0 — they use AD-Q4_K (5.3 GB encoder + 1.2 GB mmproj), which is fine for the offload experiment but must be labeled as a non-parity configuration in benchmarks.
