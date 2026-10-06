import math

import requests


CENTRAL_DB_URL = "https://icadb.com/books/api/books/relevant-examples/en/"
SOURCE_NAME = "القاعدة المركزية للمحتوى الإسلامي باللغات"


def _source_location(example, data):
    for item in (example, data):
        metadata = item.get("metadata")
        for fields in (item, metadata if isinstance(metadata, dict) else {}):
            book = fields.get("book")
            book = book if isinstance(book, dict) else {}
            title = next((value.strip() for value in (
                fields.get("book_title"), fields.get("book_name"),
                book.get("title"), book.get("name"),
            ) if isinstance(value, str) and value.strip()), None)
            if title:
                version = fields.get("version")
                version = version if isinstance(version, dict) else {}
                label = next((str(value).strip() for value in (
                    fields.get("version_title"), fields.get("version_name"),
                    version.get("title"), version.get("name"),
                    fields.get("version_number"), version.get("number"),
                ) if isinstance(value, (str, int)) and not isinstance(value, bool)
                    and str(value).strip()), None)
                return f"{title} – الإصدار {label}" if label else title
    return "نتيجة موثقة من القاعدة المركزية"


def search_central_db(query, top_k=5):
    try:
        response = requests.get(
            CENTRAL_DB_URL,
            params={"query": query, "k": top_k},
            timeout=15,
        )
        if response.status_code != 200:
            return []

        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("examples"), list):
            return []

        results = []
        for example in data["examples"]:
            if not isinstance(example, dict):
                return []
            text = example.get("source_text")
            phrase_id = example.get("phrase_id")
            similarity = example.get("similarity_percent")
            if (
                not isinstance(text, str) or not text.strip()
                or not isinstance(phrase_id, (str, int)) or isinstance(phrase_id, bool)
                or not str(phrase_id).strip()
                or not isinstance(similarity, (int, float)) or isinstance(similarity, bool)
                or not math.isfinite(similarity) or not 0 <= similarity <= 100
            ):
                return []

            results.append({
                "evidence": text,
                "source_name": SOURCE_NAME,
                "source_location": _source_location(example, data),
            })
        return results
    except (requests.RequestException, ValueError, TypeError, OverflowError):
        # Central DB is optional; other sources can still supply evidence.
        return []
