# core/accounting.py
from datetime import date
from core.db import get_connection

# System account definitions
SYSTEM_ACCOUNTS = [
    ("Cash", "1000", "ASSET"),
    ("Inventory", "1200", "ASSET"),
    ("COGS", "5000", "EXPENSE"),
    ("Sales Revenue", "4000", "INCOME"),
    ("Tax Payable", "2100", "LIABILITY"),
]


def ensure_default_accounts():
    """Create core system accounts if they don't exist."""
    conn = get_connection()
    cur = conn.cursor()

    for name, code, acc_type in SYSTEM_ACCOUNTS:
        cur.execute("SELECT id FROM ledger_accounts WHERE name = ?", (name,))
        row = cur.fetchone()
        if not row:
            cur.execute(
                """
                INSERT INTO ledger_accounts (name, code, type, is_system)
                VALUES (?, ?, ?, 1)
                """,
                (name, code, acc_type),
            )

    conn.commit()
    conn.close()


def get_account_id(name: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM ledger_accounts WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise ValueError(f"Account '{name}' not found. Did you run ensure_default_accounts()?")
    return row["id"]


# ---------- SALES POSTING ----------

def record_sale_for_order(order_id: int):
    """
    Create double-entry ledger for a POS sale:
      - Debit Cash (total_amount)
      - Credit Sales Revenue (net of tax)
      - Credit Tax Payable (tax)
      - Debit COGS
      - Credit Inventory
    """
    ensure_default_accounts()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM pos_orders WHERE id = ?", (order_id,))
    order = cur.fetchone()
    if not order:
        conn.close()
        raise ValueError(f"Order {order_id} not found")

    created_at = order["created_at"]
    if created_at and " " in created_at:
        entry_date_str = created_at.split(" ")[0]
    else:
        entry_date_str = created_at or date.today().isoformat()

    cur.execute(
        """
        SELECT poi.*, p.cost_price
        FROM pos_order_items poi
        JOIN products p ON p.id = poi.product_id
        WHERE poi.order_id = ?
        """,
        (order_id,),
    )
    items = cur.fetchall()

    net_revenue = 0.0
    cogs = 0.0

    for it in items:
        qty = it["quantity"]
        unit_price = it["unit_price"]
        line_net = qty * unit_price
        net_revenue += line_net

        if it["cost_price"] is not None:
            cogs += qty * it["cost_price"]

    total_amount = order["total_amount"]
    total_tax = order["total_tax"]

    description = f"POS Sale #{order_id}"
    cur.execute(
        """
        INSERT INTO ledger_entries (entry_date, description, entry_type, reference_type, reference_id)
        VALUES (?, ?, 'SALE', 'POS_ORDER', ?)
        """,
        (entry_date_str, description, order_id),
    )
    entry_id = cur.lastrowid

    acc_cash = get_account_id("Cash")
    acc_sales = get_account_id("Sales Revenue")
    acc_tax = get_account_id("Tax Payable")
    acc_cogs = get_account_id("COGS")
    acc_inventory = get_account_id("Inventory")

    def add_line(account_id, debit, credit):
        cur.execute(
            """
            INSERT INTO ledger_entry_lines (entry_id, account_id, debit, credit)
            VALUES (?, ?, ?, ?)
            """,
            (entry_id, account_id, float(debit), float(credit)),
        )

    # 1) Cash (Debit)
    add_line(acc_cash, debit=total_amount, credit=0)

    # 2) Sales Revenue (Credit)
    add_line(acc_sales, debit=0, credit=net_revenue)

    # 3) Tax Payable (Credit)
    if total_tax > 0:
        add_line(acc_tax, debit=0, credit=total_tax)

    # 4) COGS & Inventory
    if cogs > 0:
        add_line(acc_cogs, debit=cogs, credit=0)
        add_line(acc_inventory, debit=0, credit=cogs)

    conn.commit()
    conn.close()


# ---------- VOID SALE (reverse in ledger) ----------

def void_sale_for_order(order_id: int, reason: str = ""):
    """
    Reverse all ledger impact of a sale by creating opposite entries.
    """
    ensure_default_accounts()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM ledger_entries WHERE reference_type = 'POS_ORDER' AND reference_id = ?",
        (order_id,),
    )
    sale_entries = cur.fetchall()

    if not sale_entries:
        conn.close()
        return  # nothing to reverse (e.g. older data)

    for e in sale_entries:
        entry_date_str = e["entry_date"]
        desc = f"VOID {e['description']}"
        if reason:
            desc += f" (Reason: {reason})"

        cur.execute(
            """
            INSERT INTO ledger_entries (entry_date, description, entry_type, reference_type, reference_id)
            VALUES (?, ?, 'VOID_SALE', 'POS_ORDER_VOID', ?)
            """,
            (entry_date_str, desc, order_id),
        )
        new_entry_id = cur.lastrowid

        # Reverse each line
        cur2 = conn.cursor()
        cur2.execute(
            "SELECT * FROM ledger_entry_lines WHERE entry_id = ?",
            (e["id"],),
        )
        lines = cur2.fetchall()
        for l in lines:
            cur2.execute(
                """
                INSERT INTO ledger_entry_lines (entry_id, account_id, debit, credit)
                VALUES (?, ?, ?, ?)
                """,
                (
                    new_entry_id,
                    l["account_id"],
                    float(l["credit"]),
                    float(l["debit"]),
                ),
            )

    conn.commit()
    conn.close()


