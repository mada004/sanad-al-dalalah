from fastapi import FastAPI
from pydantic import BaseModel
from sources import SOURCES
from dorar import search_dorar

app = FastAPI()


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

        dorar_results = search_dorar(claim)

        if dorar_results:

            evidence_results = []

            for result in dorar_results:
                evidence_results.append({
                    "evidence": result["evidence"],
                    "source_name": result["source_name"],
                    "source_location": result["source_location"]
                })

            results.append({
                "claim": claim,
                "status": "needs_review",
                "evidence": evidence_results,
                "reason": "Multiple pieces of evidence were retrieved and require semantic comparison.",
                "suggestion": ""
            })

        else:
            results.append({
                "claim": claim,
                "status": "needs_review",
                "evidence": [],
                "reason": "No matching evidence was found in Dorar.net.",
                "suggestion": ""
            })

    return {"claims": results}