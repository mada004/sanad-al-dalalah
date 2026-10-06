import requests
from bs4 import BeautifulSoup


def search_dorar(query):
    response = requests.get(
        "https://dorar.net/dorar_api.json",
        params={"skey": query},
        timeout=10
    )

    response.raise_for_status()

    data = response.json()
    html = data["ahadith"]["result"]

    soup = BeautifulSoup(html, "html.parser")

    results = []

    for hadith in soup.find_all(class_="hadith"):

        text = hadith.get_text(" ", strip=True)

        info = hadith.find_next(class_="hadith-info")

        info_text = ""
        if info:
            info_text = info.get_text(" ", strip=True)

        if text:
            results.append({
                "evidence": text,
                "source_name": "Dorar.net",
                "source_location": info_text
            })

        if len(results) == 5:
            break

    return results

def show_results(query):
    results = search_dorar(query)

    for i, result in enumerate(results, start=1):
        print(f"\n===== النتيجة {i} =====")
        print("الدليل:", result["evidence"])
        print("المصدر:", result["source_name"])
        print("المعلومات:", result["source_location"])