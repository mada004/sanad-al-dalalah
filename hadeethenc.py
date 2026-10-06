import requests


BASE_URL = "https://hadeethenc.com/api/v1"


def get_categories():
    response = requests.get(
        f"{BASE_URL}/categories/list/",
        params={
            "language": "ar"
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()

def get_hadiths_by_category(category_id, page=1, per_page=5):
    response = requests.get(
        f"{BASE_URL}/hadeeths/list/",
        params={
            "language": "ar",
            "category_id": category_id,
            "page": page,
            "per_page": per_page
        },
        timeout=10
    )

    response.raise_for_status()

    return response.json()

def get_hadith_details(hadith_id):
    response = requests.get(
        f"{BASE_URL}/hadeeths/one/",
        params={
            "language": "ar",
            "id": hadith_id
        },
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return {
        "evidence": data.get("hadeeth", ""),
        "source_name": "HadeethEnc",
        "source_location": data.get("reference", ""),
        "grade": data.get("grade", ""),
        "explanation": data.get("explanation", ""),
        "attribution": data.get("attribution", ""),
        "title": data.get("title", "")
    }


if __name__ == "__main__":
    categories = get_categories()

    print("عدد التصنيفات:", len(categories))

    first_category = categories[0]

    print("\nأول تصنيف:")
    print(first_category)

    category_id = first_category["id"]

    data = get_hadiths_by_category(
        category_id=category_id,
        page=1,
        per_page=100
    )

    first_hadith = data["data"][0]

    print("\nأول حديث:")
    print("ID:", first_hadith["id"])
    print("العنوان:", first_hadith["title"])

    details = get_hadith_details(first_hadith["id"])

    print("\nتفاصيل الحديث:")
    print("النص:", details["evidence"])
    print("الدرجة:", details["grade"])
    print("المرجع:", details["source_location"])
    print("الشرح موجود:", bool(details["explanation"]))