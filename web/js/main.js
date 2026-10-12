// Qwen-Image 2.1 Turbo — vanilla JS frontend (no jQuery, no CDN).
// Talks to the FastAPI gateway at /api/*, which proxies sd-server's async jobs.

const $ = (sel) => document.querySelector(sel);

function switchTab(name) {
    $('#tabGenerate').classList.toggle('active', name === 'generate');
    $('#tabEdit').classList.toggle('active', name === 'edit');
    $('#genForm').classList.toggle('active', name === 'generate');
    $('#editForm').classList.toggle('active', name === 'edit');
}

function setStatus(msg, isError = false) {
    const el = $('#status');
    el.textContent = msg;
    el.style.display = 'block';
    el.classList.toggle('error', isError);
}

function clearResult() { $('#result').innerHTML = ''; }

// ---- Live progress: poll the job and render preview frames + step bar ----
async function trackJob(jobId) {
    const resultDiv = $('#result');
    resultDiv.innerHTML = '<p class="muted">Generating…</p><div class="progress-bar"><div class="progress-fill"></div></div>';
    const fill = resultDiv.querySelector('.progress-fill');

    while (true) {
        const r = await fetch(`/api/jobs/${jobId}`);
        if (!r.ok) throw new Error(`job poll failed: ${r.status}`);
        const job = await r.json();

        if (job.status === 'completed') {
            const img = job.result.images[0];
            resultDiv.innerHTML = '';
            const image = document.createElement('img');
            image.src = `data:image/png;base64,${img.b64_json}`;
            resultDiv.appendChild(image);
            // Persisted copy for refresh-safe viewing.
            setStatus(`Done in ${(job.completed - job.started).toFixed(1)}s`);
            return image;
        }
        if (job.status === 'failed') throw new Error(job.error?.message || 'generation failed');
        if (job.status === 'cancelled') throw new Error('job cancelled');

        // Live preview frame, if the server produced one.
        if (job.preview && job.preview.b64_json) {
            const label = resultDiv.querySelector('p');
            label.textContent = `Sampling step ${job.preview.step}/${job.preview.total_steps}`;
            fill.style.width = `${(job.preview.step / job.preview.total_steps) * 100}%`;
            let frame = resultDiv.querySelector('img.preview');
            if (!frame) {
                frame = document.createElement('img');
                frame.className = 'preview';
                resultDiv.insertBefore(frame, fill.parentElement);
            }
            frame.src = `data:image/png;base64,${job.preview.b64_json}`;
        }
        await new Promise((res) => setTimeout(res, 1500));
    }
}

// ---- Generate tab ----
$('#genForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const widthSel = $('#genWidth'), heightSel = $('#genHeight');
    // Handle the aspect-ratio presets: "864w" means 864 wide.
    let w = parseInt(widthSel.value), h = parseInt(heightSel.value);
    if (widthSel.value === '864w') { w = 864; h = 1536; }
    if (widthSel.value === '1536') { w = 1536; h = 864; }

    const body = {
        prompt: $('#genPrompt').value.trim(),
        negative_prompt: $('#genNegative').value.trim(),
        width: w, height: h,
        seed: parseInt($('#genSeed').value),
    };
    clearResult();
    setStatus('Submitting job…');
    try {
        const r = await fetch('/api/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
        });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        const { job_id } = await r.json();
        setStatus('Queued. Waiting for GPU…');
        await trackJob(job_id);
    } catch (err) {
        setStatus('Error: ' + err.message, true);
    }
});

// ---- Prompt assist (gemma-4-e2b) ----
$('#assistBtn').addEventListener('click', async () => {
    const prompt = $('#genPrompt').value.trim();
    if (!prompt) return;
    const btn = $('#assistBtn');
    btn.disabled = true; btn.textContent = '✦ Expanding…';
    try {
        const r = await fetch('/api/prompt-assist', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt }),
        });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        const { expanded_prompt } = await r.json();
        $('#genPrompt').value = expanded_prompt;
    } catch (err) {
        setStatus('Prompt assist: ' + err.message, true);
    } finally {
        btn.disabled = false; btn.textContent = '✦ Expand prompt';
    }
});

// ---- Edit tab ----
$('#sourceImage').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
        $('#previewImg').src = ev.target.result;
        $('#imagePreview').style.display = 'block';
    };
    reader.readAsDataURL(file);
});

$('#editForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const file = $('#sourceImage').files[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('prompt', $('#editPrompt').value.trim());
    fd.append('image', file);
    clearResult();
    setStatus('Uploading + submitting edit job…');
    try {
        const r = await fetch('/api/edit', { method: 'POST', body: fd });
        if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
        const { job_id } = await r.json();
        setStatus('Edit queued. Waiting for GPU…');
        await trackJob(job_id);
    } catch (err) {
        setStatus('Error: ' + err.message, true);
    }
});
