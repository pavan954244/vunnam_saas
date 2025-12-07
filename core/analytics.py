# core/analytics.py
from core.db import get_connection


def get_daily_revenue(start_date: str, end_date: str):
    """
    Returns rows: (day, revenue_net, tax_amount, total_amount)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            date(o.created_at) AS day,
            SUM(oi.quantity * oi.unit_price) AS revenue_net,
            SUM(oi.line_total - oi.quantity * oi.unit_price) AS tax_amount,
            SUM(oi.line_total) AS total_amount
        FROM pos_orders o
        JOIN pos_order_items oi ON oi.order_id = o.id
        WHERE date(o.created_at) BETWEEN ? AND ?
        GROUP BY date(o.created_at)
        ORDER BY date(o.created_at)
        """,
        (start_date, end_date),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_top_products(start_date: str, end_date: str, limit: int = 10):
    """
    Returns rows: (product_name, quantity, revenue_net, total_amount)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 
            p.name AS product_name,
            SUM(oi.quantity) AS quantity,
            SUM(oi.quantity * oi.unit_price) AS revenue_net,
            SUM(oi.line_total) AS total_amount
        FROM pos_orders o
        JOIN pos_order_items oi ON oi.order_id = o.id
        JOIN products p ON p.id = oi.product_id
        WHERE date(o.created_at) BETWEEN ? AND ?
        GROUP BY p.id, p.name
        ORDER BY revenue_net DESC
        LIMIT ?
        """,
        (start_date, end_date, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return rows
