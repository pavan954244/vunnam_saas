# core/customers.py
from core.db import get_connection


def create_customer(name: str, phone: str = None, email: str = None,
                    birthday: str = None, notes: str = None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO customers (name, phone, email, birthday, notes)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, phone, email, birthday, notes),
    )
    conn.commit()
    conn.close()


def list_customers():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM customers
        ORDER BY datetime(created_at) DESC
        LIMIT 200
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows
