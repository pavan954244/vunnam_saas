# pages/01_POS.py
import streamlit as st
from datetime import date

from core.pos import (
    list_products,
    create_product,
    update_product,
    add_inventory_movement,
    get_stock,
    create_pos_order,
    list_orders,
    get_order_items,
    list_order_payments,
    void_pos_order,
)

# Require login
if "user" not in st.session_state:
    st.warning("Please login from the main page to use VUNNAM.")
    st.stop()

st.title("🛒 POS & Inventory – VUNNAM")

tab_pos, tab_inventory, tab_orders, tab_price = st.tabs(
    ["New Sale", "Products & Stock", "Orders / Admin", "Price Check"]
)

# ------------------------------------------------
# TAB 1: NEW SALE
# ------------------------------------------------
with tab_pos:
    st.subheader("Create a New Sale")

    # --- Product selection ---
    col_search, col_stock = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "Search products by name, SKU, or barcode",
            placeholder="e.g. Coke, SKU123, 8901234567890",
            key="pos_search_query",
        )
    with col_stock:
        in_stock_only = st.checkbox(
            "Show only in-stock", value=True, key="pos_in_stock_only"
        )

    products = list_products(active_only=True)

    if search_query:
        q = search_query.lower()
        filtered = []
        for p in products:
            name = (p["name"] or "").lower()
            sku = (p["sku"] or "").lower()
            barcode = (p["barcode"] or "").lower()
            if q in name or q in sku or q in barcode:
                filtered.append(p)
        products = filtered

    if not products:
        st.info("No matching active products. Try adding products first.")
    else:
        with st.form("pos_sale_form"):
            st.markdown("#### 1) Select Products & Quantities")
            quantities = {}
            any_visible = False

            for p in products:
                stock = get_stock(p["id"])
                if in_stock_only and stock <= 0:
                    continue
                any_visible = True

                col1, col2, col3, col4 = st.columns([3, 1, 1, 1.5])
                with col1:
                    line = p["name"]
                    extra = []
                    if p["sku"]:
                        extra.append(f"SKU: {p['sku']}")
                    if p["barcode"]:
                        extra.append(f"Barcode: {p['barcode']}")
                    if extra:
                        line += " · " + " · ".join(extra)
                    st.write(line)
                    if p["category"]:
                        st.caption(p["category"])
                with col2:
                    st.text(f"${p['price']:.2f}")
                with col3:
                    st.text(f"Stock: {stock:.0f}")
                with col4:
                    max_qty = float(stock) if stock > 0 else 0.0
                    q_key = f"qty_product_{p['id']}"
                    q_val = st.number_input(
                        "Qty",
                        min_value=0.0,
                        max_value=max_qty,
                        value=0.0,
                        step=1.0,
                        key=q_key,
                    )
                    quantities[p["id"]] = q_val

            if not any_visible:
                st.info("No products to show with these filters.")

            st.markdown("#### 2) Customer & Age Check")

            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                customer_name = st.text_input("Customer Name (optional)", key="pos_customer_name")
            with col_c2:
                customer_phone = st.text_input("Customer Phone (optional)", key="pos_customer_phone")

            with col_c3:
                age_restricted = st.checkbox(
                    "Age-restricted sale (21+)", key="pos_age_restricted"
                )
                dob_str = None
                if age_restricted:
                    dob = st.date_input(
                        "Customer DOB",
                        value=date(2000, 1, 1),
                        key="pos_customer_dob",
                    )
                    dob_str = dob.isoformat()
                else:
                    dob = None

            st.markdown("#### 3) Payments")

            col_pay1, col_pay2 = st.columns(2)
            with col_pay1:
                split_payment = st.checkbox(
                    "Split payment (e.g. Cash + Card)", key="pos_split_payment"
                )

            payments = []

            if not split_payment:
                with col_pay2:
                    single_method = st.selectbox(
                        "Payment Method",
                        ["CASH", "CARD", "UPI", "BANK TRANSFER", "OTHER"],
                        key="pos_payment_method",
                    )
            else:
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    pay1_method = st.selectbox(
                        "Payment 1 Method",
                        ["CASH", "CARD", "UPI", "BANK TRANSFER", "OTHER"],
                        key="pos_pay1_method",
                    )
                    pay1_amount = st.number_input(
                        "Payment 1 Amount",
                        min_value=0.0,
                        step=0.5,
                        key="pos_pay1_amount",
                    )
                with col_p2:
                    pay2_method = st.selectbox(
                        "Payment 2 Method",
                        ["CASH", "CARD", "UPI", "BANK TRANSFER", "OTHER"],
                        key="pos_pay2_method",
                    )
                    pay2_amount = st.number_input(
                        "Payment 2 Amount",
                        min_value=0.0,
                        step=0.5,
                        key="pos_pay2_amount",
                    )

            submitted = st.form_submit_button("✅ Checkout & Create Sale")

        # --- form handler ---
        if submitted:
            # Build items list
            items = []
            for p in products:
                q = quantities.get(p["id"], 0.0)
                if q and q > 0:
                    items.append(
                        {
                            "product_id": p["id"],
                            "quantity": q,
                            "unit_price": p["price"],
                            "tax_rate": p["tax_rate"] or 0.0,
                        }
                    )

            if not items:
                st.error("Please select at least one product with quantity > 0.")
            else:
                # Compute total for validation
                total_amount = 0.0
                total_tax = 0.0
                for it in items:
                    sub = it["unit_price"] * it["quantity"]
                    tax = sub * (it["tax_rate"] / 100.0)
                    total_amount += sub + tax
                    total_tax += tax

                # Age check
                if age_restricted:
                    if not dob:
                        st.error("Please provide DOB for age-restricted sale.")
                        st.stop()
                    today = date.today()
                    age_years = (
                        today.year
                        - dob.year
                        - ((today.month, today.day) < (dob.month, dob.day))
                    )
                    if age_years < 21:
                        st.error(
                            f"Customer age is {age_years}. Cannot process age-restricted sale (needs 21+)."
                        )
                        st.stop()

                # Payments
                if not split_payment:
                    payments = [{"method": single_method, "amount": total_amount}]
                else:
                    payments = []
                    if pay1_amount > 0:
                        payments.append(
                            {"method": pay1_method, "amount": float(pay1_amount)}
                        )
                    if pay2_amount > 0:
                        payments.append(
                            {"method": pay2_method, "amount": float(pay2_amount)}
                        )

                    if not payments:
                        st.error(
                            "Please enter at least one payment amount when split payment is enabled."
                        )
                        st.stop()

                    paid_total = sum(p["amount"] for p in payments)
                    if abs(paid_total - total_amount) > 0.01:
                        st.error(
                            f"Split payments (${paid_total:.2f}) do not match sale total (${total_amount:.2f})."
                        )
                        st.stop()

                # Create order
                order_id = create_pos_order(
                    items,
                    customer_name=customer_name or None,
                    customer_phone=customer_phone or None,
                    age_checked=age_restricted,
                    customer_dob=dob_str,
                    payments=payments,
                )
                st.success(
                    f"Sale created! Order ID: {order_id} | Total: ${total_amount:.2f}"
                )
                if age_restricted:
                    st.info("Age check verified and stored with this sale.")


