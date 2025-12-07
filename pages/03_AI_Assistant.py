# pages/03_AI_Assistant.py
import streamlit as st
from datetime import date

from core.ai_engine import ask_business_question, is_ai_configured

if "user" not in st.session_state:
    st.warning("Please login from the main page to use VUNNAM.")
    st.stop()

st.title("🤖 AI Financial Assistant – VUNNAM")

if not is_ai_configured():
    st.error(
        "AI is not configured. Set OPENAI_API_KEY in your .env file and restart the app."
    )
    st.stop()

st.write("Ask natural questions about your business, like:")
st.code(
    '"Why is my profit lower this month?"\n'
    '"Which products drive most of my revenue?"\n'
    '"How did I perform in the last 7 days?"'
)

st.markdown("---")

today = date.today()
default_start = today.replace(day=1)
default_end = today

c1, c2 = st.columns(2)
with c1:
    start_date = st.date_input("Start Date", default_start)
with c2:
    end_date = st.date_input("End Date", default_end)

if start_date > end_date:
    st.error("Start date cannot be after end date.")
    st.stop()

question = st.text_area(
    "Your question",
    placeholder="Type a question like 'Why is my profit lower compared to last month?'",
    height=80,
)

if "ai_history" not in st.session_state:
    st.session_state["ai_history"] = []  # [{question, answer, context, period}]

if st.button("Ask VUNNAM AI"):
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        with st.spinner("Thinking with your real business data..."):
            try:
                answer, ctx = ask_business_question(
                    question.strip(), start_date, end_date
                )
                st.session_state["ai_history"].insert(
                    0,
                    {
                        "question": question.strip(),
                        "answer": answer,
                        "context": ctx,
                        "period": (start_date, end_date),
                    },
                )
            except Exception as e:
                st.error(f"Error while calling AI: {e}")

st.markdown("---")
st.subheader("Conversation History")

hist = st.session_state["ai_history"]
if not hist:
    st.info("No questions yet. Ask something above.")
else:
    for i, item in enumerate(hist):
        q = item["question"]
        a = item["answer"]
        ctx = item["context"]
        s, e = item["period"]

        with st.expander(f"Q{i+1}: {q} (Period: {s} → {e})", expanded=(i == 0)):
            st.markdown("**Answer:**")
            st.write(a)

            with st.expander("🔍 View numeric data used"):
                st.text(ctx)
