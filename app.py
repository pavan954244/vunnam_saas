# app.py
import streamlit as st
from core.db import init_db
from core.auth import login_user, register_user
from core.accounting import ensure_default_accounts

st.set_page_config(page_title="VUNNAM", page_icon="📘", layout="wide")


def inject_custom_css():
    st.markdown(
        """
        <style>
        /* =============== GLOBAL APP BACKGROUND =============== */
        .stApp {
            background: radial-gradient(circle at top left, #1d4ed8 0, #020617 40%, #0f172a 100%);
            color: #e5e7eb;
        }

        /* Remove default padding to make it tighter and more app-like */
        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* =============== SIDEBAR =============== */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #020617 0%, #111827 40%, #0b1120 100%);
            border-right: 1px solid #1e293b;
        }
        section[data-testid="stSidebar"] * {
            color: #e5e7eb !important;
        }

        /* Sidebar title / text tweaks */
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #e5e7eb !important;
        }

        /* =============== TITLES & HEADINGS =============== */
        h1, h2, h3, h4 {
            color: #e5e7eb;
        }
        h1 {
            font-weight: 800;
            letter-spacing: 0.03em;
        }

        /* Add subtle glowing underline to page title */
        h1 + p,
        h1 + div {
            position: relative;
        }
        h1 + p::after,
        h1 + div::after {
            content: "";
            position: absolute;
            left: 0;
            bottom: -10px;
            width: 80px;
            height: 3px;
            border-radius: 999px;
            background: linear-gradient(90deg, #4f46e5, #06b6d4);
            box-shadow: 0 0 8px rgba(79, 70, 229, 0.8);
        }

        /* =============== BUTTONS =============== */
        .stButton>button {
            background: linear-gradient(90deg, #4f46e5, #06b6d4);
            color: white;
            border-radius: 999px;
            border: none;
            padding: 0.45rem 1.2rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.9);
            transition: all 0.18s ease-out;
        }
        .stButton>button:hover {
            transform: translateY(-1px) scale(1.02);
            box-shadow: 0 15px 30px rgba(15, 23, 42, 0.95);
            filter: brightness(1.05);
        }
        .stButton>button:active {
            transform: translateY(0) scale(0.99);
            box-shadow: 0 4px 10px rgba(15, 23, 42, 0.8);
        }

        /* Small buttons (inside forms) */
        .stForm .stButton>button {
            padding: 0.3rem 0.9rem;
            font-size: 0.85rem;
        }

        /* =============== INPUTS / SELECTS / TEXTAREAS =============== */
        .stTextInput>div>div>input,
        .stNumberInput input,
        .stSelectbox>div>div>div>div,
        .stDateInput>div>div>input,
        .stTextArea textarea {
            background-color: #020617;
            border-radius: 0.75rem;
            border: 1px solid #1f2937;
            color: #e5e7eb;
        }
        .stTextInput>div>div>input:focus,
        .stNumberInput input:focus,
        .stSelectbox>div>div>div>div:focus,
        .stDateInput>div>div>input:focus,
        .stTextArea textarea:focus {
            outline: none;
            border: 1px solid #4f46e5;
            box-shadow: 0 0 0 1px rgba(79, 70, 229, 0.6);
        }

        label, .stMarkdown, .stCaption, p {
            color: #e5e7eb;
        }

        /* =============== TABS =============== */
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            border-radius: 999px !important;
            padding: 0.35rem 1rem !important;
            margin-right: 0.25rem !important;
            color: #9ca3af !important;
            border: 1px solid transparent !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background: radial-gradient(circle at top, #4f46e5 0, #1d4ed8 40%, #0f172a 100%) !important;
            color: #f9fafb !important;
            border-color: rgba(129, 140, 248, 0.8) !important;
            box-shadow: 0 0 15px rgba(79, 70, 229, 0.7);
        }

        /* =============== METRICS / CARDS =============== */
        [data-testid="stMetric"] {
            background: radial-gradient(circle at top left, #1e293b 0, #020617 60%);
            padding: 0.75rem 1rem;
            border-radius: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.25);
            box-shadow: 0 10px 25px rgba(15, 23, 42, 0.8);
        }

        /* Dataframe container */
        .stDataFrame {
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 16px 35px rgba(15, 23, 42, 0.9);
        }

        /* =============== EXPANDERS =============== */
        details {
            background: radial-gradient(circle at top left, rgba(79, 70, 229, 0.25), rgba(15, 23, 42, 0.98));
            border-radius: 1rem;
            border: 1px solid rgba(148, 163, 184, 0.4);
            padding: 0.3rem 0.9rem;
            margin-bottom: 0.75rem;
        }
        summary {
            color: #e5e7eb;
            font-weight: 600;
        }

        /* =============== CODE BLOCKS =============== */
        code, pre {
            background: #020617 !important;
            border-radius: 0.75rem;
            border: 1px solid #1f2937 !important;
            color: #e5e7eb !important;
        }

        /* =============== SCROLLBAR (WebKit) =============== */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #020617;
        }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(#4f46e5, #06b6d4);
            border-radius: 999px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


# Initialize DB + default accounts
init_db()
ensure_default_accounts()
inject_custom_css()


def ui_login():
    st.subheader("🔐 Login to VUNNAM")
    with st.container():
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        st.caption("Enter your registered email and password to access your business OS.")
        if st.button("Login", key="login_button"):
            user = login_user(email, password)
            if user:
                st.session_state["user"] = dict(user)
                st.success("Login Successful!")
                st.rerun()
            else:
                st.error("Invalid email or password")


def ui_register():
    st.subheader("🆕 Create your Account")
    with st.container():
        name = st.text_input("Name", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        st.caption("This will create your VUNNAM workspace. You can add products, sales and insights after login.")
        if st.button("Register", key="register_button"):
            if register_user(name, email, password):
                st.success("Account created! Please login.")
            else:
                st.error("Email already exists")


if "user" not in st.session_state:
    st.title("📘 VUNNAM — AI-Powered Business OS")
    st.caption("Colorful, audit-friendly POS + Accounting + Insights for SMBs.")

    tab1, tab2 = st.tabs(["Login", "Register"])
    with tab1:
        ui_login()
    with tab2:
        ui_register()
else:
    user = st.session_state["user"]

    with st.sidebar:
        st.markdown("### 👋 Logged in")
        st.write(f"**{user['name']}**")
        if st.button("Logout"):
            st.session_state.pop("user")
            st.rerun()
        st.markdown("---")
        st.caption("Use the page menu (📄 top-left) to navigate:\n\n- POS & Inventory\n- Insights\n- AI Assistant\n- LedgerBook")

    st.title("📘 VUNNAM – Home")
    st.write("Welcome to your AI-Powered, **colorful** Business OS.")
    st.write("Use the left sidebar or page selector to open:")
    st.markdown(
        "- 🛒 **POS & Inventory** – sell, manage stock, and record purchases\n"
        "- 📊 **Financial Insights** – revenue, profit, top products\n"
        "- 🤖 **AI Assistant** – ask natural questions about your business\n"
        "- 📘 **LedgerBook** – suppliers, purchase invoices, and payments"
    )
