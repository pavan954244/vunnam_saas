# pages/04_LedgerBook.py
import streamlit as st
from datetime import date

from core.pos import list_products, get_stock
from core.purchases import (
    create_supplier,
    list_suppliers,
    create_purchase_invoice,
    list_purchase_invoices,
    list_purchase_items,
    record_supplier_payment,
    list_supplier_payments,
)
from core.db import get_connection


if "user" not in st.session_state:
    st.warning("Please login from the main page to use VUNNAM.")
    st.stop()

st.title("📘 LedgerBook – Stock & Invoices")

tab_suppliers, tab_invoices, tab_stock, tab_payments = st.tabs(
    ["Suppliers", "Purchase Invoices", "Stock Movements", "Bill Payments"]
)

# ---------- SUPPLIERS ----------
with tab_suppliers:
    st.subheader("Suppliers / Salesmen")

    with st.expander("➕ Add Supplier / Salesman", expanded=True):
        with st.form("add_supplier_form"):
            name = st.text_input("Name *", key="sup_name")
            contact = st.text_input("Contact Person / Notes", key="sup_contact")
            phone = st.text_input("Phone", key="sup_phone")
            email = st.text_input("Email", key="sup_email")
            notes = st.text_area("Extra Notes", key="sup_notes")
            submitted = st.form_submit_button("Save Supplier")

        if submitted:
            if not name.strip():
                st.error("Name is required.")
            else:
                create_supplier(
                    name.strip(),
                    contact=contact or None,
                    phone=phone or None,
                    email=email or None,
                    notes=notes or None,
                )
                st.success(f"Supplier '{name}' created.")

    st.markdown("---")
    st.subheader("All Suppliers / Salesmen")

    suppliers = list_suppliers()
    if not suppliers:
        st.info("No suppliers yet.")
    else:
        for s in suppliers:
            st.markdown(f"**{s['name']}**")
            if s["phone"]:
                st.write(f"📞 {s['phone']}")
            if s["email"]:
                st.write(f"✉️ {s['email']}")
            if s["notes"]:
                st.caption(s["notes"])
            st.markdown("---")


# ---------- PURCHASE INVOICES ----------
with tab_invoices:
    st.subheader("Record Stock-In Invoice")

    suppliers = list_suppliers()
    products = list_products(active_only=True)

    if not products:
        st.warning("You need products before recording purchase invoices.")
    else:
        with st.form("add_invoice_form"):
            col1, col2 = st.columns(2)
            with col1:
                supplier_names = [f"{s['name']} (ID {s['id']})" for s in suppliers] or [
                    "No suppliers yet"
                ]
                supplier_ids = [s["id"] for s in suppliers] or [None]
                supplier_idx = st.selectbox(
                    "Supplier / Salesman",
                    list(range(len(supplier_names))),
                    format_func=lambda i: supplier_names[i],
                    key="inv_supplier_idx",
                )
                supplier_id = supplier_ids[supplier_idx]

                invoice_number = st.text_input(
                    "Invoice Number / Bill No.", key="inv_number"
                )
                inv_date = st.date_input("Invoice Date", date.today(), key="inv_date")
            with col2:
                due_date = st.date_input(
                    "Due Date (optional)", value=inv_date, key="inv_due"
                )
                payment_method = st.selectbox(
                    "Payment Method",
                    ["CASH", "CHECK", "BANK TRANSFER", "CARD", "OTHER"],
                    key="inv_payment_method",
                )
                payment_status = st.selectbox(
                    "Payment Status",
                    ["PAID", "UNPAID", "PARTIAL"],
                    index=0,
                    key="inv_payment_status",
                )

            st.markdown("#### Invoice Line (one product for now)")
            colp1, colp2, colp3 = st.columns([3, 1, 1])
            with colp1:
                product_names = [f"{p['name']} (ID {p['id']})" for p in products]
                product_ids = [p["id"] for p in products]
                prod_idx = st.selectbox(
                    "Product",
                    list(range(len(product_names))),
                    format_func=lambda i: product_names[i],
                    key="inv_prod_idx",
                )
                product_id = product_ids[prod_idx]
            with colp2:
                qty = st.number_input(
                    "Quantity",
                    min_value=0.0,
                    step=1.0,
                    value=1.0,
                    key="inv_qty",
                )
            with colp3:
                unit_cost = st.number_input(
                    "Unit Cost",
                    min_value=0.0,
                    step=0.5,
                    value=0.0,
                    key="inv_unit_cost",
                )

            submitted_inv = st.form_submit_button("💾 Save Purchase Invoice")

        if submitted_inv:
            if supplier_id is None:
                st.error("Please create and select a supplier first.")
            elif qty <= 0 or unit_cost <= 0:
                st.error("Quantity and Unit Cost must be > 0.")
            else:
                items = [
                    {
                        "product_id": product_id,
                        "quantity": qty,
                        "unit_cost": unit_cost,
                    }
                ]
                invoice_id = create_purchase_invoice(
                    supplier_id=supplier_id,
                    invoice_number=invoice_number or "",
                    invoice_date=inv_date.isoformat(),
                    items=items,
                    payment_method=payment_method,
                    payment_status=payment_status,
                    due_date=due_date.isoformat() if due_date else None,
                )
                st.success(f"Purchase invoice recorded with ID {invoice_id}.")

    st.markdown("---")
    st.subheader("Recent Purchase Invoices")

    invoices = list_purchase_invoices(limit=50)
    if not invoices:
        st.info("No purchase invoices yet.")
    else:
        for inv in invoices:
            header = (
                f"Invoice #{inv['invoice_number'] or inv['id']} – "
                f"{inv['supplier_name'] or 'Unknown supplier'} – "
                f"${inv['total_amount']:.2f} – {inv['invoice_date'] or inv['created_at']}"
            )
            with st.expander(header):
                st.write(f"**Payment Status:** {inv['payment_status']}")
                st.write(f"**Payment Method:** {inv['payment_method']}")
                if inv["due_date"]:
                    st.write(f"**Due Date:** {inv['due_date']}")

                items = list_purchase_items(inv["id"])
                if items:
                    st.write("**Items:**")
                    for it in items:
                        st.write(
                            f"- {it['product_name']} × {it['quantity']} "
                            f"@ ${it['unit_cost']:.2f} → ${it['line_total']:.2f}"
                        )


