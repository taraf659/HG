import os
import pandas as pd
import streamlit as st

from advisor import DEFAULT_QUESTION, advise
from analytics import compute_facts
from cleaning import CleaningError, clean_sales, load_file

st.set_page_config(page_title="مستشار الأعمال الذكي", page_icon="📊", layout="centered")
st.markdown("""<style>
html, body, [data-testid="stAppViewContainer"], .stMarkdown, .stTextInput, .stAlert { direction: rtl; text-align: right; }
[data-testid="stMetricValue"] { direction: ltr; text-align: right; }
</style>""", unsafe_allow_html=True)

st.title("📊 مستشار الأعمال الذكي")
st.caption("ارفعي ملف مبيعاتك، وأجيبكِ بالأرقام: ماذا حصل ولماذا وماذا تفعلين.")

with st.sidebar:
    st.header("الإعدادات")
    api_key = st.text_input("مفتاح Gemini (اختياري)", type="password",
                            value=os.getenv("GEMINI_API_KEY", ""))
    st.caption("بدون مفتاح يعمل التحليل كاملًا والشرح بقالب جاهز.")

file = st.file_uploader("ملف المبيعات (CSV أو Excel)", type=["csv", "xlsx", "xls"])
if not file:
    st.info("الأعمدة المطلوبة: التاريخ، المنتج/الصنف، والإجمالي (أو الكمية وسعر الوحدة). التكلفة اختيارية وتفعّل تحليل الربح.")
    st.stop()

try:
    df, report = clean_sales(load_file(file, file.name))
    facts = compute_facts(df)
except CleaningError as e:
    st.error(str(e))
    st.stop()

with st.expander("ماذا فعلتُ بملفك؟ (تقرير التنظيف)"):
    for line in report:
        st.write("•", line)
if facts["data_info"]["note"]:
    st.warning(facts["data_info"]["note"])

k = facts["kpis"]
c1, c2, c3 = st.columns(3)
c1.metric("إجمالي المبيعات", f"{k['total_revenue']:,.0f}")
c2.metric("عدد العمليات", f"{k['transactions']:,}")
c3.metric("متوسط العملية", f"{k['avg_transaction']:,.1f}")
c4, c5 = st.columns(2)
if "gross_margin_pct" in k:
    c4.metric("هامش الربح الإجمالي", f"{k['gross_margin_pct']}%")
else:
    c4.metric("أقوى يوم", k["best_weekday"])
c5.metric("أعلى منتج", k["top_products"][0]["product"], f"{k['top_products'][0]['share_pct']}% من المبيعات")

st.subheader("المبيعات عبر الفترات")
st.bar_chart(pd.DataFrame(facts["trend"]).set_index("period")["revenue"])

st.subheader("اسألي المستشار")
question = st.text_input("سؤالك", value=DEFAULT_QUESTION)
if st.button("حلّلي", type="primary"):
    with st.spinner("أحلل البيانات..."):
        text, source, warns = advise(question, facts, api_key or None)
    st.markdown(text)
    st.caption(f"مصدر الشرح: {source}")
    for w in warns:
        st.warning(w)
    with st.expander("الأرقام التي بُني عليها الشرح"):
        st.json(facts)
