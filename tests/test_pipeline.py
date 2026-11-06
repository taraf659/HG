import io, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pandas as pd
from cleaning import clean_sales
from analytics import compute_facts
from advisor import unverified_numbers, template_answer


def _facts():
    root = pathlib.Path(__file__).resolve().parents[1]
    if not (root / "sample_cafe_sales.csv").exists():
        subprocess.run([sys.executable, "make_sample.py"], cwd=root, check=True)
    raw = pd.read_csv(root / "sample_cafe_sales.csv")
    df, rep = clean_sales(raw)
    return raw, df, rep, compute_facts(df)


def test_cleaning():
    raw, df, rep, _ = _facts()
    assert len(df) < len(raw)
    assert df["revenue"].dtype.kind == "f"
    assert "لاتيه" in set(df["product"]) and "  لاتيه " not in set(df["product"])
    assert df["date"].notna().all()


def test_facts_match_pandas():
    _, df, _, f = _facts()
    assert f["kpis"]["total_revenue"] == round(df["revenue"].sum(), 2)
    c = f["comparison"]
    assert c["current_period"] == "2026-10" and c["previous_period"] == "2026-09"
    assert c["profit_change"] < 0
    names = {r["product"] for r in c["products_down"]}
    assert {"آيس لاتيه", "موهيتو"} <= names
    for r in c["products_down"]:
        if "volume_effect" in r:
            assert abs(r["volume_effect"] + r["price_effect"] - r["change"]) < 0.05


def test_number_guard():
    _, _, _, f = _facts()
    ok = f"المبيعات تغيّرت {abs(f['comparison']['revenue_change'])}"
    assert unverified_numbers(ok, f) == []
    assert unverified_numbers("المبيعات نزلت 987654 ريال", f) == [987654.0]
    assert "آيس لاتيه" in template_answer(f)


def test_arabic_headers_and_missing_cost():
    raw = pd.DataFrame({"التاريخ": ["01/01/2026", "02/01/2026"], "المنتج": ["أ", "ب"],
                        "الكمية": ["٢", "3"], "سعر الوحدة": ["10", "٥"]})
    df, rep = clean_sales(raw)
    assert list(df["revenue"]) == [20.0, 15.0]


if __name__ == "__main__":
    for n, fn in list(globals().items()):
        if n.startswith("test_"):
            fn(); print("PASS", n)
