"""تشغيل المستشار من الطرفية:
python cli.py sample_cafe_sales.csv
python cli.py sales.xlsx -q "ليش انخفضت أرباحي؟" --facts
"""
import argparse
import json
import sys

from advisor import DEFAULT_QUESTION, advise
from analytics import compute_facts
from cleaning import CleaningError, clean_sales, load_file


def main():
    ap = argparse.ArgumentParser(description="مستشار الأعمال الذكي")
    ap.add_argument("file", help="ملف CSV أو Excel")
    ap.add_argument("-q", "--question", default=DEFAULT_QUESTION)
    ap.add_argument("--facts", action="store_true", help="اطبع JSON الحقائق المحسوبة")
    ap.add_argument("--no-ai", action="store_true", help="بدون Gemini (قالب جاهز)")
    a = ap.parse_args()

    try:
        with open(a.file, "rb") as f:
            df, report = clean_sales(load_file(f, a.file))
    except (CleaningError, OSError) as e:
        sys.exit(f"خطأ: {e}")

    print("== تقرير التنظيف ==")
    for line in report:
        print(" •", line)
    facts = compute_facts(df)
    if a.facts:
        print("\n== الحقائق ==")
        print(json.dumps(facts, ensure_ascii=False, indent=2))

    if a.no_ai:
        from advisor import template_answer
        text, source, warns = template_answer(facts), "قالب بدون ذكاء اصطناعي", []
    else:
        text, source, warns = advise(a.question, facts)
    print(f"\n== الجواب ({source}) ==\n{text}")
    for w in warns:
        print("\n⚠", w)


if __name__ == "__main__":
    main()
