# core/db.py
import sqlite3

DB_NAME = "vunnam.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # -------- USERS (with role) --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            role TEXT DEFAULT 'ADMIN'   -- ADMIN / CASHIER (default first user: ADMIN)
        );
        """
    )

    # -------- BUSINESS SETTINGS (single row) --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS business_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            business_name TEXT,
            legal_name TEXT,
            address_line1 TEXT,
            address_line2 TEXT,
            city TEXT,
            state TEXT,
            postal_code TEXT,
            country TEXT,
            phone TEXT,
            email TEXT,
            currency TEXT DEFAULT 'INR',
            default_tax_rate REAL DEFAULT 0,
            receipt_footer TEXT
        );
        """
    )

    # Ensure one row exists
    cur.execute("SELECT id FROM business_settings WHERE id = 1;")
    if not cur.fetchone():
        cur.execute(
            """
            INSERT INTO business_settings (id, business_name, currency, receipt_footer)
            VALUES (1, 'VUNNAM Demo Store', 'INR', 'Thank you for shopping with us!')
            """
        )

    # -------- CUSTOMERS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            birthday TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            notes TEXT
        );
        """
    )

    # -------- PRODUCTS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            sku TEXT,
            barcode TEXT,
            price REAL NOT NULL DEFAULT 0,
            cost_price REAL DEFAULT 0,
            category TEXT,
            tax_rate REAL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        """
    )

    # -------- INVENTORY MOVEMENTS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS inventory_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity_change REAL NOT NULL,
            reason TEXT,
            reference_type TEXT,
            reference_id INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )

    # -------- POS ORDERS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            customer_id INTEGER,
            customer_name TEXT,
            customer_phone TEXT,
            customer_dob TEXT,
            is_age_verified INTEGER DEFAULT 0,
            total_amount REAL NOT NULL,
            total_tax REAL NOT NULL,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'PAID',
            voided INTEGER DEFAULT 0,
            void_reason TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
        """
    )

    # -------- POS ORDER ITEMS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit_price REAL NOT NULL,
            tax_rate REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES pos_orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )

    # -------- POS PAYMENTS (for split payments) --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (order_id) REFERENCES pos_orders(id)
        );
        """
    )

    # -------- LEDGER ACCOUNTS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT,
            type TEXT NOT NULL,
            is_system INTEGER NOT NULL DEFAULT 0
        );
        """
    )

    # -------- LEDGER ENTRIES --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL DEFAULT (date('now')),
            description TEXT,
            entry_type TEXT,
            reference_type TEXT,
            reference_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
        """
    )

    # -------- LEDGER ENTRY LINES --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_entry_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            account_id INTEGER NOT NULL,
            debit REAL NOT NULL DEFAULT 0,
            credit REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (entry_id) REFERENCES ledger_entries(id),
            FOREIGN KEY (account_id) REFERENCES ledger_accounts(id)
        );
        """
    )

    # -------- SUPPLIERS (vendors / salesmen) --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT,
            phone TEXT,
            email TEXT,
            notes TEXT
        );
        """
    )

    # -------- PURCHASE INVOICES --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER,
            invoice_number TEXT,
            invoice_date TEXT,
            total_amount REAL NOT NULL,
            payment_status TEXT DEFAULT 'UNPAID',
            payment_method TEXT,
            due_date TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );
        """
    )

    # -------- PURCHASE INVOICE ITEMS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            unit_cost REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES purchase_invoices(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        """
    )

    # -------- SUPPLIER PAYMENTS --------
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS supplier_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier_id INTEGER,
            invoice_id INTEGER,
            payment_date TEXT,
            amount REAL NOT NULL,
            method TEXT,
            reference TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id),
            FOREIGN KEY (invoice_id) REFERENCES purchase_invoices(id)
        );
        """
    )

    conn.commit()
    conn.close()
