# core/ai_engine.py
import os
from datetime import date, timedelta

from dotenv import load_dotenv
from openai import OpenAI

from core.accounting import get_pnl_between
from core.analytics import get_daily_revenue, get_top_products

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)


def is_ai_configured() -> bool:
    return client is not None


def _date_to_str(d: date) -> str:
    return d.isoformat()


def build_business_context(question: str, start_date: date, end_date: date) -> str:
    start_str = _date_to_str(start_date)
    end_str = _date_to_str(end_date)

    pnl_current = get_pnl_between(start_str, end_str)

    # previous period same length
    delta = end_date - start_date
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - delta
    prev_start_str = _date_to_str(prev_start)
    prev_end_str = _date_to_str(prev_end)
    pnl_prev = get_pnl_between(prev_start_str, prev_end_str)

    daily_rows = get_daily_revenue(start_str, end_str)
    top_rows = get_top_products(start_str, end_str, limit=10)

    lines = []
    lines.append(f"QUESTION: {question}")
    lines.append("")
    lines.append("PERIOD:")
    lines.append(f"  Current period: {start_str} to {end_str}")
    lines.append(f"  Previous period: {prev_start_str} to {prev_end_str}")
    lines.append("")
    lines.append("P&L CURRENT PERIOD:")
    lines.append(f"  Revenue: {pnl_current['revenue']:.2f}")
    lines.append(f"  Expenses_incl_COGS: {pnl_current['expenses']:.2f}")
    lines.append(f"  Net_Profit: {pnl_current['net_profit']:.2f}")
    lines.append("")
    lines.append("P&L PREVIOUS PERIOD:")
    lines.append(f"  Revenue: {pnl_prev['revenue']:.2f}")
    lines.append(f"  Expenses_incl_COGS: {pnl_prev['expenses']:.2f}")
    lines.append(f"  Net_Profit: {pnl_prev['net_profit']:.2f}")
    lines.append("")
    lines.append("DAILY_REVENUE_CURRENT_PERIOD:")
    if not daily_rows:
        lines.append("  NO_DAILY_REVENUE_DATA")
    else:
        for r in daily_rows:
            day, revenue_net, tax_amount, total_amount = r
            lines.append(
                f"  {day}: net_revenue={float(revenue_net):.2f}, tax={float(tax_amount):.2f}, total={float(total_amount):.2f}"
            )
    lines.append("")
    lines.append("TOP_PRODUCTS_CURRENT_PERIOD (by net revenue):")
    if not top_rows:
        lines.append("  NO_PRODUCT_DATA")
    else:
        for r in top_rows:
            product_name, qty, revenue_net, total_amount = r
            lines.append(
                f"  {product_name}: qty={float(qty):.0f}, net_revenue={float(revenue_net):.2f}, total_amount={float(total_amount):.2f}"
            )

    return "\n".join(lines)


def ask_business_question(question: str, start_date: date, end_date: date):
    if client is None:
        raise RuntimeError("OPENAI_API_KEY is not configured in .env")

    context_text = build_business_context(question, start_date, end_date)

    system_message = (
        "You are VUNNAM's financial intelligence assistant for small businesses. "
        "You ONLY use the numeric business data provided in the DATA section. "
        "You do NOT make up any new numbers. If you do not have enough data to answer, "
        "you must clearly say 'I don't know from the available data'.\n\n"
        "Style:\n"
        "- Clear and concise.\n"
        "- Explain trends and comparisons in simple language.\n"
        "- Use bullet points where useful.\n"
    )

    user_message = f"""
Here is the business data:

DATA_START
{context_text}
DATA_END

User question: {question}

Using ONLY the data above, answer the question.
If you compare this period vs the previous period, explicitly mention increases/decreases.
If you don't have enough information, say you don't know from the available data.
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
    )

    answer = resp.choices[0].message.content
    return answer, context_text
