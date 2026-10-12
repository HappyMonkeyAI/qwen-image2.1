# ROADMAP.md

Dependencies flow top-down; each phase's exit gate is its SPEC section.

```
Phase 1  single-GPU baseline          ✅ 2026-10-12
   │    (build, models, sd-cli gen+edit)
Phase 2  docker-compose product       ✅ 2026-10-12 (T2.6 edit E2E pending)
   │    (sd-server + gateway + web UI, public repo)
Phase 3  distributed encoder offload  ◻ next — the experimental core
   │    (llama.cpp worker, parity harness, gateway routing, benchmark)
Phase 4  polish & GitHub-ready        ◻ after Phase 3 lands or is consciously parked
        (prompt-assist, INT8 benchmark, clean-machine verification, Truth Audit)
```

## Phase 3 detail (next work)

1. **Worker image** — llama.cpp container running the *identical* `Qwen-Image-2.1-Turbo-Abliterated-Uncensored-Q8_0.gguf` (or AD-Q4_K on an 8 GB box, with parity caveats documented). Endpoint: prompt in → `[n_token, hidden_size]` float tensor out (base64 or raw bytes over HTTP).
2. **sd.cpp patch branch** — stock sd.cpp has no LLM hidden-state injection (`token_embed_custom` is CLIP-only; the LLM conditioner always runs `llm->compute()`). Add: encode-only mode that dumps the post-processed `c_crossattn` tensor, and an inject path that consumes it and skips `llm->compute()`. Kept as a maintained branch of the pinned submodule — parity by construction (same tokenizer/template/weighting code on both ends).
3. **Parity harness** — script that encodes ≥3 fixed prompts through the patched local path and via the worker, asserts max abs diff < 1e-4. This is the "meat" of the project: no parity, no offload claim.
4. **Gateway routing** — `OFFLOAD_WORKERS=http://host:8081,...` env; health check per worker; on failure fall back to local encoding and log it.
5. **Benchmark** — wall-clock + peak VRAM, local vs offloaded, same seed, recorded in PROGRESS.md and surfaced in README.

Target hosts: 192.168.5.229 (runs gemma-4-e2b; AMD 5700XT 8 GB) and 192.168.5.232 (RTX 1070 FE 8 GB, nothing listening as of 2026-10-12). AD-Q4_K encoder (5.3 GB) + mmproj (1.2 GB) fits both.

## Phase 4 detail

- Prompt-assist endpoint against gemma-4-e2b at 192.168.5.229:1234/v1 with timeout + fallback text.
- Unsloth INT8 vs AtomicChat Q8_0 perceptual benchmark (their docs claim LPIPS 0.064/SSIM 0.936 for INT8 — verify on our prompts).
- Clean-machine run of the README quick start; fix whatever breaks.
- Truth Audit of LTM against code.

## Explicitly out of scope

- Layer-level denoiser splitting across machines (per-step LAN latency kills it).
- ComfyUI / SD WebUI porting (wrong weight format for these GGUFs).
- Multi-GPU or multi-node denoising.
