"""طبقة الشرح: Gemini يصوغ فقط من الحقائق المحسوبة. وفحص يكشف أي رقم غير موجود فيها."""
import json
import os
import re

SYSTEM = """أنت مستشار أعمال لصاحب منشأة صغيرة. اكتب بالعربية البسيطة وبإيجاز.
قواعد صارمة:
1) استخدم فقط الأرقام الموجودة في JSON الحقائق. لا تحسب أرقامًا جديدة ولا تقرّب بطريقة تغيّر المعنى.
2) إن لم تكفِ الحقائق للإجابة فقل ذلك صراحة، ولا تخمّن أسبابًا خارج البيانات.
3) الهيكل: (أ) الخلاصة في جملة أو جملتين، (ب) أهم الأسباب مرتبة بأثرها، (ج) ثلاث توصيات عملية قابلة للتنفيذ هذا الأسبوع.
4) فرّق بين ما تُظهره البيانات وما هو احتمال يحتاج تأكيدًا من صاحب المنشأة."""

_AR = str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬،", "0123456789.,,")
DEFAULT_QUESTION = "ليش انخفضت أرباحي؟"


def _numbers_in(text: str):
    t = str(text).translate(_AR).replace(",", "")
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]


def _collect(node, out):
    if isinstance(node, dict):
        for v in node.values():
            _collect(v, out)
    elif isinstance(node, list):
        for v in node:
            _collect(v, out)
    elif isinstance(node, bool) or node is None:
        return
    elif isinstance(node, (int, float)):
        out.add(abs(float(node)))
    else:
        out.update(_numbers_in(node))


def unverified_numbers(text: str, facts: dict):
    """أرقام وردت في الشرح ولا تقابل أي رقم في الحقائق (بتسامح 0.5%). الأعداد ≤10 تُتجاهل (ترقيم)."""
    known = set()
    _collect(facts, known)
    bad = []
    for n in _numbers_in(text):
        if n == int(n) and n <= 10:
            continue
        if not any(abs(n - k) <= max(0.06, 0.005 * k) for k in known):
            bad.append(n)
    return sorted(set(bad))


def template_answer(facts: dict) -> str:
    """شرح بدون ذكاء اصطناعي (احتياطي عند غياب المفتاح أو فشل الاتصال)."""
    c = facts.get("comparison")
    if not c:
        return "البيانات لا تغطي فترتين كاملتين للمقارنة. ارفعي بيانات أطول لأعطيكِ تحليلًا للتغيّر."
    lines = []
    if "profit_change" in c:
        word = "انخفض" if c["profit_change"] < 0 else "ارتفع"
        lines.append(f"ربح {c['current_period']} {word} بمقدار {abs(c['profit_change'])} مقارنة بـ {c['previous_period']} "
                     f"(الهامش من {c['margin_previous_pct']}% إلى {c['margin_current_pct']}%).")
    word = "انخفضت" if c["revenue_change"] < 0 else "ارتفعت"
    lines.append(f"المبيعات {word} بمقدار {abs(c['revenue_change'])} ({c['revenue_change_pct']}%).")
    if c.get("cost_change_pct") is not None:
        lines.append(f"التكلفة تغيّرت بنسبة {c['cost_change_pct']}%.")
    for r in c["products_down"]:
        lines.append(f"- {r['product']}: تراجع {abs(r['change'])}"
                     + (f" (أثر الكمية {r['volume_effect']}، أثر السعر {r['price_effect']})" if "volume_effect" in r else
                        f" ({r.get('status', '')})"))
    return "\n".join(lines)


def ask_gemini(question: str, facts: dict, api_key: str | None = None, model: str | None = None) -> str:
    from google import genai
    from google.genai import types
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("لا يوجد GEMINI_API_KEY")
    client = genai.Client(api_key=key)
    prompt = f"السؤال: {question}\n\nالحقائق (JSON):\n{json.dumps(facts, ensure_ascii=False)}"
    resp = client.models.generate_content(
        model=model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.2),
    )
    return resp.text


def advise(question: str, facts: dict, api_key: str | None = None):
    """يرجع (النص، مصدر الشرح، تحذيرات)."""
    try:
        text = ask_gemini(question, facts, api_key)
    except Exception as e:  # بدون مفتاح أو فشل شبكة
        return template_answer(facts), f"قالب بدون ذكاء اصطناعي ({type(e).__name__})", []
    bad = unverified_numbers(text, facts)
    warns = [f"أرقام في الشرح لا تطابق الحسابات: {bad}. راجعي الجداول قبل الاعتماد عليها."] if bad else []
    return text, "Gemini", warns
