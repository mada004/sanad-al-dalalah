import json
import re

import requests

from ai_compare import ask_ai


def extract_claims(text):
    # Accept the input; a lack of review items is not a submission error.
    if len(re.findall(r"[^\W\d_]+", text, re.UNICODE)) < 2:
        return []

    prompt = (
        'Find the declarative factual statements INSIDE this Arabic conversation or content. '
        'Copy only the complete assertions verbatim. Omit greetings, transitions, headings, '
        'personal opinions, incomplete fragments and questions from the selected substrings. '
        'Do not split coherent assertions at commas or decide whether assertions are true. '
        'Output {"claims": ["exact original assertion"]}, or {"claims": []} if none. '
        'Arabic content:\n' + text
    )

    try:
        response = ask_ai(prompt).strip()
        if response.startswith("```"):
            response = re.sub(r"^```(?:json)?\s*|\s*```$", "", response)
        data = json.loads(response)
        if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
            return []
    except (requests.RequestException, ValueError, TypeError):
        # Do not invent claims when semantic extraction is unavailable.
        return []

    claims = []
    for claim in data["claims"]:
        if not isinstance(claim, str):
            continue
        claim = claim.strip()
        start = text.find(claim)
        if start < 0 or len(re.findall(r"[^\W\d_]+", claim, re.UNICODE)) < 2:
            continue
        if claim.endswith(("?", "؟")):
            continue
        # A statement can occur inside conversational wording. Require whole
        # words, not sentence punctuation; semantic completeness is model-led.
        end = start + len(claim)
        if start and re.match(r"\w", text[start - 1]) and re.match(r"\w", claim[0]):
            continue
        if end < len(text) and re.match(r"\w", text[end]) and re.match(r"\w", claim[-1]):
            continue
        if claim not in claims:
            claims.append(claim)
    return sorted(claims, key=text.find)
