import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analytics import compute_facts
from cleaning import CleaningError, clean_sales, load_file

if not (ROOT / "test_data").exists():
    subprocess.run([sys.executable, "make_test_files.py"], cwd=ROOT, check=True)


def run(name):
    p = ROOT / "test_data" / name
    with open(p, "rb") as f:
        df, rep = clean_sales(load_file(f, name))
    return df, rep, compute_facts(df)


def test_01_messy_cafe():
    df, _, f = run("01_cafe_messy_arabic.csv")
    assert f["comparison"]["current_period"] == "2026-10"
    assert f["data_info"]["has_cost"]


def test_02_excel_title_rows_no_cost():
    df, _, f = run("02_english_xlsx_title_rows_no_cost.xlsx")
    assert set(df["product"]) >= {"برجر", "عصير"}
    assert (df.date.min().month, df.date.max().month) == (6, 10)
    assert f["comparison"]["current_period"] == "2026-10"
    assert not f["data_info"]["has_cost"] and "best_weekday" in f["kpis"]
    assert f["comparison"]["revenue_change"] < 0
    assert "profit_change" not in f["comparison"]


def test_03_semicolon_cp1256_thousands():
    df, _, f = run("03_semicolon_cp1256.csv")
    assert df["revenue"].max() == 1800
    assert f["comparison"]["cost_change_pct"] > 15


def test_04_returns():
    df, rep, _ = run("04_returns_negative.csv")
    assert (df["revenue"] < 0).sum() == 25 and any("مرتجعات" in r for r in rep)


def test_05_too_short():
    df, _, f = run("05_too_short.csv")
    assert str(df.date.min().date()) == "2026-06-01" and str(df.date.max().date()) == "2026-06-05"
    assert f["comparison"] is None


def test_06_missing_date_is_rejected_clearly():
    try:
        run("06_missing_date.csv")
    except CleaningError as e:
        assert "التاريخ" in str(e)
    else:
        raise AssertionError("كان يجب رفض الملف")


def test_07_mixed_date_formats_keep_all_rows():
    df, rep, _ = run("07_mixed_date_formats.csv")
    assert not any("غير صالح" in r for r in rep)
    assert df["date"].min().month == 6 and df["date"].max().month == 10


def test_08_weekly_drops_partial_last_week():
    df, _, f = run("08_weekly_30_days.csv")
    assert (df.date.min().month, df.date.max().month) == (6, 6)
    assert f["data_info"]["period_unit"] == "أسبوع" and f["data_info"]["note"]


if __name__ == "__main__":
    bad = 0
    for n, fn in list(globals().items()):
        if n.startswith("test_"):
            try:
                fn(); print("PASS", n)
            except Exception as e:
                bad += 1; print("FAIL", n, "->", repr(e))
    sys.exit(bad)
