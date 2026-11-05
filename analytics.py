"""كل الأرقام تُحسب هنا بـ Pandas. النموذج اللغوي لا يحسب شيئًا."""
import pandas as pd

_WEEKDAYS = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def _r(x, nd=2):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def _pct(new, old):
    return None if not old or pd.isna(old) else round((new - old) / abs(old) * 100, 1)


def _periods(df):
    span = (df["date"].max() - df["date"].min()).days
    freq = "M" if span >= 60 else "W"
    p = df["date"].dt.to_period(freq)
    periods = sorted(p.unique())
    note = None
    last = periods[-1]
    if df["date"].max().normalize() < last.end_time.normalize() and len(periods) >= 3:
        periods = periods[:-1]
        note = f"استُبعدت الفترة الأخيرة ({last}) لأنها غير مكتملة."
    return p, periods, ("شهر" if freq == "M" else "أسبوع"), note


def _product_drivers(cur, prev, has_qty):
    a = cur.groupby("product").agg(rev_c=("revenue", "sum"), q_c=("quantity", "sum"))
    b = prev.groupby("product").agg(rev_p=("revenue", "sum"), q_p=("quantity", "sum"))
    m = a.join(b, how="outer").fillna(0)
    m["change"] = m["rev_c"] - m["rev_p"]
    rows = []
    for name, x in m.iterrows():
        row = {"product": name, "revenue_previous": _r(x.rev_p), "revenue_current": _r(x.rev_c),
               "change": _r(x.change)}
        if x.rev_p == 0:
            row["status"] = "منتج جديد في الفترة الحالية"
        elif x.rev_c == 0:
            row["status"] = "لم يُبَع في الفترة الحالية"
        elif has_qty and x.q_p > 0 and x.q_c > 0:
            p0, p1 = x.rev_p / x.q_p, x.rev_c / x.q_c
            row.update(quantity_previous=_r(x.q_p), quantity_current=_r(x.q_c),
                       volume_effect=_r((x.q_c - x.q_p) * p0), price_effect=_r((p1 - p0) * x.q_c))
        rows.append(row)
    rows.sort(key=lambda r: r["change"])
    down = [r for r in rows if r["change"] < 0][:3]
    up = [r for r in reversed(rows) if r["change"] > 0][:3]
    return down, up


def compute_facts(df: pd.DataFrame) -> dict:
    has_cost, has_qty = df["cost"].notna().any(), df["quantity"].notna().any()
    total = df["revenue"].sum()
    top = df.groupby("product")["revenue"].sum().sort_values(ascending=False)
    p, periods, unit, note = _periods(df)

    kpis = {
        "total_revenue": _r(total),
        "transactions": int(len(df)),
        "avg_transaction": _r(df["revenue"].mean()),
        "top_products": [{"product": k, "revenue": _r(v), "share_pct": _r(v / total * 100, 1)}
                         for k, v in top.head(3).items()],
    }
    if has_cost:
        profit = df["revenue"].sum() - df["cost"].sum()
        kpis["gross_profit"] = _r(profit)
        kpis["gross_margin_pct"] = _r(profit / total * 100, 1)
    else:
        wd = df.groupby(df["date"].dt.weekday)["revenue"].sum()
        kpis["best_weekday"] = _WEEKDAYS[int(wd.idxmax())]
        kpis["weakest_weekday"] = _WEEKDAYS[int(wd.idxmin())]

    facts = {
        "data_info": {"rows": int(len(df)), "from": str(df["date"].min().date()),
                      "to": str(df["date"].max().date()), "has_cost": bool(has_cost),
                      "has_quantity": bool(has_qty), "period_unit": unit, "note": note},
        "kpis": kpis,
        "trend": [{"period": str(k), "revenue": _r(df.loc[p == k, "revenue"].sum())} for k in periods],
        "comparison": None,
    }
    if len(periods) >= 2:
        cp, pp = periods[-1], periods[-2]
        cur, prev = df[p == cp], df[p == pp]
        cmp_ = {"current_period": str(cp), "previous_period": str(pp),
                "revenue_current": _r(cur["revenue"].sum()), "revenue_previous": _r(prev["revenue"].sum())}
        cmp_["revenue_change"] = _r(cmp_["revenue_current"] - cmp_["revenue_previous"])
        cmp_["revenue_change_pct"] = _pct(cmp_["revenue_current"], cmp_["revenue_previous"])
        if has_cost:
            c_c, c_p = cur["cost"].sum(), prev["cost"].sum()
            pr_c, pr_p = cur["revenue"].sum() - c_c, prev["revenue"].sum() - c_p
            cmp_.update(cost_current=_r(c_c), cost_previous=_r(c_p), cost_change_pct=_pct(c_c, c_p),
                        profit_current=_r(pr_c), profit_previous=_r(pr_p), profit_change=_r(pr_c - pr_p),
                        profit_change_pct=_pct(pr_c, pr_p),
                        margin_current_pct=_r(pr_c / cur["revenue"].sum() * 100, 1),
                        margin_previous_pct=_r(pr_p / prev["revenue"].sum() * 100, 1))
        cmp_["products_down"], cmp_["products_up"] = _product_drivers(cur, prev, has_qty)
        facts["comparison"] = cmp_
    return facts
