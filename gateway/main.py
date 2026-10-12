"""FastAPI gateway for Qwen-Image-2.1 Turbo (stable-diffusion.cpp backend).

Serves the web frontend and exposes a small JSON API that proxies to the
sd-server's native async job API (/sdcpp/v1/*), plus a prompt-assist endpoint
backed by a local vision-capable LLM (gemma-4-e2b) for prompt expansion.

The Turbo schedule is baked in: 8 steps, CFG 1.0, euler, fixed sigma list.
"""

import os
import re
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

SD_SERVER = os.environ.get("SD_SERVER_URL", "http://sd-server:8080")
GEMMA_URL = os.environ.get("GEMMA_URL", "http://host.docker.internal:1234/v1")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/app/output"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Turbo distilled schedule — do not change without re-distilling the model.
TURBO_SIGMAS = [1.0, 0.978453, 0.95418, 0.926626, 0.89508, 0.845148, 0.704534, 0.414568, 0.0]
TURBO_STEPS = 8
TURBO_CFG = 1.0

app = FastAPI(title="Qwen-Image-2.1 Turbo Gateway")


class GenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = ""
    width: int = Field(1024, ge=64, le=4096, multiple_of=32)
    height: int = Field(1024, ge=64, le=4096, multiple_of=32)
    seed: int = -1
    batch_count: int = Field(1, ge=1, le=8)
    output_format: str = "png"


class EditRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    width: int = 0  # 0 => follow the input image
    height: int = 0
    seed: int = -1


def _sample_params() -> dict:
    return {
        "scheduler": "discrete",
        "sample_method": "euler",
        "sample_steps": TURBO_STEPS,
        "custom_sigmas": TURBO_SIGMAS,
        "guidance": {"txt_cfg": TURBO_CFG},
    }


def _image_dims(data: bytes):
    """Read (width, height) from raw PNG/JPEG bytes with the stdlib only.

    Returns None if the format is unrecognized — callers fall back to 0/0,
    which lets sd-server apply its own default.
    """
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        import struct
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":  # JPEG: scan for a SOF0-SOF15 marker
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return (w, h)
            seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
            i += 2 + seg_len
    return None


async def _submit_job(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{SD_SERVER}/sdcpp/v1/img_gen", json=payload)
    if r.status_code != 202:
        raise HTTPException(502, f"sd-server rejected job: {r.text[:500]}")
    return r.json()


@app.get("/api/capabilities")
async def capabilities():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{SD_SERVER}/sdcpp/v1/capabilities")
    if r.status_code != 200:
        raise HTTPException(503, "sd-server not ready yet")
    return r.json()


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    payload = {
        "prompt": req.prompt,
        "negative_prompt": req.negative_prompt,
        "width": req.width,
        "height": req.height,
        "seed": req.seed,
        "batch_count": req.batch_count,
        "sample_params": _sample_params(),
        "output_format": req.output_format,
        "preview": "proj",  # live latent previews during sampling
    }
    job = await _submit_job(payload)
    return {"job_id": job["id"], "poll_url": f"/api/jobs/{job['id']}"}


@app.post("/api/edit")
async def edit(
    prompt: str = Form(...),
    image: UploadFile = File(...),
):
    data = await image.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(413, "image too large (max 25MB)")
    import base64

    b64 = base64.b64encode(data).decode()
    # Forward the input image's real dimensions so sd-server preserves them
    # instead of falling back to its 512 default (which silently downscales edits).
    width, height = _image_dims(data) or (0, 0)
    payload = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "seed": -1,
        "init_image": b64,
        "sample_params": _sample_params(),
        "output_format": "png",
        "preview": "proj",
    }
    job = await _submit_job(payload)
    return {"job_id": job["id"], "poll_url": f"/api/jobs/{job['id']}"}


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{SD_SERVER}/sdcpp/v1/jobs/{job_id}")
    if r.status_code == 404 or r.status_code == 410:
        raise HTTPException(404, "job not found (expired?)")
    data = r.json()
    # Persist finished images to disk so they survive browser refreshes.
    if data.get("status") == "completed" and data.get("result"):
        for img in data["result"].get("images", []):
            import base64

            fn = OUTPUT_DIR / f"{job_id}_{img['index']}.png"
            if not fn.exists():
                fn.write_bytes(base64.b64decode(img["b64_json"]))
    return data


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_job(job_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{SD_SERVER}/sdcpp/v1/jobs/{job_id}/cancel")
    return JSONResponse(status_code=r.status_code, content=r.json())


@app.get("/api/output/{filename}")
async def output_image(filename: str):
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "", filename)
    p = OUTPUT_DIR / safe
    if not p.exists():
        raise HTTPException(404, "not found")
    return FileResponse(p, media_type="image/png")


@app.post("/api/prompt-assist")
async def prompt_assist(req: GenerateRequest):
    """Expand a short prompt into a rich image-generation prompt using gemma-4-e2b."""
    system = (
        "You are an expert at writing vivid, detailed prompts for AI image generation. "
        "Take the user's short idea and expand it into one rich, specific paragraph covering "
        "subject, setting, lighting, mood, composition, and style. No preamble, no quotes."
    )
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{GEMMA_URL}/chat/completions",
                json={
                    "model": "google/gemma-4-e2b",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": req.prompt},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 300,
                },
            )
            r.raise_for_status()
            return {"expanded_prompt": r.json()["choices"][0]["message"]["content"].strip()}
    except Exception as e:
        raise HTTPException(502, f"prompt assistant unavailable: {e}")


# Static frontend — mounted last so /api/* wins.
app.mount("/", StaticFiles(directory="/app/web", html=True), name="web")
