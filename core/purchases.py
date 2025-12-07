# core/purchases.py
from datetime import datetime
from typing import List, Dict

from core.db import get_connection
from core.accounting import record_purchase_invoice


# ---------- SUPPLIERS ----------

def create_supplier(name: str, contact: str = None, phone: str = None,
                    email: str = None, notes: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO suppliers (name, contact, phone, email, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, contact, phone, email, notes),
    )
    conn.commit()
    conn.close()


def list_suppliers():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM suppliers ORDER BY name;")
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- PURCHASE INVOICES ----------

def create_purchase_invoice(
    supplier_id: int,
    invoice_number: str,
    invoice_date: str,  # "YYYY-MM-DD"
    items: List[Dict],
    payment_method: str = "CASH",
    payment_status: str = "PAID",
    due_date: str = None,
):
    """
    items: list of dicts:
      {
        "product_id": int,
        "quantity": float,
        "unit_cost": float
      }
    """
    if not items:
        return None

    total_amount = 0.0
    for it in items:
        total_amount += it["quantity"] * it["unit_cost"]

    conn = get_connection()
    cur = conn.cursor()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute(
        """
        INSERT INTO purchase_invoices
        (supplier_id, invoice_number, invoice_date, total_amount,
         payment_status, payment_method, due_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            supplier_id,
            invoice_number,
            invoice_date,
            total_amount,
            payment_status,
            payment_method,
            due_date,
            now_str,
        ),
    )
    invoice_id = cur.lastrowid

    # Insert items + stock IN
    for it in items:
        qty = it["quantity"]
        cost = it["unit_cost"]
        line_total = qty * cost

        cur.execute(
            """
            INSERT INTO purchase_invoice_items
            (invoice_id, product_id, quantity, unit_cost, line_total)
            VALUES (?, ?, ?, ?, ?)
            """,
            (invoice_id, it["product_id"], qty, cost, line_total),
        )

        # Stock increase
        cur.execute(
            """
            INSERT INTO inventory_movements
            (product_id, quantity_change, reason, reference_type, reference_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                it["product_id"],
                qty,
                "PURCHASE",
                "PURCHASE_INVOICE",
                invoice_id,
            ),
        )

    conn.commit()
    conn.close()

    # Post to ledger (Inventory / Cash)
    try:
        record_purchase_invoice(invoice_id)
    except Exception as e:
        print("Error recording purchase in ledger:", e)

    return invoice_id


def list_purchase_invoices(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pi.*, s.name AS supplier_name
        FROM purchase_invoices pi
        LEFT JOIN suppliers s ON s.id = pi.supplier_id
        ORDER BY datetime(pi.created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_purchase_items(invoice_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT pii.*, p.name AS product_name
        FROM purchase_invoice_items pii
        JOIN products p ON p.id = pii.product_id
        WHERE pii.invoice_id = ?
        """,
        (invoice_id,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ---------- SUPPLIER PAYMENTS / CHECKS ----------

def record_supplier_payment(
    supplier_id: int,
    invoice_id: int,
    payment_date: str,  # "YYYY-MM-DD"
    amount: float,
    method: str,
    reference: str = None,
):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO supplier_payments
        (supplier_id, invoice_id, payment_date, amount, method, reference)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (supplier_id, invoice_id, payment_date, amount, method, reference),
    )
    conn.commit()
    conn.close()


def list_supplier_payments(limit: int = 50):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sp.*, s.name AS supplier_name,
               pi.invoice_number
        FROM supplier_payments sp
        LEFT JOIN suppliers s ON s.id = sp.supplier_id
        LEFT JOIN purchase_invoices pi ON pi.id = sp.invoice_id
        ORDER BY datetime(sp.created_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
