# core/pos.py

from typing import List, Dict
from datetime import datetime
from core.db import get_connection
from core.accounting import record_sale_for_order, void_sale_for_order

# =========================
# PRODUCTS
# =========================

def create_product(
    name: str,
    price: float,
    sku: str = None,
    barcode: str = None,
    cost_price: float = None,
    category: str = None,
    tax_rate: float = 0.0,
    is_active: bool = True,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO products (name, price, sku, barcode, cost_price, category, tax_rate, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (name, price, sku, barcode, cost_price, category, tax_rate, 1 if is_active else 0),
    )
    conn.commit()
    conn.close()


def list_products(active_only: bool = True):
    conn = get_connection()
    cur = conn.cursor()
    if active_only:
        cur.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name;")
    else:
        cur.execute("SELECT * FROM products ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return rows


def update_product(product_id: int, **fields):
    if not fields:
        return
    conn = get_connection()
    cur = conn.cursor()
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(product_id)
    sql = f"UPDATE products SET {', '.join(cols)} WHERE id = ?"
    cur.execute(sql, vals)
    conn.commit()
    conn.close()


def delete_product(product_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()


# =========================
# INVENTORY
# =========================

def add_inventory_movement(
    product_id: int,
    quantity_change: float,
    reason: str = None,
    reference_type: str = None,
    reference_id: int = None,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO inventory_movements (product_id, quantity_change, reason, reference_type, reference_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (product_id, quantity_change, reason, reference_type, reference_id),
    )
    conn.commit()
    conn.close()


def get_stock(product_id: int) -> float:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COALESCE(SUM(quantity_change), 0) AS stock
        FROM inventory_movements
        WHERE product_id = ?
        """,
        (product_id,),
    )
    row = cur.fetchone()
    conn.close()
    return row["stock"] if row else 0.0


# =========================
# POS ORDERS & PAYMENTS
# =========================

def create_pos_order(
    items: List[Dict],
    customer_name: str = None,
    customer_phone: str = None,
    age_checked: bool = False,
    customer_dob: str = None,  # "YYYY-MM-DD"
    payments: List[Dict] | None = None,
):
    """
    items: list of dicts:
        {
          "product_id": int,
          "quantity": float,
          "unit_price": float,
          "tax_rate": float
        }

    payments: list of dicts:
        {
          "method": str,
          "amount": float
        }
    """
    if not items:
        return None

    total_amount = 0.0
    total_tax = 0.0
    line_totals = []

    for item in items:
        line_subtotal = item["unit_price"] * item["quantity"]
        tax_amount = line_subtotal * (item.get("tax_rate", 0.0) / 100.0)
        line_total = line_subtotal + tax_amount

        total_amount += line_total
        total_tax += tax_amount
        line_totals.append((line_subtotal, tax_amount, line_total))

    if not payments or len(payments) == 0:
        payments = [{"method": "CASH", "amount": total_amount}]

    # Derive payment_method summary
    methods_unique = list({p["method"] for p in payments})
    if len(methods_unique) == 1:
        payment_method_str = methods_unique[0]
    else:
        payment_method_str = "SPLIT: " + "+".join(methods_unique)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cur = conn.cursor()

    # Insert order
    cur.execute(
        """
        INSERT INTO pos_orders
        (created_at, customer_name, customer_phone, customer_dob, is_age_verified,
         total_amount, total_tax, payment_method, payment_status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_str,
            customer_name,
            customer_phone,
            customer_dob,
            1 if age_checked else 0,
            total_amount,
            total_tax,
            payment_method_str,
            "PAID",
        ),
    )
    order_id = cur.lastrowid

    # Insert line items + inventory movements
    for item, (_sub, tax_amount, line_total) in zip(items, line_totals):
        cur.execute(
            """
            INSERT INTO pos_order_items (order_id, product_id, quantity, unit_price, tax_rate, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                item["product_id"],
                item["quantity"],
                item["unit_price"],
                item.get("tax_rate", 0.0),
                line_total,
            ),
        )

        # Inventory OUT
        cur.execute(
            """
            INSERT INTO inventory_movements (product_id, quantity_change, reason, reference_type, reference_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                item["product_id"],
                -item["quantity"],
                "SALE",
                "POS_ORDER",
                order_id,
            ),
        )

    # Insert payments
    for p in payments:
        cur.execute(
            """
            INSERT INTO pos_payments (order_id, payment_method, amount)
            VALUES (?, ?, ?)
            """,
            (order_id, p["method"], p["amount"]),
        )

    conn.commit()
    conn.close()

    # Ledger entries
    try:
        record_sale_for_order(order_id)
    except Exception as e:
        print("Error recording sale in ledger:", e)

    return order_id


def list_orders(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, created_at, customer_name, customer_phone,
               total_amount, total_tax, payment_method, payment_status,
               voided, void_reason
        FROM pos_orders
        ORDER BY datetime(created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_order_items(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT poi.*, p.name AS product_name
        FROM pos_order_items poi
        JOIN products p ON p.id = poi.product_id
        WHERE poi.order_id = ?
        """,
        (order_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_order_payments(order_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM pos_payments
        WHERE order_id = ?
        ORDER BY id
        """,
        (order_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def void_pos_order(order_id: int, reason: str = ""):
    """
    Mark order as void, put stock back IN, and reverse ledger.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pos_orders WHERE id = ?", (order_id,))
    order = cur.fetchone()
    if not order:
        conn.close()
        raise ValueError(f"Order {order_id} not found")

    if order["voided"]:
        conn.close()
        return  # already voided

    # Mark order void
    cur.execute(
        """
        UPDATE pos_orders
        SET voided = 1,
            payment_status = 'VOID',
            void_reason = ?
        WHERE id = ?
        """,
        (reason, order_id),
    )

    # Reverse inventory (put stock back IN)
    cur.execute(
        """
        SELECT * FROM pos_order_items
        WHERE order_id = ?
        """,
        (order_id,),
    )
    items = cur.fetchall()
    for it in items:
        cur.execute(
            """
            INSERT INTO inventory_movements
            (product_id, quantity_change, reason, reference_type, reference_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                it["product_id"],
                it["quantity"],  # back in
                "VOID",
                "POS_VOID",
                order_id,
            ),
        )

    conn.commit()
    conn.close()

    # Reverse ledger
    try:
        void_sale_for_order(order_id, reason=reason)
    except Exception as e:
        print("Error reversing sale in ledger:", e)
