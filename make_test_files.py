"""يولّد test_data/ : ملفات تحاكي ما سيرسله أصحاب المتاجر فعلًا (فوضوية عن قصد)."""
import pathlib
import shutil

import numpy as np
import pandas as pd
from openpyxl import Workbook

OUT = pathlib.Path("test_data")
OUT.mkdir(exist_ok=True)
rng = np.random.default_rng(11)

MENU = {"شاورما دجاج": (15, 8), "برجر": (28, 14), "بطاطس": (8, 3), "عصير": (10, 4), "وجبة عائلية": (65, 38)}
BASE = {"شاورما دجاج": 30, "برجر": 18, "بطاطس": 25, "عصير": 20, "وجبة عائلية": 6}


def base(start, end):
    rows = []
    for d in pd.date_range(start, end):
        for p, (price, cost) in MENU.items():
            q = int(rng.poisson(BASE[p]))
            if q:
                rows.append([d, p, q, price, q * price, round(q * cost, 2)])
    return pd.DataFrame(rows, columns=["date", "product", "qty", "price", "total", "cost"])


ar = {"date": "التاريخ", "product": "الصنف", "qty": "الكمية", "price": "سعر الوحدة", "total": "الإجمالي", "cost": "التكلفة"}
en = {"date": "Date", "product": "Item", "qty": "Qty", "price": "Unit Price", "total": "Total", "cost": "Cost"}

# 01: مقهى (الملف الأصلي) بأخطاء متنوعة
shutil.copy("sample_cafe_sales.csv", OUT / "01_cafe_messy_arabic.csv") if pathlib.Path("sample_cafe_sales.csv").exists() else None

# 02: Excel بعناوين إنجليزية + أسطر عنوان تقرير فوق الجدول + ورقة ملاحظات + بدون تكلفة
df = base("2026-06-01", "2026-10-31")
wb = Workbook()
ws = wb.active
ws.title = "Sales"
ws.append(["Al-Noor Grocery - Sales Report"])
ws.append(["Generated from POS - 2026"])
ws.append([])
ws.append(["Date", "Item", "Qty", "Unit Price", "Total"])
for r in df.itertuples():
    ws.append([r.date.to_pydatetime(), r.product, r.qty, r.price, r.total * (0.7 if r.date.month == 10 else 1)])
ws2 = wb.create_sheet("Notes")
ws2.append(["ملاحظات"])
ws2.append(["لا تحذف هذه الورقة"])
wb.save(OUT / "02_english_xlsx_title_rows_no_cost.xlsx")

# 03: فاصلة منقوطة + ترميز cp1256 (ويندوز عربي) + آلاف بفواصل
df = base("2026-06-01", "2026-10-31")
df["cost"] = df["cost"] * df["date"].dt.month.map(lambda m: 1.25 if m == 10 else 1)
out = df.rename(columns=ar)[list(ar.values())].copy()
out["التاريخ"] = df["date"].dt.strftime("%d-%m-%Y")
cat = pd.DataFrame({"التاريخ": pd.date_range("2026-06-01", "2026-10-31", freq="3D").strftime("%d-%m-%Y"),
                    "الصنف": "طلبية تموين", "الكمية": 4, "سعر الوحدة": 450, "الإجمالي": 1800, "التكلفة": 1200})
out["الإجمالي"] = df["total"]
out = pd.concat([out, cat], ignore_index=True)
out["الإجمالي"] = out["الإجمالي"].map(lambda v: f"{v:,.0f}")   # 1,800 بفاصلة آلاف
out.to_csv(OUT / "03_semicolon_cp1256.csv", sep=";", index=False, encoding="cp1256")

# 04: مرتجعات (مبالغ سالبة)
df = base("2026-06-01", "2026-10-31")
neg = df.sample(25, random_state=3).copy()
neg[["qty", "total", "cost"]] *= -1
pd.concat([df, neg]).rename(columns=ar).to_csv(OUT / "04_returns_negative.csv", index=False, encoding="utf-8-sig")

# 05: بيانات قصيرة جدًا (5 أيام): لا تكفي للمقارنة
base("2026-06-01", "2026-06-05").rename(columns=ar).to_csv(OUT / "05_too_short.csv", index=False, encoding="utf-8-sig")

# 06: ملف بلا عمود تاريخ: يجب أن يرفضه بخطأ واضح
base("2026-06-01", "2026-07-30").rename(columns=ar).drop(columns=["التاريخ"]).to_csv(
    OUT / "06_missing_date.csv", index=False, encoding="utf-8-sig")

# 07: صيغ تواريخ مختلطة في نفس العمود
df = base("2026-06-01", "2026-10-31")
fmt = np.array(["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"])
df["date"] = [d.strftime(fmt[i % 3]) for i, d in enumerate(df["date"])]
df.rename(columns=ar).to_csv(OUT / "07_mixed_date_formats.csv", index=False, encoding="utf-8-sig")

# 08: 30 يومًا فقط (مقارنة أسبوعية؛ آخر أسبوع ناقص)
base("2026-06-01", "2026-06-30").rename(columns=en).to_csv(OUT / "08_weekly_30_days.csv", index=False)

print(*sorted(p.name for p in OUT.iterdir()), sep="\n")
