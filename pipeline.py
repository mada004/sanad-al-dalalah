import json

from semantic_search import search_hadiths
from dorar import search_dorar
from ai_compare import compare_claim_with_evidence


def retrieve_evidence(claim, top_k=3):

    print("\n==============================")
    print("البحث عن الأدلة")
    print("==============================")

    # ==========================================
    # 1. البحث في HadeethEnc
    # ==========================================

    print("\n[1] البحث في HadeethEnc...")

    hadeethenc_results = search_hadiths(
        claim,
        top_k=top_k
    )

    print(
        f"تم العثور على {len(hadeethenc_results)} نتائج من HadeethEnc"
    )

    # ==========================================
    # 2. البحث في Dorar.net
    # ==========================================

    print("\n[2] البحث في Dorar.net...")

    dorar_results = search_dorar(claim)

    print(
        f"تم العثور على {len(dorar_results)} نتائج من Dorar.net"
    )

    # ==========================================
    # 3. دمج النتائج
    # ==========================================

    all_results = []

    for result in hadeethenc_results:

        all_results.append({
            "evidence": result.get(
                "evidence",
                ""
            ),
            "source_name": "HadeethEnc",
            "source_location": result.get(
                "source_location",
                ""
            ),
            "grade": result.get(
                "grade",
                ""
            )
        })

    for result in dorar_results:

        all_results.append({
            "evidence": result.get(
                "evidence",
                ""
            ),
            "source_name": "Dorar.net",
            "source_location": result.get(
                "source_location",
                ""
            ),
            "grade": result.get(
                "grade",
                ""
            )
        })

    # ==========================================
    # 4. عرض الأدلة المجمعة
    # ==========================================

    print("\n==============================")
    print("الأدلة المجمعة")
    print("==============================")

    for i, result in enumerate(
        all_results,
        start=1
    ):

        print(f"\n===== الدليل {i} =====")

        print(
            "المصدر:",
            result["source_name"]
        )

        print(
            "الدليل:",
            result["evidence"]
        )

        print(
            "المعلومات:",
            result["source_location"]
        )

        if result.get("grade"):
            print(
                "الدرجة:",
                result["grade"]
            )

    return all_results


def run_pipeline(claim):

    print("\n\n########################################")
    print("          SANAD PIPELINE")
    print("########################################")

    # ==========================================
    # 1. استرجاع الأدلة
    # ==========================================

    evidence_results = retrieve_evidence(
        claim
    )

    # ==========================================
    # 2. مقارنة الادعاء مع الأدلة باستخدام AI
    # ==========================================

    print("\n\n==============================")
    print("بدء مقارنة الادعاء مع الأدلة")
    print("==============================")

    ai_result = compare_claim_with_evidence(
        claim,
        evidence_results
    )

    # ==========================================
    # 3. الحصول على أفضل دليل
    # ==========================================

    best_evidence_index = ai_result.get(
        "best_evidence"
    )

    selected_evidence = []

    if (
        best_evidence_index is not None
        and isinstance(best_evidence_index, int)
        and 1 <= best_evidence_index <= len(evidence_results)
    ):

        selected_evidence.append(
            evidence_results[
                best_evidence_index - 1
            ]
        )

    else:

        # إذا لم يحدد AI دليلًا معينًا،
        # نستخدم الأدلة المسترجعة كلها.
        selected_evidence = evidence_results

    # ==========================================
    # 4. تجهيز الأدلة للعقد النهائي
    # ==========================================

    final_evidence = []

    for evidence in selected_evidence:

        final_evidence.append({
            "evidence": evidence.get(
                "evidence",
                ""
            ),
            "source_name": evidence.get(
                "source_name",
                ""
            ),
            "source_location": evidence.get(
                "source_location",
                ""
            )
        })

    # ==========================================
    # 5. بناء JSON النهائي
    # ==========================================

    final_result = {
        "claims": [
            {
                "claim": claim,
                "status": ai_result.get(
                    "status",
                    "needs_review"
                ),
                "evidence": final_evidence,
                "reason": ai_result.get(
                    "reason",
                    ""
                ),
                "suggestion": ai_result.get(
                    "suggestion",
                    ""
                )
            }
        ]
    }

    # ==========================================
    # 6. عرض النتيجة النهائية
    # ==========================================

    print("\n\n########################################")
    print("             FINAL JSON")
    print("########################################")

    print(
        json.dumps(
            final_result,
            ensure_ascii=False,
            indent=2
        )
    )

    return final_result


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    claim = "خيركم من يحفظ الشعر العربي"

    run_pipeline(claim)