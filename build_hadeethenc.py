import json
import os
import time

from hadeethenc import (
    get_categories,
    get_hadiths_by_category,
    get_hadith_details
)


OUTPUT_FILE = "hadeethenc_data.json"


def collect_hadith_ids():
    print("بدء جمع IDs الأحاديث...")

    categories = get_categories()

    print(f"عدد التصنيفات: {len(categories)}")

    hadith_ids = set()

    for index, category in enumerate(categories, start=1):

        category_id = category["id"]
        category_title = category["title"]
        total = int(category.get("hadeeths_count", 0))

        print(
            f"\n[{index}/{len(categories)}] "
            f"{category_title} - {total} حديث"
        )

        if total == 0:
            continue

        page = 1

        while True:

            data = get_hadiths_by_category(
                category_id=category_id,
                page=page,
                per_page=100
            )

            for hadith in data.get("data", []):
                hadith_ids.add(hadith["id"])

            meta = data.get("meta", {})

            last_page = int(meta.get("last_page", 1))

            print(
                f"  الصفحة {page}/{last_page} "
                f"- الأحاديث الفريدة: {len(hadith_ids)}"
            )

            if page >= last_page:
                break

            page += 1

    print(f"\nإجمالي IDs الفريدة: {len(hadith_ids)}")

    return sorted(hadith_ids)


def load_existing_data():
    if not os.path.exists(OUTPUT_FILE):
        return {}

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            item["id"]: item
            for item in data
        }

    except (json.JSONDecodeError, KeyError):
        print("تحذير: ملف البيانات موجود لكنه غير صالح، سنبدأ من جديد.")
        return {}


def save_data(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            list(data.values()),
            file,
            ensure_ascii=False,
            indent=2
        )


def collect_hadith_details(hadith_ids):
    data = load_existing_data()

    print(f"\nالأحاديث المحفوظة مسبقًا: {len(data)}")

    remaining_ids = [
        hadith_id
        for hadith_id in hadith_ids
        if hadith_id not in data
    ]

    print(f"الأحاديث المتبقية: {len(remaining_ids)}")

    for index, hadith_id in enumerate(remaining_ids, start=1):

        try:
            details = get_hadith_details(hadith_id)

            data[hadith_id] = {
                "id": hadith_id,
                "evidence": details["evidence"],
                "source_name": details["source_name"],
                "source_location": details["source_location"],
                "grade": details["grade"],
                "explanation": details["explanation"],
                "attribution": details["attribution"],
                "title": details["title"]
            }

            save_data(data)

            print(
                f"\rتم تحميل: {index}/{len(remaining_ids)} "
                f"| الإجمالي المحفوظ: {len(data)}",
                end=""
            )

            time.sleep(0.05)

        except Exception as e:
            print(
                f"\nخطأ في الحديث {hadith_id}: {e}"
            )

            print("تم حفظ البيانات السابقة.")
            save_data(data)

    print("\n\nاكتمل جمع التفاصيل.")
    print(f"إجمالي الأحاديث المحفوظة: {len(data)}")


def main():
    print("===================================")
    print("      Sanad - HadeethEnc Data")
    print("===================================")

    hadith_ids = collect_hadith_ids()

    collect_hadith_details(hadith_ids)


if __name__ == "__main__":
    main()