# ------------------------------------------------
# TAB 2: PRODUCTS & STOCK
# ------------------------------------------------
with tab_inventory:
    st.subheader("Product Catalog")

    # Add product
    with st.expander("➕ Add New Product", expanded=True):
        with st.form("add_product_form"):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Product Name *", key="inv_new_name")
                price = st.number_input(
                    "Selling Price *", min_value=0.0, step=0.5, key="inv_new_price"
                )
                cost_price = st.number_input(
                    "Cost Price", min_value=0.0, step=0.5, key="inv_new_cost"
                )
            with col2:
                sku = st.text_input("SKU", key="inv_new_sku")
                barcode = st.text_input("Barcode", key="inv_new_barcode")
                category = st.text_input("Category", key="inv_new_category")
                tax_rate = st.number_input(
                    "Tax Rate (%)",
                    min_value=0.0,
                    max_value=100.0,
                    value=0.0,
                    step=0.5,
                    key="inv_new_tax",
                )

            submitted_product = st.form_submit_button("💾 Save Product")

        if submitted_product:
            if not name or price <= 0:
                st.error("Please provide at least a Product Name and Selling Price.")
            else:
                create_product(
                    name=name,
                    price=price,
                    sku=sku or None,
                    barcode=barcode or None,
                    cost_price=cost_price or None,
                    category=category or None,
                    tax_rate=tax_rate or 0.0,
                )
                st.success(f"Product '{name}' created.")

    st.markdown("---")
    st.subheader("Existing Products")

    col_s2, col_active = st.columns([3, 1])
    with col_s2:
        inv_search_query = st.text_input(
            "Search products (name, SKU, barcode)", key="inv_search_query"
        )
    with col_active:
        show_only_active = st.checkbox(
            "Show only active", value=True, key="inv_show_only_active"
        )

    products_all = list_products(active_only=show_only_active)

    if inv_search_query:
        q2 = inv_search_query.lower()
        filtered2 = []
        for p in products_all:
            name = (p["name"] or "").lower()
            sku = (p["sku"] or "").lower()
            barcode = (p["barcode"] or "").lower()
            if q2 in name or q2 in sku or q2 in barcode:
                filtered2.append(p)
        products_all = filtered2

    if not products_all:
        st.info("No products found.")
    else:
        for p in products_all:
            stock = get_stock(p["id"])
            col1, col2, col3, col4, col5 = st.columns([3, 1.5, 1.5, 1.8, 1.2])
            with col1:
                line = p["name"]
                extra = []
                if p["sku"]:
                    extra.append(f"SKU: {p['sku']}")
                if p["barcode"]:
                    extra.append(f"Barcode: {p['barcode']}")
                if extra:
                    line += " · " + " · ".join(extra)
                st.markdown(f"**{line}**")
                if p["category"]:
                    st.caption(p["category"])
            with col2:
                st.text(f"Selling: ${p['price']:.2f}")
                if p["cost_price"] is not None:
                    st.caption(f"Cost: ${p['cost_price']:.2f}")
            with col3:
                st.text(f"Stock: {stock:.0f}")
                st.caption(f"Tax: {p['tax_rate'] or 0:.1f}%")
            with col4:
                with st.form(f"stock_form_{p['id']}"):
                    qty_change = st.number_input(
                        "Adj. Qty",
                        step=1.0,
                        value=0.0,
                        key=f"inv_adj_{p['id']}",
                    )
                    reason = st.text_input(
                        "Reason",
                        value="Manual adjustment",
                        key=f"inv_reason_{p['id']}",
                    )
                    if st.form_submit_button("Update Stock", use_container_width=True):
                        if qty_change != 0:
                            add_inventory_movement(p["id"], qty_change, reason=reason)
                            st.success("Stock updated.")
                        else:
                            st.warning("Quantity change is 0.")
            with col5:
                if p["is_active"]:
                    if st.button("Deactivate", key=f"inv_deact_{p['id']}"):
                        update_product(p["id"], is_active=0)
                        st.success("Product deactivated.")
                else:
                    if st.button("Activate", key=f"inv_act_{p['id']}"):
                        update_product(p["id"], is_active=1)
                        st.success("Product activated.")

        st.caption("Deactivating hides a product from POS but keeps history.")


