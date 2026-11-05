"""تنظيف ملف المبيعات: توحيد الأعمدة، الأرقام العربية، التواريخ، التكرار."""
import re
import pandas as pd

STANDARD = ["date", "product", "revenue", "quantity", "cost"]

SYNONYMS = {
    "date": ["date", "order date", "day", "التاريخ", "تاريخ", "تاريخ البيع", "يوم"],
    "product": ["product", "item", "name", "المنتج", "الصنف", "اسم المنتج", "اسم الصنف", "الصنف المنتج"],
    "quantity": ["quantity", "qty", "الكمية", "كمية", "العدد", "عدد"],
    "unit_price": ["price", "unit price", "unit_price", "السعر", "سعر الوحدة", "سعر البيع"],
    "revenue": ["total", "revenue", "sales", "amount", "الاجمالي", "اجمالي", "المبلغ",
                "المبيعات", "اجمالي المبيعات", "الاجمالي بعد الضريبه"],
    "cost": ["cost", "total cost", "التكلفه", "تكلفه", "اجمالي التكلفه"],
}

_AR_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬،", "0123456789.,,")


class CleaningError(Exception):
    """خطأ مفهوم للمستخدم (عمود ناقص مثلاً)."""


def _norm_header(s) -> str:
    s = str(s).strip().lower().translate(_AR_DIGITS)
    s = re.sub("[أإآ]", "ا", s)
    s = s.replace("ة", "ه").replace("ى", "ي")
    s = re.sub(r"[_/\-\(\)]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _to_number(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.translate(_AR_DIGITS)
    s = s.str.replace(r"(?i)sar|ر\.?\s?س|ريال|﷼", "", regex=True)
    s = s.str.replace(",", "", regex=False).str.replace(r"\s+", "", regex=True)
    return pd.to_numeric(s, errors="coerce")


_LOOKUP = None


def _lookup():
    global _LOOKUP
    if _LOOKUP is None:
        _LOOKUP = {_norm_header(a): k for k, v in SYNONYMS.items() for a in v}
    return _LOOKUP


def _promote_header(raw: pd.DataFrame):
    """يدوّر على صف العناوين الحقيقي في أول 15 صفًا (يتجاوز عناوين التقارير والأسطر الفارغة)."""
    best, best_i = 0, None
    for i in range(min(15, len(raw))):
        score = sum(_norm_header(v) in _lookup() for v in raw.iloc[i] if pd.notna(v))
        if score > best:
            best, best_i = score, i
    if best_i is None or best < 2:
        return None, 0
    names, seen = [], {}
    for j, h in enumerate(raw.iloc[best_i]):
        h = f"col_{j}" if pd.isna(h) or str(h).strip() == "" else str(h).strip()
        seen[h] = seen.get(h, 0) + 1
        names.append(h if seen[h] == 1 else f"{h}_{seen[h]}")
    body = raw.iloc[best_i + 1:].copy()
    body.columns = names
    return body.reset_index(drop=True), best


def _read_csv_bytes(data: bytes) -> pd.DataFrame:
    import csv
    import statistics
    text = None
    for enc in ("utf-8-sig", "cp1256", "latin-1"):
        try:
            text = data.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        raise CleaningError("الملف فارغ.")
    delim = max(",;\t|", key=lambda d: statistics.median(l.count(d) for l in lines[:30]))
    rows = list(csv.reader(lines, delimiter=delim))
    width = max(len(r) for r in rows)
    return pd.DataFrame([r + [None] * (width - len(r)) for r in rows], dtype=object)


def load_file(file, name: str) -> pd.DataFrame:
    """يقرأ CSV (أي ترميز/فاصل) أو Excel (أي ورقة، مع أسطر عناوين تقارير)."""
    import io
    file.seek(0)
    data = file.read()
    if name.lower().endswith((".xlsx", ".xlsm", ".xls")):
        sheets = pd.read_excel(io.BytesIO(data), sheet_name=None, header=None, dtype=object)
        candidates = [(sh, _promote_header(df)) for sh, df in sheets.items()]
    else:
        candidates = [("csv", _promote_header(_read_csv_bytes(data)))]
    candidates = [(sh, r) for sh, r in candidates if r[0] is not None]
    if not candidates:
        raise CleaningError("لم أجد صف عناوين مفهومًا (التاريخ، المنتج، الإجمالي...). تأكدي أن الملف يحوي أعمدة المبيعات.")
    return max(candidates, key=lambda c: c[1][1])[1][0]


def _parse_dates(col: pd.Series) -> pd.Series:
    """سنة-شهر-يوم (ISO) تُقرأ سنةً أولًا، وغيرها (15/06/2026) يومًا أولًا. كل خلية تُحكم وحدها."""
    s = col.astype(str).str.translate(_AR_DIGITS).fillna("").str.strip()
    iso = s.str.match(r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}").fillna(False).astype(bool)
    a = pd.to_datetime(s[iso], errors="coerce", yearfirst=True, format="mixed")
    b = pd.to_datetime(s[~iso], errors="coerce", dayfirst=True, format="mixed")
    return pd.concat([a, b]).sort_index()


def clean_sales(raw: pd.DataFrame):
    """يرجع (df نظيف، تقرير بالإجراءات). الأعمدة: date, product, revenue, quantity, cost."""
    report = []
    n_in = len(raw)
    lookup = {_norm_header(a): k for k, v in SYNONYMS.items() for a in v}
    rename = {}
    for col in raw.columns:
        key = lookup.get(_norm_header(col))
        if key and key not in rename.values():
            rename[col] = key
    df = raw.rename(columns=rename)[list(rename.values())].copy()
    if rename:
        report.append("الأعمدة المعتمدة: " + "، ".join(f"{o} ← {n}" for o, n in rename.items()))

    for need, label in (("date", "التاريخ"), ("product", "المنتج/الصنف")):
        if need not in df:
            raise CleaningError(f"لم أجد عمود {label}. الأعمدة الموجودة: {list(raw.columns)}")

    df = df.dropna(how="all")
    for c in ("revenue", "quantity", "cost", "unit_price"):
        if c in df:
            df[c] = _to_number(df[c])

    if "revenue" not in df:
        if {"quantity", "unit_price"} <= set(df.columns):
            df["revenue"] = df["quantity"] * df["unit_price"]
            report.append("حُسب الإجمالي = الكمية × سعر الوحدة (لا يوجد عمود إجمالي).")
        else:
            raise CleaningError("لم أجد عمود الإجمالي، ولا الكمية مع سعر الوحدة.")
    for c in ("quantity", "cost"):
        if c not in df:
            df[c] = float("nan")

    df["date"] = _parse_dates(df["date"])
    bad = df["date"].isna() | df["revenue"].isna()
    if bad.sum():
        report.append(f"حُذف {int(bad.sum())} صف لأن التاريخ أو المبلغ غير صالح.")
    df = df[~bad]

    df["product"] = df["product"].astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
    df = df[df["product"].ne("") & df["product"].str.lower().ne("nan")]

    before = len(df)
    df = df.drop_duplicates(subset=["date", "product", "revenue", "quantity"])
    if before - len(df):
        report.append(f"حُذف {before - len(df)} صف مكرر تمامًا.")

    neg = int((df["revenue"] < 0).sum())
    if neg:
        report.append(f"يوجد {neg} صف بمبلغ سالب (مرتجعات)؛ أُبقيت وتُخصم من المبيعات.")

    df = df[STANDARD].sort_values("date").reset_index(drop=True)
    df["revenue"] = df["revenue"].astype(float)
    report.append(f"الصفوف: {n_in} ← {len(df)} بعد التنظيف.")
    if len(df) == 0:
        raise CleaningError("لم يتبقَّ أي صف صالح بعد التنظيف.")
    return df, report
