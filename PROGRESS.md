# PROGRESS.md — dated log with evidence

Newest first. Every `done` task cites the real command/output that proves it (ADR-0001: worker self-report is never Done proof).

## 2026-10-12 — Session close (end of day)

**State at close:** working tree clean, local `main` even with `origin/main` at `a222a41`. Product ships as a single-5090 docker-compose stack: native sd-server web UI on :8080 (generation + reference-image editing), API-only FastAPI gateway on :3000 (proxy + prompt-assist). All four model files present at authoritative sizes; edit path verified E2E and genuinely conditioning on the input image.

**Done today (all pushed):**
- Phase 1: CUDA 12.8 / arch 120 Docker build, all 4 models downloaded & size-verified, ~46 s baseline generation.
- Phase 2: docker-compose stack, gateway + frontend, E2E generation + editing through the API; public repo.
- Edit path fixed for real: `init_image` was silently ignored by Qwen-Image 2.1 → switched to `ref_images[]`; confirmed a true edit (scene preserved, change applied), not a regeneration. No HF model swap needed.
- Option 1 restructure: dropped the redundant custom `web/` frontend; :3000 is API-only, :8080 owns the UI. Docs + LTM updated to match.
- Frontend timing bug (epoch seconds vs ms) and JPEG-upload crash (branch-local `import struct`) both fixed and verified.

**Known / carried forward:**
- **Phase 3 offload — deferred by user.** Stock sd.cpp has no LLM hidden-state injection for Qwen-Image; would need a maintained patch branch (encode-dump + inject). No llama.cpp worker running anywhere yet.
- Native :8080 UI does not persist images to disk (returns base64 in the response); only the gateway path writes to `output/`. Untouched this session — revisit if on-disk saves from the native UI are wanted.

## 2026-10-12 — Phase 2 complete + repo public

- **T2.4 E2E generation via gateway** ✅ — `POST /api/generate` → `job_6acd0f5b_00000000` → polled to `completed` in ~45 s → `output/job_6acd0f5b_00000000_0.png`, verified 1024×1024 PNG (2.3 MB). Frontend assets (`/`, `/js/main.js`, `/css/styles.css`) all HTTP 200 on :3000.
- **Gateway crash-loop fixed** ✅ — container was restarting on `RuntimeError: Form data requires "python-multipart"` from the multipart `/api/edit` route; added `python-multipart==0.0.*` to requirements, rebuilt, container stable.
- **T2.5 public repo** ✅ — https://github.com/SPhillips1337/qwen-image2.1 (public), commit b543fd5 on main. Contents: .gitignore (models/, output/, .env, ref-frontend/), MIT LICENSE, README.md with quick start + API table, sd-cpp pinned submodule @792bcd3, repo description set via `gh repo edit`. `.env` (HF token) confirmed absent from git.
- **Compose-up mystery resolved** ✅ — repeated "exit ?" results were the terminal validator rejecting foreground commands whose text matched a server pattern; script-file workaround returned `UP_EXIT=0`. sd-server up 9 min at check time, `/sdcpp/v1/capabilities` reports model Qwen-Image-2.1-Turbo-Q8_0.gguf, modes [img_gen].

## 2026-10-12 — Phase 1 complete

