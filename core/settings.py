# core/settings.py
from core.db import get_connection


def get_business_settings():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM business_settings WHERE id = 1;")
    row = cur.fetchone()
    conn.close()
    return row


def update_business_settings(**fields):
    if not fields:
        return
    conn = get_connection()
    cur = conn.cursor()
    cols = []
    vals = []
    for k, v in fields.items():
        cols.append(f"{k} = ?")
        vals.append(v)
    vals.append(1)  # id = 1
    sql = f"UPDATE business_settings SET {', '.join(cols)} WHERE id = ?"
    cur.execute(sql, vals)
    conn.commit()
    conn.close()
