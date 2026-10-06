# sanad-al-dalalah
AI-powered evidence verification tool for Islamic content.

## Deployment preparation

No deployment is configured or performed. The React UI, retrieval, AI prompts,
and comparison workflow are unchanged. Direct backend dependencies are listed
in `requirements.txt` using the versions in the working local environment.

### Environment variables

| Variable | Where | Default / usage |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Frontend build/dev environment | `http://127.0.0.1:8002`; set to the public HTTPS backend base URL for production, without `/analyze`. |
| `CORS_ALLOWED_ORIGINS` | Backend process environment | Optional comma-separated additional HTTP(S) origins, with no paths or trailing slashes. Wildcards are rejected. |
| `OLLAMA_BASE_URL` | Backend process environment | `http://localhost:11434`; the backend appends `/api/generate`. |
| `OLLAMA_MODEL` | Backend process environment | `qwen2.5:3b` locally; use `gpt-oss:20b` for Ollama Cloud. |
| `OLLAMA_API_KEY` | Backend secret environment | Optional locally; required for direct Ollama Cloud access. Sent only as a bearer authorization header. |

CORS always includes `http://localhost:5173`, `http://127.0.0.1:5173`, and
`https://quiet-sprinkles-4f25c6.netlify.app`. Credentials use explicit allowed
origins, never a wildcard. Frontend environment variables are public build-time
configuration; changing them requires rebuilding. Vite reads `frontend/.env.local`.
Python reads the process environment; backend `.env` files are not loaded automatically.
All `.env` and `.env.*` files are ignored by Git. No keys or secrets are required
for local Ollama. Keep the cloud key in the backend environment only; never put
it in frontend variables, source files, logs, or version control.

### Ollama Cloud

Set these backend environment variables for production:

```text
OLLAMA_BASE_URL=https://ollama.com
OLLAMA_MODEL=gpt-oss:20b
OLLAMA_API_KEY=<secret>
```

The endpoint becomes `https://ollama.com/api/generate`. Without a key, no
Authorization header is sent, preserving local Ollama support. The request
still uses `stream: false`, `think: false`, and a 180-second timeout; prompts,
JSON parsing, and comparison statuses are unchanged. Thinking controls vary
by model, so confirm the cloud model accepts `think: false` during testing.

To test from the repository root in PowerShell, enter the key at a hidden
prompt rather than placing it in shell history:

```powershell
$env:OLLAMA_BASE_URL = "https://ollama.com"
$env:OLLAMA_MODEL = "gpt-oss:20b"
$env:OLLAMA_API_KEY = ([System.Net.NetworkCredential]::new("", (Read-Host "Ollama API key" -AsSecureString))).Password
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8002
```

Submit content through the existing local frontend to exercise the complete
pipeline. After stopping the backend, remove the key from the terminal environment:

```powershell
Remove-Item Env:OLLAMA_API_KEY -ErrorAction SilentlyContinue
```

### Local run commands (PowerShell)

Run from the repository root. Create the virtual environment only if absent:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama serve
```

If the Ollama desktop app already runs the service, skip `ollama serve`.
In another terminal, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8002
```

In another terminal, from the repository root:

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

All environment variables are optional locally. To set overrides, use
`$env:VARIABLE_NAME = "value"` in the terminal before starting that process.

### Checks

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py ai_compare.py dorar.py semantic_search.py hadeethenc.py build_hadeethenc.py pipeline.py
cd frontend
npm run lint
npm run build
```

### What public hosting still requires

The static frontend can be built with `frontend` as its base directory,
`npm run build` as the build command, and `dist` as the publish directory.
Set `VITE_API_BASE_URL` to the actual public HTTPS backend URL before building.
The localhost fallback refers to each visitor's own computer and cannot serve
a public frontend. An HTTPS frontend also needs an HTTPS backend endpoint.

The backend needs a persistent Python service, HTTPS routing, and a listening
address/port appropriate to its host. A production startup command is
`python -m uvicorn main:app --host 0.0.0.0 --port 8002` (adjust the port to the
host's requirement; omit `--reload`). Start it from the repository root and
package the existing `hadeethenc_data.json`, which retrieval reads by relative path.
The host also needs outbound access to Dorar and network access to Ollama.

For self-hosted Ollama, it must run continuously with enough RAM/compute and persistent
model storage, with `qwen2.5:3b` pulled. It can share the backend host (the default
URL works there), or run on a privately reachable separate host configured with
`OLLAMA_BASE_URL`. A hosted backend cannot reach Ollama on your laptop through
`localhost`. Keep Ollama on a private network; only FastAPI needs a public HTTPS
endpoint. Netlify's static frontend hosting does not supply this Ollama service.

Alternatively, use Ollama Cloud with the three backend variables above; no
self-hosted model server is required. The backend then needs outbound HTTPS
access to `ollama.com` and a valid cloud API key supplied through its host's
secret environment settings.

The current synchronous analysis makes multiple model calls per claim, each
with a 180-second request timeout. Hosting/proxy request limits and capacity
must accommodate that existing behavior. Public traffic controls and service
supervision remain deployment work; no analysis logic was changed here.