# ---------- PURCHASE POSTING ----------

def record_purchase_invoice(invoice_id: int):
    """
    Post a purchase invoice as:
      - Debit Inventory (total_amount)
      - Credit Cash (total_amount)
    (Assumes immediate payment from Cash for now.)
    """
    ensure_default_accounts()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM purchase_invoices WHERE id = ?", (invoice_id,))
    inv = cur.fetchone()
    if not inv:
        conn.close()
        raise ValueError(f"Purchase invoice {invoice_id} not found")

    inv_created = inv["invoice_date"] or inv["created_at"]
    if inv_created and " " in inv_created:
        entry_date_str = inv_created.split(" ")[0]
    else:
        entry_date_str = inv_created or date.today().isoformat()

    total_amount = inv["total_amount"]

    description = f"Purchase Invoice #{inv['invoice_number'] or invoice_id}"
    cur.execute(
        """
        INSERT INTO ledger_entries (entry_date, description, entry_type, reference_type, reference_id)
        VALUES (?, ?, 'PURCHASE', 'PURCHASE_INVOICE', ?)
        """,
        (entry_date_str, description, invoice_id),
    )
    entry_id = cur.lastrowid

    acc_cash = get_account_id("Cash")
    acc_inventory = get_account_id("Inventory")

    def add_line(account_id, debit, credit):
        cur.execute(
            """
            INSERT INTO ledger_entry_lines (entry_id, account_id, debit, credit)
            VALUES (?, ?, ?, ?)
            """,
            (entry_id, account_id, float(debit), float(credit)),
        )

    # Debit Inventory, Credit Cash
    add_line(acc_inventory, debit=total_amount, credit=0)
    add_line(acc_cash, debit=0, credit=total_amount)

    conn.commit()
    conn.close()


# ---------- P&L & STATS ----------

def get_pnl_between(start_date: str, end_date: str):
    """
    Return Profit & Loss totals between two dates (YYYY-MM-DD).
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.type, SUM(l.debit - l.credit) AS balance
        FROM ledger_entry_lines l
        JOIN ledger_accounts a ON a.id = l.account_id
        JOIN ledger_entries e ON e.id = l.entry_id
        WHERE e.entry_date BETWEEN ? AND ?
        GROUP BY a.type
        """,
        (start_date, end_date),
    )
    rows = cur.fetchall()
    conn.close()

    balances = {row["type"]: row["balance"] for row in rows}

    revenue = -balances.get("INCOME", 0.0)  # income is normally credit
    expenses = balances.get("EXPENSE", 0.0)

    return {
        "revenue": float(revenue),
        "expenses": float(expenses),
        "net_profit": float(revenue - expenses),
    }


def get_ledger_stats():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM ledger_entries")
    entries = cur.fetchone()["c"]
    cur.execute("SELECT COUNT(*) AS c FROM ledger_entry_lines")
    lines = cur.fetchone()["c"]
    conn.close()
    return entries, lines
