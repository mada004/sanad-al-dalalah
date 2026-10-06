from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dorar import search_dorar
from semantic_search import search_hadiths
from ai_compare import compare_claim_with_evidence


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
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

    claims = [
        claim.strip()
        for claim in request.text.split(".")
        if claim.strip()
    ]

    results = []

    for claim in claims:

        # البحث في HadeethEnc
        hadeethenc_results = search_hadiths(
            claim,
            top_k=3
        )

        # البحث في Dorar
        dorar_results = search_dorar(claim)

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

            results.append({
                "claim": claim,
                "status": ai_result.get("status", "needs_review"),
                "evidence": [best_evidence] if best_evidence else [],
                "reason": ai_result.get("reason", ""),
                "suggestion": ai_result.get("suggestion", "")
            })

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