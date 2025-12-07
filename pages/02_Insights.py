# pages/02_Insights.py
import streamlit as st
from datetime import date, timedelta
import pandas as pd

from core.accounting import get_pnl_between, get_ledger_stats
from core.analytics import get_daily_revenue, get_top_products

if "user" not in st.session_state:
    st.warning("Please login from the main page to use VUNNAM.")
    st.stop()

st.title("📊 Financial Insights – VUNNAM")

entries_count, lines_count = get_ledger_stats()
st.caption(
    f"Debug: {entries_count} ledger entries, {lines_count} ledger lines recorded."
)

today = date.today()
first_of_this_month = today.replace(day=1)
last_month_end = first_of_this_month - timedelta(days=1)
first_of_last_month = last_month_end.replace(day=1)

# ---------- This month vs last month ----------
colA, colB = st.columns(2)

with colA:
    st.subheader("This Month")
    pnl_this = get_pnl_between(first_of_this_month.isoformat(), today.isoformat())
    st.metric("Revenue", f"${pnl_this['revenue']:.2f}")
    st.metric("Expenses (incl. COGS)", f"${pnl_this['expenses']:.2f}")
    st.metric("Net Profit", f"${pnl_this['net_profit']:.2f}")

with colB:
    st.subheader("Last Month")
    pnl_last = get_pnl_between(first_of_last_month.isoformat(), last_month_end.isoformat())
    st.metric("Revenue", f"${pnl_last['revenue']:.2f}")
    st.metric("Expenses (incl. COGS)", f"${pnl_last['expenses']:.2f}")
    st.metric("Net Profit", f"${pnl_last['net_profit']:.2f}")

st.markdown("---")

# ---------- Custom range ----------
st.subheader("Custom Date Range Performance")

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Start Date", first_of_this_month)
with c2:
    end_date = st.date_input("End Date", today)

if start_date > end_date:
    st.error("Start date cannot be after end date.")
    st.stop()

start_str = start_date.isoformat()
end_str = end_date.isoformat()

pnl = get_pnl_between(start_str, end_str)

st.write(f"### Summary from {start_date} to {end_date}")
c1, c2, c3 = st.columns(3)
with c1:
    st.metric("Revenue", f"${pnl['revenue']:.2f}")
with c2:
    st.metric("Expenses (incl. COGS)", f"${pnl['expenses']:.2f}")
with c3:
    st.metric("Net Profit", f"${pnl['net_profit']:.2f}")

st.markdown("")

# ---------- Revenue over time ----------
st.subheader("📈 Revenue Over Time")

daily_rows = get_daily_revenue(start_str, end_str)
if not daily_rows:
    st.info("No sales in this date range yet.")
else:
    df_daily = pd.DataFrame(
        daily_rows, columns=["day", "revenue_net", "tax_amount", "total_amount"]
    )
    df_daily["day"] = pd.to_datetime(df_daily["day"])

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Net Revenue (excluding tax)")
        st.line_chart(df_daily.set_index("day")[["revenue_net"]], height=250)
    with col2:
        st.caption("Total Amount (including tax)")
        st.line_chart(df_daily.set_index("day")[["total_amount"]], height=250)

# ---------- Top Products ----------
st.subheader("🏆 Top Products by Revenue")

top_rows = get_top_products(start_str, end_str, limit=10)
if not top_rows:
    st.info("No product sales in this date range.")
else:
    df_top = pd.DataFrame(
        top_rows, columns=["product_name", "quantity", "revenue_net", "total_amount"]
    )

    st.dataframe(
        df_top.style.format(
            {
                "quantity": "{:.0f}",
                "revenue_net": "${:.2f}",
                "total_amount": "${:.2f}",
            }
        ),
        use_container_width=True,
    )

    st.caption("Top products by net revenue")
    st.bar_chart(df_top.set_index("product_name")[["revenue_net"]], height=300)