# ---------- STOCK MOVEMENTS ----------
with tab_stock:
    st.subheader("Recent Stock Movements")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT im.*, p.name AS product_name
        FROM inventory_movements im
        JOIN products p ON p.id = im.product_id
        ORDER BY datetime(im.created_at) DESC
        LIMIT 100
        """
    )
    rows = cur.fetchall()
    conn.close()

    if not rows:
        st.info("No stock movements yet.")
    else:
        for r in rows:
            direction = "IN" if r["quantity_change"] > 0 else "OUT"
            st.write(
                f"- {r['created_at']}: {direction} {abs(r['quantity_change']):.0f} "
                f"of **{r['product_name']}** "
                f"(reason: {r['reason'] or '-'}, ref: {r['reference_type'] or '-'} #{r['reference_id'] or '-'})"
            )


# ---------- BILL PAYMENTS / CHECKS ----------
with tab_payments:
    st.subheader("Record Bill Payment / Check")

    invoices = list_purchase_invoices(limit=100)
    suppliers = list_suppliers()

    if not invoices:
        st.warning("You need purchase invoices before recording payments.")
    else:
        with st.form("add_payment_form"):
            sup_map = {inv["id"]: inv["supplier_name"] for inv in invoices}
            inv_labels = [
                f"{inv['invoice_number'] or inv['id']} – {sup_map.get(inv['id']) or 'Unknown'} – ${inv['total_amount']:.2f}"
                for inv in invoices
            ]
            inv_ids = [inv["id"] for inv in invoices]
            idx = st.selectbox(
                "Invoice to pay",
                list(range(len(inv_labels))),
                format_func=lambda i: inv_labels[i],
                key="pay_inv_idx",
            )
            invoice_id = inv_ids[idx]
            supplier_name = sup_map.get(invoice_id)
            supplier_id = None
            for s in suppliers:
                if s["name"] == supplier_name:
                    supplier_id = s["id"]
                    break

            pay_date = st.date_input("Payment Date", date.today(), key="pay_date")
            amount = st.number_input(
                "Amount", min_value=0.0, step=1.0, key="pay_amount"
            )
            method = st.selectbox(
                "Method",
                ["CASH", "CHECK", "BANK TRANSFER", "CARD", "OTHER"],
                key="pay_method",
            )
            reference = st.text_input(
                "Reference / Check No. / Notes", key="pay_ref"
            )
            submitted_pay = st.form_submit_button("💸 Record Payment")

        if submitted_pay:
            if amount <= 0:
                st.error("Amount must be > 0.")
            else:
                record_supplier_payment(
                    supplier_id=supplier_id or None,
                    invoice_id=invoice_id,
                    payment_date=pay_date.isoformat(),
                    amount=amount,
                    method=method,
                    reference=reference or None,
                )
                st.success("Payment recorded.")

    st.markdown("---")
    st.subheader("Recent Payments")

    payments = list_supplier_payments(limit=50)
    if not payments:
        st.info("No payments recorded yet.")
    else:
        for p in payments:
            st.write(
                f"- {p['payment_date']}: ${p['amount']:.2f} via {p['method']} "
                f"to **{p['supplier_name'] or 'Unknown'}** "
                f"(Invoice {p['invoice_number'] or p['invoice_id']}, Ref: {p['reference'] or '-'})"
            )
