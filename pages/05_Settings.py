# pages/05_Settings.py
import streamlit as st
from datetime import date

from core.settings import get_business_settings, update_business_settings
from core.customers import create_customer, list_customers
from core.auth import is_admin

if "user" not in st.session_state:
    st.warning("Please login to use VUNNAM.")
    st.stop()

user = st.session_state["user"]
admin = is_admin(user)

st.title("⚙️ Store Settings & Customers")

tab_store, tab_customers = st.tabs(["Store Profile", "Customers"])

# ------------- STORE PROFILE -------------
with tab_store:
    st.subheader("Store / Business Profile")

    if not admin:
        st.error("Only ADMIN users can change store settings.")
        st.stop()

    bs = get_business_settings()

    with st.form("store_settings_form"):
        col1, col2 = st.columns(2)
        with col1:
            business_name = st.text_input(
                "Display Name (receipt/store header)",
                value=bs["business_name"] or "",
            )
            legal_name = st.text_input(
                "Legal Name (optional)",
                value=bs["legal_name"] or "",
            )
            phone = st.text_input("Business Phone", value=bs["phone"] or "")
            email = st.text_input("Business Email", value=bs["email"] or "")
            currency = st.text_input("Currency (e.g. INR, USD)", value=bs["currency"] or "INR")
        with col2:
            address_line1 = st.text_input("Address line 1", value=bs["address_line1"] or "")
            address_line2 = st.text_input("Address line 2", value=bs["address_line2"] or "")
            city = st.text_input("City", value=bs["city"] or "")
            state = st.text_input("State", value=bs["state"] or "")
            postal_code = st.text_input("Postal Code", value=bs["postal_code"] or "")
            country = st.text_input("Country", value=bs["country"] or "")

        default_tax_rate = st.number_input(
            "Default Tax Rate (%) for new products",
            min_value=0.0,
            max_value=100.0,
            value=float(bs["default_tax_rate"] or 0.0),
            step=0.5,
        )

        receipt_footer = st.text_area(
            "Receipt footer message",
            value=bs["receipt_footer"] or "Thank you for shopping with us!",
        )

        submitted = st.form_submit_button("💾 Save Settings")

    if submitted:
        update_business_settings(
            business_name=business_name,
            legal_name=legal_name,
            phone=phone,
            email=email,
            currency=currency,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            default_tax_rate=default_tax_rate,
            receipt_footer=receipt_footer,
        )
        st.success("Store settings updated.")


# ------------- CUSTOMERS -------------
with tab_customers:
    st.subheader("Customer Master")

    with st.expander("➕ Add Customer", expanded=True):
        with st.form("add_customer_form"):
            name = st.text_input("Customer Name *", key="cust_name")
            phone = st.text_input("Phone", key="cust_phone")
            email = st.text_input("Email", key="cust_email")
            birthday = st.date_input(
                "Birthday (optional)",
                value=date(2000, 1, 1),
                key="cust_bday",
            )
            notes = st.text_area("Notes (optional)", key="cust_notes")
            submitted_c = st.form_submit_button("Save Customer")

        if submitted_c:
            if not name.strip():
                st.error("Name is required.")
            else:
                bday_str = birthday.isoformat() if birthday else None
                create_customer(
                    name=name.strip(),
                    phone=phone or None,
                    email=email or None,
                    birthday=bday_str,
                    notes=notes or None,
                )
                st.success(f"Customer '{name}' added.")

    st.markdown("---")
    st.subheader("Recent Customers")

    customers = list_customers()
    if not customers:
        st.info("No customers yet.")
    else:
        for c in customers:
            st.markdown(f"**{c['name']}**")
            line = []
            if c["phone"]:
                line.append(c["phone"])
            if c["email"]:
                line.append(c["email"])
            if line:
                st.caption(" · ".join(line))
            if c["notes"]:
                st.caption(c["notes"])
            st.markdown("---")