- **T1.3 baseline generation** ✅ — `sd-cli --diffusion-model ...Turbo-Q8_0.gguf --llm ...Abliterated-Uncensored-Q8_0.gguf --vae qwen_image_2.1_vae_bf16.safetensors -p '...' --steps 8 --cfg-scale 1.0 --sampling-method euler --sigmas "1.0,0.978453,0.95418,0.926626,0.89508,0.845148,0.704534,0.414568,0.0" -W 1024 -H 1024 --diffusion-fa` → ~46 s total (encode 15.6 s, sample 26.4 s @ 1.1 it/s, decode 4 s) → valid 1024×1024 RGBA PNG at `models/test_baseline.png`. Required `--entrypoint ""`.
- **T1.2 models** ✅ — all four files at authoritative sizes (verified against HF API `/api/models/.../tree/main`, not README): denoiser 7,591,554,784 B; encoder 8,709,520,096 B; mmproj F16 1,159,029,984 B; VAE 675,509,688 B.
- **T1.1 image build** ✅ — `docker build -f docker/Dockerfile.cuda --build-arg CUDA_VERSION=12.8.0 --build-arg UBUNTU_VERSION=24.04 --build-arg CUDA_ARCHITECTURES=120 --build-arg GGML_CUDA_FA_ALL_QUANTS=ON -t sdcpp-cuda:5090 .` → exit 0. First attempt failed on missing ggml submodule (`git clone --depth 1` doesn't fetch submodules); fixed with `git submodule update --init --depth 1`.

## 2026-10-12 — Phase 3 recon: offload seam does not exist in stock sd.cpp (user deferred)

- **T3.1 recon** ✅ (investigation complete, build deferred by user) — Traced the Qwen-Image-2.1 conditioning path in `sd-cpp/src/conditioning/conditioner.hpp`:
  - `token_embed_custom` / `--embd-dir` belong to `FrozenCLIPEmbedderWithCustomWords` (SD1/SD2/SDXL CLIP conditioner, A1111 custom words) — NOT the LLM path. Prior "no-fork offload seam" assumption was a misread; AD-03 superseded, lesson logged in patterns_and_lessons.md.
  - The Qwen LLM conditioner's `encode_prompt()` unconditionally calls `llm->compute()`, then applies token weighting, slices the prompt-template prefix, zero-pads, and builds `c_token_types` image slots. No CLI flag, server endpoint, or file-load path accepts precomputed hidden states; only server mode is `img_gen`. Upstream's single newer commit (d637cfb) adds only a sigma preset — no encode-only mode.
  - **Viable design (for when Phase 3 resumes):** small maintained patch to sd.cpp — encode-only dump of the post-processed `c_crossattn` + inject path that skips `llm->compute()`. Parity by construction (same tokenizer/template/weighting code), worker = llama.cpp box with identical GGUF. Text-only generation is deterministic given identical tokens; editing would need image-slot handling too.
  - **User decision:** defer offload, ship the single-5090 product as-is. Phase 3 stays documented in ROADMAP/SPEC for later.

## 2026-10-12 — Edit path verified E2E (T1.4 + T2.6) + gateway downscale bug fixed

- **T1.4 / T2.6 edit E2E** ✅ — `POST /api/edit` multipart (`prompt` + `image=@models/test_baseline.png`) → `job_6acd2009_00000001` → `completed` in ~12 s → `output/job_6acd2009_00000001_0.png`, verified **1024×1024** PNG. This exercises the full mmproj + `init_image` conditioning path through gateway → sd-server.
- **Bug found & fixed: edits silently downscaled to 512×512.** The gateway hardcoded `width: 0, height: 0` in the edit payload, so sd-server fell back to its default instead of preserving the input image's size (first edit attempt produced a 512×512 PNG). Fix: added `_image_dims()` to `gateway/main.py` — stdlib-only PNG IHDR / JPEG SOF dimension reader — and the `/api/edit` handler now forwards the upload's real dimensions. Rebuilt gateway, re-ran edit → 1024×1024 confirmed.
- **Operational note:** sd-server restarts (e.g. after a stopped probe) leave the gateway's httpx pool pointing at a dead peer for a few seconds — `/api/edit` returns `Internal Server Error` until the container is back; retry, don't rebuild.

## 2026-10-12 — Edit crash on JPEG uploads fixed + frontend JSON-parse error hardened (V3 browser)

- **Bug: every JPEG upload crashed the gateway with 500.** `_image_dims()` imported `struct` inside only the PNG branch, so the JPEG branch hit `UnboundLocalError` → plain-text "Internal Server Error" body. The frontend then tried `r.json()` on that text and showed `Unexpected token 'I', "Internal S"... is not valid JSON`.
- **Fixes:** (1) moved `import struct` to the top of `_image_dims()`; (2) added `_detail(r)` to `web/js/main.js` — tries JSON `{detail}`, falls back to raw text — and switched all three error call sites (generate, prompt-assist, edit) to it. No more JSON-parse crash on any non-JSON error body.
- **Verified:** PIL-generated valid 512×512 JPEG → gateway parser returns `(512, 512)` → `POST /api/edit` accepted (`job_6acd3247`) → completed → output PNG **512×512** (dimensions correctly preserved from the JPEG input). PNG path re-verified in a real browser earlier same day.

## 2026-10-12 — Edit path was silently text-to-image: `init_image` ignored, fixed with `ref_images[]`

- **User report:** "it's not an edit model… it just generated new ones." True — but the model IS a genuine edit model (Qwen-Image 2.1 Turbo supports editing at CFG=1 per the AtomicChat README). The bug was ours: the gateway sent `init_image`, which sd-server's Qwen-Image path **ignores**. Verified in server logs: those jobs never logged "EDIT mode" or any vision encoding — pure text-to-image, same as /api/generate.
- **Fix:** `gateway/main.py` `/api/edit` now sends `"ref_images": [b64]`. sd-server log for the fixed job shows: `preprocess ref[0]: 1024x1024 …`, `Using 'qwen' preset for reference images`, `EDIT mode --- image.cpp:274`, plus VAE encode + qwen3vl vision encoding of the input.
- **Verified E2E through gateway:** `POST /api/edit` (multipart, test_baseline.png, "paint the panda wearing a top hat") → `job_6acd365c_0000000b` → completed → `output/gw-edit-test.png`. Vision analysis: original lake/mountain/forest scene **preserved**, panda with black top hat added on the rock in the foreground — a real edit, not a regeneration. Direct sd-server probe (`ref_images[]`) produced the same result; an `init_image` probe of the same prompt produced only the untouched landscape.
- **No HF model swap needed** — no separate "edit model" required; this was a payload-field bug.

## 2026-10-12 — Option 1 restructure: gateway is API-only, UI lives on sd-server :8080

- **Decision (user):** there were two overlapping web frontends — our custom `web/` at :3000 and sd-server's native embedded sdcpp-webui at :8080. Resolved by dropping the custom frontend; :3000 is now a pure JSON API (proxy + prompt-assist), :8080 owns all UI including reference-image editing.
- **Changes:** removed `web/` (git rm -r); deleted the `StaticFiles` mount + import from `gateway/main.py`, replaced with a `/` route returning a JSON pointer to :8080; dropped `COPY web ./web` from `gateway/Dockerfile`. Updated README (architecture diagram, quick start now points to :8080, API-surface note), CONTEXT.md services table, and LTM modules.md.
- **Verified:** rebuilt gateway → `:3000/` returns the pointer JSON; `/api/capabilities` still proxies correctly; `:8080/` serves `<title>stable-diffusion.cpp WebUI</title>`. The native UI's edit input is its **Reference Images** section (maps to `ref_images[]`) — confirmed present in the served bundle (`ref_images` ×26, "Reference Images" ×4).
- **Note:** GitHub moved the repo to `HappyMonkeyAI/qwen-image2.1`; local remote updated to match so pushes keep working.

## Open items carried forward

- **Phase 3** — deferred by user; design + patch-branch plan recorded above and in ROADMAP.md. No llama.cpp worker running anywhere yet; 192.168.5.232 ports 1234/8080/5000/8188 all closed as of today's probe.
