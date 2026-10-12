# TASKS.md — task board

Statuses: `todo` → `doing` → `review` → `done` (with evidence in PROGRESS.md) or `blocked` (reason + unblock condition).

## Phase 1 — single-GPU baseline
| ID | Task | Status |
|----|------|--------|
| T1.1 | Build sdcpp-cuda:5090 image (CUDA 12.8, arch 120) from sd-cpp submodule @792bcd3 | done |
| T1.2 | Download all 4 model files into models/ with size verification | done |
| T1.3 | Baseline 1024×1024 generation via sd-cli | done |
| T1.4 | Image edit baseline via sd-cli (`--llm_vision` mmproj + `-r` input) | todo |

## Phase 2 — docker-compose product
| ID | Task | Status |
|----|------|--------|
| T2.1 | docker-compose.yml: sd-server + api-gateway services | done |
| T2.2 | FastAPI gateway (proxy, Turbo sigmas, job polling, static frontend) | done |
| T2.3 | Web frontend (Generate/Edit tabs, live progress, no CDN) | done |
| T2.4 | End-to-end generation through gateway → valid PNG in output/ | done |
| T2.5 | Push public repo: .gitignore, MIT LICENSE, sd-cpp submodule, README, description | done |
| T2.6 | End-to-end edit through gateway `/api/edit` (multipart) | todo |

## Phase 3 — distributed encoder offload (experimental)
| ID | Task | Status |
|----|------|--------|
| T3.1 | llama.cpp worker container image + embedding endpoint for the abliterated GGUF | todo |
| T3.2 | Parity harness: local vs remote hidden states, 3 fixed prompts, max-abs-diff < 1e-4 | todo |
| T3.3 | Gateway offload routing (OFFLOAD_WORKERS health check + fallback to local) | todo |
| T3.4 | Latency + VRAM benchmark table (local vs offloaded) | todo |

## Phase 4 — polish & GitHub-ready
| ID | Task | Status |
|----|------|--------|
| T4.1 | `/api/prompt-assist` wired to gemma-4-e2b with graceful degradation | todo |
| T4.2 | Unsloth INT8 vs Q8_0 quality benchmark → research/ | todo |
| T4.3 | Clean-machine quick-start verification | todo |
| T4.4 | LTM Truth Audit (AGENTS.md §2 rule 3) | todo |
