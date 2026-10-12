# MCP.md — Intent → server routing (qwen-image2.1)

**Purpose:** Stop mid-task tool amnesia. Route work by **intent**, then confirm/activate via live catalogue — not by hoping a tool is already in the session list.

**Rules (ADR-0003):**
1. On grounding / protocol bootstrap: read this file + optional `MCP.local.md`.
2. Before non-trivial work matching a row: prefer the listed MCP over shell improvisation.
3. **Listed ≠ mounted.** If tools are missing: one live check (proxy search/activate, or Hermes config) before claiming "unavailable."
4. Never put secrets, tokens, or raw connection strings here. Names and hosts only.
5. Keep this table short (high-value intents).

## Project intents

| Intent | Server / tool (typical name) | Use when | Notes |
|--------|------------------------------|----------|-------|
| Docker build / GPU container work | `terminal` (docker, nvidia-smi) | Building sdcpp-cuda image, running sd-server/sd-cli | Blackwell needs CUDA 12.8 + arch 120; verify with `nvidia/cuda:12.8.0-base-ubuntu24.04 nvidia-smi` inside a container |
| Model download / size verification | `terminal` (curl) or HF API via `web_extract` | Fetching GGUFs, checking authoritative file sizes | HF xet rejects Range resume; verify Content-Length against `/api/models/<repo>/tree/main` |
| Web UI live QA (V3) | `browser_exec` | Frontend job polling, edit upload flow | Gateway on :3000, sd-server on :8080 |
| GitHub repo / push / description | `terminal` (gh CLI) | Spine commits, releases | `gh auth setup-git` first; plain `git push` may fail credential prompting |
| LAN host probing (encoder workers) | `terminal` (curl with short timeouts) | Checking 192.168.5.229 / .232 for llama.cpp workers | 229 runs gemma-4-e2b at :1234/v1; 232 had nothing listening as of 2026-10-12 |
| Prompt-assist integration testing | `terminal` (curl) against gemma-4-e2b | `/api/prompt-assist` endpoint | http://192.168.5.229:1234/v1 — OpenAI-compatible |

## Core plane (Hermes session defaults)

| Intent | Server (typical name) | Use when | Notes |
|--------|----------------------|----------|-------|
| Lazy tool belt / activate on-demand servers | `dynamic_proxy` | Need a server not in session tool list | Search → activate → handshake with project context |
| Host CPU/RAM admission for heavy jobs | `resource_sentinel` | Full docker builds, 17 GB downloads, parallel agents | Snapshot → request slot → lease → heartbeat → release |
| Live browser QA (V3) | `browser_exec` / Playwright MCP | Frontend + gateway live checks | Real URL + state readback |

## On-demand plane

| Intent | Server / component | Activate / find via | Protocol hook |
|--------|--------------------|---------------------|---------------|
| Security audit of gateway (FastAPI, file upload) | `auditscan` | Hermes always-on when configured · else `proxy_activate_server("auditscan")` | Trident input, not Owner V2/V3 substitute |
| Article / model research | `article_research` or `web_search`/`web_extract` | Planning RECON for Phase 4 benchmarks | Unsloth INT8 vs FP8 comparison etc. |

**Related:** `AGENTS.md` §4 · `BOOTSTRAP.md` (discovery) · skill `mcp-intent-routing` · overlay: `MCP.local.md` (gitignored, machine-local).
