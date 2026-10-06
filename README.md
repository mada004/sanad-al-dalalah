# سند الدلالة | Sanad Al-Dalalah

An Arabic evidence-review assistant for Islamic content. It identifies informational assertions in user-written text, retrieves reference passages, and helps a human reviewer assess and improve the content.

**AI assists the reviewer; final judgment and approval remain human.** The system does not issue religious rulings or certify hadith authenticity.

## Demo

- [Production frontend](https://quiet-sprinkles-4f25c6.netlify.app/)
- [Production backend](https://sanad-al-dalalah.onrender.com)
- [Interactive API documentation](https://sanad-al-dalalah.onrender.com/docs)

## Problem and solution

Reviewing Islamic content requires finding relevant references and comparing their meaning with what an author actually wrote. Evidence may support only part of a statement, supply an important missing qualification, or be insufficient.

Sanad Al-Dalalah brings original content, retrieved evidence, AI explanations, and proposed revisions into one Arabic review workspace. It supports evidence-informed editing while keeping the reviewer in control of every change.

## How it works

1. The user submits natural Arabic text. The frontend retains the full original content.
2. The backend extracts informational assertions, aiming to exclude greetings, pure questions, headings, and empty fragments without judging whether evidence exists.
3. Retrieval searches the configured sources and combines their results.
4. Source-neutral text ranking orders candidates; Stage 1 selects evidence relevant to a substantive part of the current assertion.
5. Stage 2 evaluates the current assertion against the selected evidence and returns a status, a reason, and an optional suggestion. Grounding validation and Arabic-language handling help check the output; uncertain evaluations can fall back to human review.
6. The frontend presents review items, primary evidence, source names, explanations, and available suggestions. Additional retrieved evidence can be expanded separately.

An input with no extracted assertions returns zero review items. Lack of adequate evidence is a review outcome, not proof that a statement is false.

## Main features

- Arabic interface with right-to-left layout.
- Individual assertion review while preserving the original text.
- Four evaluation statuses and Arabic explanations for Arabic input.
- Primary evidence and optional additional evidence with human-readable source names.
- Evidence-grounded suggested revisions when a safe replacement is available.
- Reviewer decisions, final text assembly, and copying of the reviewed version.
- Optional-source resilience: Dorar or Central DB failures return no results rather than stopping analysis.

## Human-in-the-loop workflow

For each review item, the reviewer can **keep the original**, **accept an available improvement**, or **refer it to a specialist**. Decisions can be revisited before generating the improved version. Only accepted suggestions replace the corresponding original text; other content remains intact.

The reviewer compares the original and improved versions and approves the final review. Decisions and approval are held in the current browser session; persistent review records are not provided.

## Evaluation statuses

| Status | Intended meaning |
| --- | --- |
| `supported` | The selected evidence establishes all substantive meaning without an important missing qualification. |
| `partially_supported` | The current review item contains multiple independently evaluable assertions; evidence establishes some but not others. Topical overlap alone is insufficient. |
| `needs_context` | The core is established, but evidence supplies an important condition, scope, exception, or qualification omitted from the wording. |
| `needs_review` | Evidence is insufficient, unrelated, ambiguous, conflicting, or cannot establish enough for a confident evaluation. |

These labels express an AI-assisted assessment of the selected passage, not a definitive religious judgment.

## Evidence and source approach

Retrieval is limited to the project's configured reference sources rather than unrestricted web search:

- **موسوعة الأحاديث النبوية – HadeethEnc:** searches the included `hadeethenc_data.json` using Arabic normalization, character n-gram TF-IDF, and cosine similarity.
- **القاعدة المركزية للمحتوى الإسلامي باللغات — ICADB Central DB:** semantic API search across books, using returned Arabic source passages.
- **الدرر السنية — Dorar:** optional hadith API search with resilient HTTP failure handling.

Ranking does not prefer a source by name. Source identity and location accompany evidence in the API for traceability; the interface displays evidence text and source names without raw technical metadata or source-location fields. Source inclusion and retrieval similarity do not independently establish authority, authenticity, or support. Additional passages are retrieval results, not separately evaluated confirmations.

## Architecture and tech stack

```text
React + Vite frontend
    → FastAPI POST /analyze
    → Claim extraction
    → HadeethEnc + Central DB + optional Dorar retrieval
    → Source-neutral ranking → Stage 1 relevance selection
    → AI-assisted evidence evaluation through Ollama
    → Review results → Human decisions → Final reviewed text
```

- **Frontend:** React, Vite, JavaScript, and CSS.
- **Backend:** Python, FastAPI, Pydantic, and Uvicorn.
- **Retrieval/integration:** scikit-learn, Requests, and Beautiful Soup.
- **AI:** Ollama generation API, supporting local Ollama and configured Ollama Cloud access.
- **Checks:** Python unittest, Python compilation, Oxlint, and Vite production build.

The frontend sends `POST /analyze` with a JSON `text` field. The response contains a `claims` array; each item includes `claim`, `status`, `evidence`, `reason`, and `suggestion`, with optional `additional_evidence`.

## Local setup

Prerequisites: Python, Node.js with npm, and Ollama for local inference. Run backend commands from the repository root so the included HadeethEnc dataset can be located.

Install dependencies and the default local model:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
ollama pull qwen2.5:3b
```

Start Ollama in a separate terminal if its desktop service is not already running:

```powershell
ollama serve
```

Start the backend from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8002
```

Start the frontend in another terminal:

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open `http://127.0.0.1:5173`. Local API documentation is at `http://127.0.0.1:8002/docs`. With no overrides, the backend uses local Ollama and `qwen2.5:3b`; no Cloud key is required for this setup.

### Environment variables

| Name | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Frontend API base URL; public build-time configuration. |
| `CORS_ALLOWED_ORIGINS` | Additional explicit backend CORS origins, comma-separated. |
| `OLLAMA_BASE_URL` | Local or Cloud Ollama service base URL. |
| `OLLAMA_MODEL` | Model used for extraction and evaluation. |
| `OLLAMA_API_KEY` | Optional backend-only secret for authenticated Cloud access. |

Configure backend variables in the process environment; backend `.env` files are not automatically loaded. Frontend configuration can use `frontend/.env.local`. Environment files are ignored by Git. Never place credentials in frontend variables, source code, or version control.

### Verification

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q main.py claim_extraction.py ai_compare.py semantic_search.py central_db.py dorar.py
cd frontend
npm run lint
npm run build
```

## Current limitations

- Extraction and evaluation depend on the configured model. Assertions may be missed or statuses and explanations may be incorrect; human review remains necessary.
- Coverage is limited by the bundled dataset and external search results. Relevant evidence may be absent, incomplete, or ranked poorly.
- External services and model calls affect availability and latency; longer texts require multiple sequential evaluations.
- Suggested revisions are conservative and may be unavailable. Grounding checks do not guarantee semantic correctness.
- This is a review aid, not a comprehensive verification service, authenticity assessment, or substitute for specialist judgment.
