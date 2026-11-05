"""يولّد ملف مبيعات تجريبي لمقهى (يونيو-أكتوبر 2026) بأخطاء واقعية، وبهبوط مزروع في أكتوبر."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
menu = {"لاتيه": (18, 5.5), "قهوة مختصة": (22, 7), "كابتشينو": (17, 5), "آيس لاتيه": (20, 6),
        "موهيتو": (16, 4.5), "كرواسون": (12, 5), "تشيز كيك": (24, 11)}
base_qty = {"لاتيه": 28, "قهوة مختصة": 14, "كابتشينو": 16, "آيس لاتيه": 22, "موهيتو": 15, "كرواسون": 12, "تشيز كيك": 8}
rows = []
for d in pd.date_range("2026-06-01", "2026-10-31"):
    for p, (price, cost) in menu.items():
        q = rng.poisson(base_qty[p] * (1.25 if d.weekday() in (3, 4) else 1.0))
        c = cost
        if d.month == 10:  # الهبوط المزروع: المشروبات الباردة تتراجع وتكلفة الحليب ترتفع
            if p in ("آيس لاتيه", "موهيتو"):
                q = int(q * 0.6)
            if p in ("لاتيه", "كابتشينو"):
                c = cost * 1.18
        rows.append([d.strftime("%d/%m/%Y"), p, q, price, q * price, round(q * c, 2)])
df = pd.DataFrame(rows, columns=["التاريخ", "الصنف", "الكمية", "سعر الوحدة", "الإجمالي", "التكلفة"])
df = df[df["الكمية"] > 0]
# تشويش واقعي: تكرار، فراغات، أرقام عربية، مسافات، تاريخ تالف
df = pd.concat([df, df.sample(15, random_state=1)]).reset_index(drop=True)
df["الإجمالي"] = df["الإجمالي"].astype(object)
idx = df.sample(20, random_state=2).index
df.loc[idx, "الإجمالي"] = df.loc[idx, "الإجمالي"].astype(str) + " ريال"
df.iloc[5, 0] = "٠٥/٠٦/٢٠٢٦"
df.iloc[9, 1] = "  لاتيه "
df.iloc[30, 0] = "غير معروف"
df = pd.concat([df, pd.DataFrame([[None] * 6], columns=df.columns)])
df.to_csv("sample_cafe_sales.csv", index=False, encoding="utf-8-sig")
print("rows:", len(df))
