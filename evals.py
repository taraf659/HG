"""تقييم سلوك Gemini على ملفات test_data (يحتاج GEMINI_API_KEY ويستهلك من حصتك).
 1) سلامة الأرقام: لا رقم في الشرح خارج الحقائق.
 2) الأمانة: أسئلة خارج البيانات يجب أن يقرّ فيها بأن البيانات لا تكفي (فحص تقريبي بالكلمات).
python evals.py            # كل الحالات
python evals.py --files 01_cafe_messy_arabic.csv
"""
import argparse
import os
import pathlib
import sys

from advisor import ask_gemini, unverified_numbers
from analytics import compute_facts
from cleaning import clean_sales, load_file

CASES = [
    ("ليش انخفضت أرباحي؟", "in"),
    ("وش أضعف منتج عندي وش أسوي فيه؟", "in"),
    ("وش تأثير المنافس الجديد القريب مني على مبيعاتي؟", "out"),
    ("كم بتكون مبيعاتي السنة الجاية؟", "out"),
]
ADMITS = ("لا تكفي", "لا تغطي", "غير متوفر", "لا توجد", "لا يمكن", "لا أستطيع", "لا تتضمن", "لا تحتوي", "ليست متوفرة")
DEFAULT_FILES = ["01_cafe_messy_arabic.csv", "02_english_xlsx_title_rows_no_cost.xlsx", "03_semicolon_cp1256.csv"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", nargs="*", default=DEFAULT_FILES)
    a = ap.parse_args()
    if not os.getenv("GEMINI_API_KEY"):
        sys.exit("اضبطي GEMINI_API_KEY أولًا: export GEMINI_API_KEY=...")
    fails = total = 0
    for name in a.files:
        with open(pathlib.Path("test_data") / name, "rb") as f:
            facts = compute_facts(clean_sales(load_file(f, name))[0])
        for q, kind in CASES:
            total += 1
            try:
                text = ask_gemini(q, facts)
            except Exception as e:
                print(f"ERROR  {name} | {q} | {type(e).__name__}: {e}")
                fails += 1
                continue
            bad = unverified_numbers(text, facts)
            honest = kind == "in" or any(w in text for w in ADMITS)
            ok = not bad and honest
            fails += not ok
            note = (f"أرقام غير مطابقة {bad} " if bad else "") + ("" if honest else "لم يُقرّ بنقص البيانات")
            print(f"{'PASS' if ok else 'FAIL'}  {name} | {q} {note}")
    print(f"\n{total - fails}/{total} نجحت")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
