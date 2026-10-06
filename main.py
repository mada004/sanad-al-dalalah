import os
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dorar import search_dorar
from central_db import search_central_db
from claim_extraction import extract_claims
from semantic_search import search_hadiths, normalize_arabic
from ai_compare import compare_claim_with_evidence, basic_relation_check


app = FastAPI()

allowed_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://quiet-sprinkles-4f25c6.netlify.app",
]
for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(","):
    origin = origin.strip()
    if not origin:
        continue
    parsed = urlsplit(origin)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or "*" in origin
    ):
        raise ValueError("CORS_ALLOWED_ORIGINS must contain explicit HTTP(S) origins without paths")
    if origin not in allowed_origins:
        allowed_origins.append(origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


@app.get("/")
def home():
    return {"message": "Sanad project is running!"}


@app.post("/analyze")
def analyze(request: AnalyzeRequest):

    claims = extract_claims(request.text)

    results = []

    for claim in claims:

        # البحث في HadeethEnc
        hadeethenc_results = search_hadiths(
            claim,
            top_k=3
        )

        # البحث في Dorar
        dorar_results = search_dorar(claim)

        central_db_results = search_central_db(claim, top_k=5)

        # نجمع الأدلة
        evidence_results = []

        for result in hadeethenc_results:
            evidence_results.append({
                "evidence": result["evidence"],
                "source_name": result["source_name"],
                "source_location": result["source_location"]
            })

        for result in dorar_results[:2]:
            evidence_results.append({
                "evidence": result["evidence"],
                "source_name": result["source_name"],
                "source_location": result["source_location"]
            })

        evidence_results.extend(central_db_results)

        # إذا وجدنا أدلة، نرسل جميع الأدلة للـ AI للمقارنة
        if evidence_results:

            ai_result = compare_claim_with_evidence(
                claim,
                evidence_results
            )

            best_evidence_index = ai_result.get("best_evidence")

            if best_evidence_index is not None:
                best_evidence = evidence_results[best_evidence_index - 1]
            else:
                best_evidence = None

            result = {
                "claim": claim,
                "status": ai_result.get("status", "needs_review"),
                "evidence": [best_evidence] if best_evidence else [],
                "reason": ai_result.get("reason", ""),
                "suggestion": ai_result.get("suggestion", "")
            }
            if best_evidence:
                seen = {normalize_arabic(best_evidence["evidence"])}
                additional = []
                for candidate in evidence_results:
                    text_key = normalize_arabic(candidate["evidence"])
                    if text_key and text_key not in seen and basic_relation_check(claim, candidate["evidence"]):
                        additional.append(candidate)
                        seen.add(text_key)
                if additional:
                    result["additional_evidence"] = additional
            results.append(result)

        else:

            results.append({
                "claim": claim,
                "status": "needs_review",
                "evidence": [],
                "reason": "لم يتم العثور على دليل مناسب للمقارنة.",
                "suggestion": ""
            })

    return {
        "claims": results
    }