# ------------------------------------------------
# TAB 3: ORDERS / ADMIN (void, reprint, payments)
# ------------------------------------------------
with tab_orders:
    st.subheader("Recent POS Orders & Admin Tools")

    orders = list_orders(limit=50)
    if not orders:
        st.info("No orders yet.")
    else:
        for o in orders:
            status_badge = "VOID" if o["voided"] else o["payment_status"]
            header = (
                f"Order #{o['id']} – ${o['total_amount']:.2f} – "
                f"{o['payment_method']} – {o['created_at']} – [{status_badge}]"
            )
            with st.expander(header):
                if o["customer_name"]:
                    st.write(
                        f"**Customer:** {o['customer_name']} "
                        f"{'('+o['customer_phone']+')' if o['customer_phone'] else ''}"
                    )

                if o["voided"]:
                    st.error(f"This order is VOID. Reason: {o['void_reason'] or '-'}")
                else:
                    st.write(f"**Status:** {o['payment_status']}")

                st.write(f"**Total Tax:** ${o['total_tax']:.2f}")

                # Line items (receipt style)
                items = get_order_items(o["id"])
                if items:
                    st.markdown("**Receipt View:**")
                    st.text("Item                    Qty   Price    Total")
                    st.text("---------------------------------------------")
                    for it in items:
                        line = f"{it['product_name'][:20]:20} {it['quantity']:>3.0f}  ${it['unit_price']:>6.2f}  ${it['line_total']:>7.2f}"
                        st.text(line)

                # Payments
                pays = list_order_payments(o["id"])
                if pays:
                    st.markdown("**Payments:**")
                    for p in pays:
                        st.write(
                            f"- {p['payment_method']}: ${p['amount']:.2f} ({p['created_at']})"
                        )

                st.markdown("---")
                st.markdown("**Admin Actions:**")

                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    if not o["voided"]:
                        void_reason = st.text_input(
                            f"Void reason for order {o['id']}",
                            key=f"void_reason_{o['id']}",
                        )
                        if st.button(
                            f"🛑 Void Order #{o['id']}",
                            key=f"void_btn_{o['id']}",
                        ):
                            void_pos_order(o["id"], reason=void_reason or "")
                            st.success("Order voided. Stock and ledger reversed.")
                            st.experimental_rerun()
                with col_a2:
                    st.info(
                        "To reprint, use the receipt view above. "
                        "You can copy it into your physical receipt printer."
                    )


# ------------------------------------------------
# TAB 4: PRICE CHECK
# ------------------------------------------------
with tab_price:
    st.subheader("Quick Price Check")

    products_all = list_products(active_only=False)

    q = st.text_input(
        "Search by name, SKU, or barcode",
        placeholder="Type at least 2 characters...",
        key="price_check_q",
    )

    if not q or len(q) < 2:
        st.info("Type at least 2 characters to search.")
    else:
        ql = q.lower()
        results = []
        for p in products_all:
            name = (p["name"] or "").lower()
            sku = (p["sku"] or "").lower()
            barcode = (p["barcode"] or "").lower()
            if ql in name or ql in sku or ql in barcode:
                results.append(p)

        if not results:
            st.warning("No matching products.")
        else:
            for p in results:
                stock = get_stock(p["id"])
                st.markdown(f"**{p['name']}**")
                if p["sku"]:
                    st.caption(f"SKU: {p['sku']}")
                if p["barcode"]:
                    st.caption(f"Barcode: {p['barcode']}")
                st.write(f"Selling Price: **${p['price']:.2f}**")
                if p["cost_price"] is not None:
                    st.caption(f"Cost Price: ${p['cost_price']:.2f}")
                st.caption(f"Current Stock: {stock:.0f}")
                st.markdown("---")
