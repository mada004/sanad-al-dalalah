import json
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


DATA_FILE = "hadeethenc_data.json"


def normalize_arabic(text):
    """
    تنظيف وتوحيد النص العربي قبل المقارنة.
    """

    if not text:
        return ""

    # إزالة التشكيل
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)

    # توحيد أشكال الألف
    text = re.sub(r"[إأآٱ]", "ا", text)

    # توحيد الياء والألف المقصورة
    text = text.replace("ى", "ي")

    # إزالة التطويل
    text = text.replace("ـ", "")

    # إزالة علامات الترقيم
    text = re.sub(r"[^\w\s]", " ", text)

    # توحيد المسافات
    text = re.sub(r"\s+", " ", text).strip()

    return text


def load_hadiths():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def search_hadiths(query, top_k=5):

    hadiths = load_hadiths()

    texts = [
        normalize_arabic(
            hadith.get("title", "") + " " + hadith.get("evidence", "")
        )
        for hadith in hadiths
    ]

    normalized_query = normalize_arabic(query)

    vectorizer = TfidfVectorizer(
        analyzer="char",
        ngram_range=(2, 5)
    )

    vectors = vectorizer.fit_transform(texts)

    query_vector = vectorizer.transform([normalized_query])

    similarities = cosine_similarity(
        query_vector,
        vectors
    ).flatten()

    best_indexes = similarities.argsort()[-top_k:][::-1]

    results = []

    for index in best_indexes:

        hadith = hadiths[index]

        results.append({
            "id": hadith["id"],
            "evidence": hadith["evidence"],
            "source_name": hadith["source_name"],
            "source_location": hadith["source_location"],
            "grade": hadith["grade"],
            "similarity": round(
                float(similarities[index]),
                4
            )
        })

    return results


if __name__ == "__main__":

    query = "خير الناس من يتعلم القرآن ويعلمه"

    results = search_hadiths(query, top_k=5)

    print("\n===== أفضل النتائج =====")

    for i, result in enumerate(results, start=1):

        print(f"\n--- النتيجة {i} ---")
        print("ID:", result["id"])
        print("الحديث:", result["evidence"])
        print("الدرجة:", result["grade"])
        print("التشابه:", result["similarity"])