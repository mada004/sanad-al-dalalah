import re
import unicodedata
import json

from ai_compare import ask_ai


def _has_content(text):
    # Ignore only obvious artifacts, not short sentences or unverifiable ideas.
    normalized = unicodedata.normalize("NFKC", text)
    normalized = re.sub(r"[\u0640\u064B-\u065F\u0670]", "", normalized)
    words = re.findall(r"[^\W\d_]+", normalized, re.UNICODE)
    return any(len(word) > 1 for word in words)


def _candidate_statements(text):
    """Segment content without splitting commas, decimals or wrapped lines."""
    statements = []
    start = 0
    # Commas, conjunctions, decimals and single wrapped lines stay intact.
    boundaries = re.finditer(
        r"[!?؟]+(?=\s|$)|(?<!\d)\.(?!\d)(?=\s|$)|\n[ \t]*\n", text,
    )
    for boundary in boundaries:
        if boundary.group() == ".":
            word = re.search(r"([^\W\d_]+)$", text[:boundary.start()], re.UNICODE)
            if word and len(word.group()) == 1:
                continue
        statement = text[start:boundary.end()].strip()
        if _has_content(statement):
            statements.append(statement)
        start = boundary.end()
    remainder = text[start:].strip()
    if _has_content(remainder):
        statements.append(remainder)
    return statements


def extract_claims(text):
    """Select literal informational assertions, without judging their evidence."""
    candidates = _candidate_statements(text)
    if not candidates:
        return []
    prompt = (
        'Remove only non-assertive parts (greetings, pure questions, headings, '
        'subjective preferences, fragments) from this Arabic content. Keep all '
        'informational assertions, even short informal nominal statements or '
        'false statements. Do not assess truth or evidence availability. '
        'Copy retained assertions exactly. Return JSON {"claims": ["retained text"]}. '
        'If the content asserts a fact, keep it. Arabic content:\n' + text
    )
    raw = ask_ai(prompt)
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())
    # Local models sometimes surround the JSON object with explanatory text.
    object_start = raw.find("{")
    if object_start < 0:
        raise ValueError("Invalid claim extraction response")
    data, _ = json.JSONDecoder().raw_decode(raw[object_start:])
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        raise ValueError("Invalid claim extraction response")
    claims = []
    positions = set()
    for claim in data["claims"]:
        if not isinstance(claim, str) or not _has_content(claim):
            continue
        claim = claim.strip()
        # The model may select a substring, but cannot rewrite or invent content.
        match = re.search(r"(?<!\w)" + re.escape(claim) + r"(?!\w)", text)
        if match and match.start() not in positions:
            positions.add(match.start())
            claims.append((match.start(), claim))
    return [claim for _, claim in sorted(claims)]
