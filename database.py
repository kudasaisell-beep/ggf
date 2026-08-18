import os
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shop.db")


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance REAL DEFAULT 0,
            total_spent REAL DEFAULT 0,
            spent_today REAL DEFAULT 0,
            referrals INTEGER DEFAULT 0,
            ref_earnings REAL DEFAULT 0,
            referred_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT,
            country_name TEXT,
            account_type TEXT,
            price REAL,
            cost_price REAL,
            status TEXT DEFAULT 'available',
            data TEXT,
            item_age_days INTEGER,
            has_avatar INTEGER DEFAULT 0,
            reg_date TEXT,
            contacts_count INTEGER,
            has_premium INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            account_id INTEGER,
            price REAL,
            guarantee_until TEXT,
            is_insured INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            account_id INTEGER,
            item_id INTEGER,
            country_code TEXT,
            country_name TEXT,
            account_type TEXT,
            price REAL,
            cost_price REAL,
            item_age_days INTEGER,
            has_avatar INTEGER DEFAULT 0,
            reg_date TEXT,
            contacts_count INTEGER,
            has_premium INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: add columns to existing cart
    c.execute("PRAGMA table_info(cart)")
    existing_cols = {row["name"] for row in c.fetchall()}
    for col, ddl in [
        ("item_id", "INTEGER"),
        ("country_code", "TEXT"),
        ("country_name", "TEXT"),
        ("account_type", "TEXT"),
        ("price", "REAL"),
        ("cost_price", "REAL"),
        ("item_age_days", "INTEGER"),
        ("has_avatar", "INTEGER DEFAULT 0"),
        ("reg_date", "TEXT"),
        ("contacts_count", "INTEGER"),
        ("has_premium", "INTEGER DEFAULT 0"),
    ]:
        if col not in existing_cols:
            c.execute(f"ALTER TABLE cart ADD COLUMN {col} {ddl}")

    c.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            rating INTEGER,
            text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS prices (
            country_code TEXT,
            account_type TEXT,
            price REAL,
            PRIMARY KEY (country_code, account_type)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            full_name TEXT,
            type TEXT,
            status TEXT DEFAULT 'open',
            message TEXT,
            purchase_id INTEGER,
            admin_reply TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            country_code TEXT,
            account_type TEXT,
            subcat_key TEXT DEFAULT 'telegram',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, country_code, account_type, subcat_key)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS code_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            purchase_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS refunds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            purchase_id INTEGER,
            amount REAL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # NEW: pending_purchases
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            price REAL,
            cost_price REAL,
            account_data TEXT,
            country_code TEXT,
            country_name TEXT,
            account_type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # NEW: deposits
    c.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            receipt_file_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# ========== USERS ==========

def get_or_create_user(user_id: int, username: str = None, full_name: str = None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    if not user:
        c.execute(
            "INSERT INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        conn.commit()
        c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = c.fetchone()
    conn.close()
    return user


def get_user(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def add_balance(user_id: int, amount: float):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def deduct_balance_only(user_id: int, amount: float):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    if not row or row["balance"] < amount:
        conn.close()
        return {"ok": False, "error": "insufficient_balance"}
    c.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def refund_balance(user_id: int, amount: float):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def reset_spent_today():
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE users SET spent_today = 0")
    count = c.rowcount
    conn.commit()
    conn.close()
    return count


# ========== ACCOUNTS ==========

def get_account(account_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    row = c.fetchone()
    conn.close()
    return row




def get_account_by_id(account_id: int):
    """Alias for get_account."""
    return get_account(account_id)


def get_available_accounts(limit: int = 50):
    """Returns available accounts ordered by price."""
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM accounts
        WHERE status = 'available'
        ORDER BY price ASC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def add_account(country_code, country_name, account_type, price, cost_price, data="",
                item_age_days=None, has_avatar=False, reg_date=None,
                contacts_count=None, has_premium=False):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO accounts (country_code, country_name, account_type, price, cost_price, data,
                              item_age_days, has_avatar, reg_date, contacts_count, has_premium)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        RETURNING id
    """, (country_code, country_name, account_type, price, cost_price, data,
          item_age_days, 1 if has_avatar else 0, reg_date, contacts_count, 1 if has_premium else 0))
    account_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return account_id


def update_account_status(account_id, status):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE accounts SET status = ? WHERE id = ?", (status, account_id))
    conn.commit()
    conn.close()


def get_accounts_by_country_and_type(country_code, account_type, status='available'):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM accounts
        WHERE country_code = ? AND account_type = ? AND status = ?
        ORDER BY price ASC
    """, (country_code, account_type, status))
    rows = c.fetchall()
    conn.close()
    return rows


def get_min_price(country_code: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT MIN(price) as min_price FROM prices WHERE country_code = ?", (country_code.upper(),))
    row = c.fetchone()
    conn.close()
    return row["min_price"] if row else None


# ========== PRICES ==========

def get_all_prices():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM prices")
    rows = c.fetchall()
    conn.close()
    result = {}
    for r in rows:
        code = r["country_code"]
        if code not in result:
            result[code] = {}
        result[code][r["account_type"]] = r["price"]
    return result


def get_price(country_code: str, account_type: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT price FROM prices WHERE country_code = ? AND account_type = ?", (country_code.upper(), account_type))
    row = c.fetchone()
    conn.close()
    return row["price"] if row else None


def set_price(country_code: str, account_type: str, price: float):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO prices (country_code, account_type, price)
        VALUES (?, ?, ?)
        ON CONFLICT (country_code, account_type) DO UPDATE SET price = excluded.price
    """, (country_code.upper(), account_type, price))
    conn.commit()
    conn.close()


# ========== PURCHASES ==========

def create_pending_purchase(user_id, item_id, price, cost_price, account_data,
                            country_code, country_name, account_type):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO pending_purchases (user_id, item_id, price, cost_price, account_data,
                                       country_code, country_name, account_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        RETURNING id
    """, (user_id, item_id, price, cost_price, account_data,
          country_code, country_name, account_type))
    pending_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return pending_id


def finalize_pending_purchase(pending_id, user_id, price, cost_price, account_data,
                              country_code, country_name, account_type,
                              item_age_days=None, has_avatar=False, reg_date=None,
                              contacts_count=None, has_premium=False):
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO accounts (country_code, country_name, account_type, price, cost_price, data, status,
                                  item_age_days, has_avatar, reg_date, contacts_count, has_premium)
            VALUES (?, ?, ?, ?, ?, ?, 'sold', ?, ?, ?, ?, ?)
            RETURNING id
        """, (country_code, country_name, account_type, price, cost_price, account_data,
              item_age_days, 1 if has_avatar else 0, reg_date, contacts_count, 1 if has_premium else 0))
        account_id = c.fetchone()["id"]

        c.execute("UPDATE pending_purchases SET status = 'completed' WHERE id = ?", (pending_id,))

        guarantee_until = (datetime.now() + timedelta(hours=24)).isoformat()
        c.execute("""
            INSERT INTO purchases (user_id, account_id, price, guarantee_until)
            VALUES (?, ?, ?, ?)
        """, (user_id, account_id, price, guarantee_until))

        c.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (price, user_id))

        conn.commit()
        conn.close()
        return {"ok": True, "account_id": account_id}
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "error": str(e)}


def add_purchase(user_id, account_id, price, guarantee_hours=24, is_insured=False):
    conn = get_db()
    c = conn.cursor()
    guarantee_until = (datetime.now() + timedelta(hours=guarantee_hours)).isoformat() if not is_insured else None
    c.execute("""
        INSERT INTO purchases (user_id, account_id, price, guarantee_until, is_insured)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, account_id, price, guarantee_until, 1 if is_insured else 0))
    c.execute("UPDATE users SET total_spent = total_spent + ?, spent_today = spent_today + ? WHERE user_id = ?",
              (price, price, user_id))
    conn.commit()
    conn.close()



def create_purchase(user_id, account_id, price, guarantee_hours=24, is_insured=False):
    """Alias for add_purchase."""
    return add_purchase(user_id, account_id, price, guarantee_hours, is_insured)


def get_user_purchases(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT p.*, a.country_name, a.country_code, a.account_type, a.data,
               a.item_age_days, a.has_avatar, a.reg_date, a.contacts_count, a.has_premium
        FROM purchases p
        JOIN accounts a ON p.account_id = a.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


# ========== CART ==========

def add_to_cart(user_id, account_id=None, item_id=None, country_code=None, country_name=None,
                account_type=None, price=None, cost_price=None, item_age_days=None,
                has_avatar=False, reg_date=None, contacts_count=None, has_premium=False):
    conn = get_db()
    c = conn.cursor()
    if item_id is not None:
        c.execute("SELECT 1 FROM cart WHERE user_id = ? AND item_id = ?", (user_id, item_id))
        if c.fetchone():
            conn.close()
            return
    c.execute("""
        INSERT INTO cart (user_id, account_id, item_id, country_code, country_name, account_type,
                          price, cost_price, item_age_days, has_avatar, reg_date, contacts_count, has_premium)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, account_id, item_id, country_code, country_name, account_type,
          price, cost_price, item_age_days, 1 if has_avatar else 0, reg_date,
          contacts_count, 1 if has_premium else 0))
    conn.commit()
    conn.close()


def get_cart(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT c.*,
               COALESCE(c.country_name, a.country_name) AS country_name,
               COALESCE(c.account_type, a.account_type) AS account_type,
               COALESCE(c.price, a.price) AS price
        FROM cart c
        LEFT JOIN accounts a ON c.account_id = a.id
        WHERE c.user_id = ?
        ORDER BY c.created_at ASC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def clear_cart(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def remove_cart_item(cart_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM cart WHERE id = ?", (cart_id,))
    conn.commit()
    conn.close()


# ========== REVIEWS ==========

def add_review(user_id, rating, text):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO reviews (user_id, rating, text) VALUES (?, ?, ?)", (user_id, rating, text))
    conn.commit()
    conn.close()


def get_reviews(limit=10):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT r.*, u.username, u.full_name
        FROM reviews r
        LEFT JOIN users u ON r.user_id = u.user_id
        ORDER BY r.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_reviews_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt, COALESCE(AVG(rating), 0) as avg_rating FROM reviews")
    row = c.fetchone()
    conn.close()
    return {"count": row["cnt"], "avg": round(row["avg_rating"], 1)}


def has_user_reviewed(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT 1 FROM reviews WHERE user_id = ? LIMIT 1", (user_id,))
    row = c.fetchone()
    conn.close()
    return row is not None


# ========== LOGS ==========

def add_log(user_id, action, details=""):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)", (user_id, action, details))
    conn.commit()
    conn.close()


def get_recent_errors(limit: int = 10):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM logs WHERE action = 'error' ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


# ========== TICKETS ==========

def create_ticket(user_id: int, username: str, full_name: str, ticket_type: str, message: str, purchase_id: int = None):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tickets (user_id, username, full_name, type, message, purchase_id)
        VALUES (?, ?, ?, ?, ?, ?)
        RETURNING id
    """, (user_id, username, full_name, ticket_type, message, purchase_id))
    ticket_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return ticket_id


def get_ticket(ticket_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
    row = c.fetchone()
    conn.close()
    return row


def get_user_tickets(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def get_open_tickets():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE status IN ('open', 'waiting') ORDER BY created_at ASC")
    rows = c.fetchall()
    conn.close()
    return rows


def update_ticket_status(ticket_id: int, status: str, admin_reply: str = None):
    conn = get_db()
    c = conn.cursor()
    if admin_reply:
        c.execute("""
            UPDATE tickets SET status = ?, admin_reply = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, admin_reply, ticket_id))
    else:
        c.execute("""
            UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, ticket_id))
    conn.commit()
    conn.close()


# ========== FAVORITES ==========

def add_favorite(user_id: int, country_code: str, account_type: str, subcat_key: str = "telegram"):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO favorites (user_id, country_code, account_type, subcat_key)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (user_id, country_code, account_type, subcat_key) DO NOTHING
    """, (user_id, country_code, account_type, subcat_key))
    conn.commit()
    conn.close()


def get_favorites(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM favorites WHERE user_id = ?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows


def remove_favorite(user_id: int, country_code: str, account_type: str, subcat_key: str = "telegram"):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        DELETE FROM favorites WHERE user_id = ? AND country_code = ? AND account_type = ? AND subcat_key = ?
    """, (user_id, country_code, account_type, subcat_key))
    conn.commit()
    conn.close()


# ========== CODE REQUESTS ==========

def create_code_request(user_id: int, purchase_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO code_requests (user_id, purchase_id)
        VALUES (?, ?)
        RETURNING id
    """, (user_id, purchase_id))
    req_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return req_id


def get_pending_code_requests():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM code_requests WHERE status = 'pending' ORDER BY created_at ASC")
    rows = c.fetchall()
    conn.close()
    return rows


def update_code_request_status(req_id: int, status: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE code_requests SET status = ? WHERE id = ?", (status, req_id))
    conn.commit()
    conn.close()


# ========== REFUNDS ==========

def get_pending_refunds():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM refunds WHERE status = 'pending' ORDER BY created_at ASC")
    rows = c.fetchall()
    conn.close()
    return rows


def process_refund(refund_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM refunds WHERE id = ?", (refund_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "Refund not found"}
    if row["status"] != "pending":
        conn.close()
        return {"ok": False, "error": "Already processed"}
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (row["amount"], row["user_id"]))
    c.execute("UPDATE refunds SET status = 'completed' WHERE id = ?", (refund_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ========== DEPOSITS (NEW) ==========

def create_deposit(user_id: int, amount: float, status: str = "pending"):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO deposits (user_id, amount, status)
        VALUES (?, ?, ?)
        RETURNING id
    """, (user_id, amount, status))
    deposit_id = c.fetchone()["id"]
    conn.commit()
    conn.close()
    return deposit_id


def get_deposit(deposit_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_deposit_status(deposit_id: int, status: str):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE deposits SET status = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (status, deposit_id))
    conn.commit()
    conn.close()


# ========== STATS ==========

def get_stats():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as total_users FROM users")
    total_users = c.fetchone()["total_users"]
    c.execute("SELECT COUNT(*) as total_accounts FROM accounts WHERE status = 'available'")
    total_accounts = c.fetchone()["total_accounts"]
    c.execute("SELECT COUNT(*) as total_purchases FROM purchases")
    total_purchases = c.fetchone()["total_purchases"]
    c.execute("SELECT COALESCE(SUM(price), 0) as revenue FROM purchases")
    revenue = c.fetchone()["revenue"]
    conn.close()
    return {
        "total_users": total_users,
        "total_accounts": total_accounts,
        "total_purchases": total_purchases,
        "revenue": revenue,
    }


def get_stats_period(period: str):
    conn = get_db()
    c = conn.cursor()
    now = datetime.now()
    if period == "день":
        start = now.strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as revenue FROM purchases WHERE DATE(created_at) = ?", (start,))
    elif period == "неделя":
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as revenue FROM purchases WHERE DATE(created_at) >= ?", (start,))
    elif period == "месяц":
        start = now.strftime("%Y-%m-01")
        c.execute("SELECT COUNT(*) as cnt, COALESCE(SUM(price), 0) as revenue FROM purchases WHERE DATE(created_at) >= ?", (start,))
    else:
        conn.close()
        return None
    row = c.fetchone()
    purchases = row["cnt"] or 0
    revenue = row["revenue"] or 0

    if period == "день":
        start = now.strftime("%Y-%m-%d")
        c.execute("""
            SELECT COALESCE(SUM(a.cost_price), 0) as costs
            FROM purchases p
            JOIN accounts a ON p.account_id = a.id
            WHERE DATE(p.created_at) = ?
        """, (start,))
    elif period == "неделя":
        start = (now - timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("""
            SELECT COALESCE(SUM(a.cost_price), 0) as costs
            FROM purchases p
            JOIN accounts a ON p.account_id = a.id
            WHERE DATE(p.created_at) >= ?
        """, (start,))
    elif period == "месяц":
        start = now.strftime("%Y-%m-01")
        c.execute("""
            SELECT COALESCE(SUM(a.cost_price), 0) as costs
            FROM purchases p
            JOIN accounts a ON p.account_id = a.id
            WHERE DATE(p.created_at) >= ?
        """, (start,))
    costs_row = c.fetchone()
    costs = costs_row["costs"] or 0
    profit = revenue - costs
    conn.close()
    return {
        "period": period,
        "purchases": purchases,
        "revenue": revenue,
        "costs": costs,
        "profit": profit,
    }


# ========== TRANSACTIONS ==========

def purchase_account_tx(user_id: int, account_id: int, price: float, cost_price: float, account_data: str,
                        country_code: str, country_name: str, account_type: str,
                        item_age_days=None, has_avatar=False, reg_date=None, contacts_count=None, has_premium=False,
                        guarantee_hours=24, is_insured=False) -> dict:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("BEGIN EXCLUSIVE")
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.rollback()
            return {"ok": False, "error": "user_not_found"}
        balance = float(row["balance"])
        if balance < price:
            conn.rollback()
            return {"ok": False, "error": "insufficient_balance", "balance": balance}

        c.execute("""
            INSERT INTO accounts (country_code, country_name, account_type, price, cost_price, data, status,
                                  item_age_days, has_avatar, reg_date, contacts_count, has_premium)
            VALUES (?, ?, ?, ?, ?, ?, 'sold', ?, ?, ?, ?, ?)
            RETURNING id
        """, (country_code, country_name, account_type, price, cost_price, account_data,
              item_age_days, 1 if has_avatar else 0, reg_date, contacts_count, 1 if has_premium else 0))
        new_account_id = c.fetchone()["id"]

        c.execute("""
            UPDATE users SET balance = balance - ?, total_spent = total_spent + ?, spent_today = spent_today + ?
            WHERE user_id = ?
        """, (price, price, price, user_id))

        guarantee_until = (datetime.now() + timedelta(hours=guarantee_hours)).isoformat() if not is_insured else None
        c.execute("""
            INSERT INTO purchases (user_id, account_id, price, guarantee_until, is_insured)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
        """, (user_id, new_account_id, price, guarantee_until, 1 if is_insured else 0))
        purchase_id = c.fetchone()["id"]

        c.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                  (user_id, "purchase_tx", f"account_id={new_account_id}, price={price}, insured={is_insured}"))

        conn.commit()
        return {"ok": True, "purchase_id": purchase_id, "account_id": new_account_id}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def purchase_existing_account_tx(user_id: int, account_id: int, price: float,
                                 guarantee_hours=24, is_insured=False) -> dict:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("BEGIN EXCLUSIVE")
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = c.fetchone()
        if not row:
            conn.rollback()
            return {"ok": False, "error": "user_not_found"}
        balance = float(row["balance"])
        if balance < price:
            conn.rollback()
            return {"ok": False, "error": "insufficient_balance", "balance": balance}

        c.execute("SELECT status FROM accounts WHERE id = ?", (account_id,))
        acc = c.fetchone()
        if not acc or acc["status"] != "available":
            conn.rollback()
            return {"ok": False, "error": "account_unavailable"}

        c.execute("""
            UPDATE users SET balance = balance - ?, total_spent = total_spent + ?, spent_today = spent_today + ?
            WHERE user_id = ?
        """, (price, price, price, user_id))

        c.execute("UPDATE accounts SET status = 'sold' WHERE id = ?", (account_id,))

        guarantee_until = (datetime.now() + timedelta(hours=guarantee_hours)).isoformat() if not is_insured else None
        c.execute("""
            INSERT INTO purchases (user_id, account_id, price, guarantee_until, is_insured)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
        """, (user_id, account_id, price, guarantee_until, 1 if is_insured else 0))
        purchase_id = c.fetchone()["id"]

        c.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                  (user_id, "purchase_existing_tx", f"account_id={account_id}, price={price}"))

        conn.commit()
        return {"ok": True, "purchase_id": purchase_id}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def add_balance_tx(user_id: int, amount: float) -> dict:
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute("BEGIN EXCLUSIVE")
        c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        if not c.fetchone():
            conn.rollback()
            return {"ok": False, "error": "user_not_found"}
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        c.execute("INSERT INTO logs (user_id, action, details) VALUES (?, ?, ?)",
                  (user_id, "topup", f"amount={amount}"))
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


# ========== DEMO ==========

def seed_demo_accounts():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM accounts")
    if c.fetchone()["cnt"] > 0:
        conn.close()
        return

    countries = [
        ("US", "США", "🇺🇸", 45, 95), ("KZ", "Казахстан", "🇰🇿", 35, 75),
        ("IN", "Индия", "🇮🇳", 25, 55), ("ID", "Индонезия", "🇮🇩", 30, 65),
        ("PH", "Филиппины", "🇵🇭", 28, 60), ("VN", "Вьетнам", "🇻🇳", 32, 70),
        ("BR", "Бразилия", "🇧🇷", 40, 85), ("AR", "Аргентина", "🇦🇷", 38, 80),
        ("TR", "Турция", "🇹🇷", 42, 88), ("RO", "Румыния", "🇷🇴", 36, 78),
        ("PL", "Польша", "🇵🇱", 44, 92), ("DE", "Германия", "🇩🇪", 55, 120),
        ("GB", "Великобритания", "🇬🇧", 50, 110), ("IT", "Италия", "🇮🇹", 48, 105),
        ("ES", "Испания", "🇪🇸", 47, 100), ("FR", "Франция", "🇫🇷", 49, 108),
        ("NL", "Нидерланды", "🇳🇱", 52, 115), ("CZ", "Чехия", "🇨🇿", 43, 90),
        ("BG", "Болгария", "🇧🇬", 37, 76), ("MX", "Мексика", "🇲🇽", 41, 87),
        ("CL", "Чили", "🇨🇱", 39, 82), ("PE", "Перу", "🇵🇪", 33, 72),
        ("CO", "Колумбия", "🇨🇴", 34, 74), ("TH", "Таиланд", "🇹🇭", 46, 98),
        ("MY", "Малайзия", "🇲🇾", 44, 93), ("PK", "Пакистан", "🇵🇰", 22, 48),
        ("BD", "Бангладеш", "🇧🇩", 20, 45), ("EG", "Египет", "🇪🇬", 26, 58),
        ("MA", "Марокко", "🇲🇦", 27, 59), ("NG", "Нигерия", "🇳🇬", 24, 52),
        ("KE", "Кения", "🇰🇪", 23, 50), ("ZA", "ЮАР", "🇿🇦", 35, 77),
    ]

    for code, name, flag, p1, p2 in countries:
        for i in range(3):
            c.execute("""
                INSERT INTO accounts (country_code, country_name, account_type, price, cost_price, data,
                                      item_age_days, has_avatar, reg_date, contacts_count, has_premium)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, flag + " " + name, "samoreg", p1 + i * 5, p1 * 0.6,
                  "demo_data_" + code + "_samoreg_" + str(i),
                  30 + i * 5, 1 if i % 2 == 0 else 0, "2024-01-" + str(10 + i), 5 + i, 1 if i % 3 == 0 else 0))
            c.execute("""
                INSERT INTO accounts (country_code, country_name, account_type, price, cost_price, data,
                                      item_age_days, has_avatar, reg_date, contacts_count, has_premium)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (code, flag + " " + name, "autoreg", p2 + i * 10, p2 * 0.6,
                  "demo_data_" + code + "_autoreg_" + str(i),
                  60 + i * 10, 1, "2023-06-" + str(5 + i), 0, 1 if i % 2 == 0 else 0))

    conn.commit()
    conn.close()


def close_db():
    pass


# ========== RATE LIMIT (fallback) ==========

def check_rate_limit(user_id: int, action: str, max_count: int = 5, window_seconds: int = 60):
    conn = get_db()
    c = conn.cursor()
    since = (datetime.now() - timedelta(seconds=window_seconds)).isoformat()
    c.execute("""
        SELECT COUNT(*) as cnt FROM logs
        WHERE user_id = ? AND action = ? AND created_at >= ?
    """, (user_id, action, since))
    cnt = c.fetchone()["cnt"]
    conn.close()
    if cnt >= max_count:
        return {"ok": False, "retry_after": window_seconds}
    return {"ok": True}




def get_available_accounts(country_code=None, account_type=None, limit=20):
    conn = get_db()
    c = conn.cursor()
    if country_code and account_type:
        c.execute("""
            SELECT * FROM accounts 
            WHERE country_code = ? AND account_type = ? AND status = 'available'
            ORDER BY price ASC LIMIT ?
        """, (country_code.upper(), account_type, limit))
    elif country_code:
        c.execute("""
            SELECT * FROM accounts 
            WHERE country_code = ? AND status = 'available'
            ORDER BY price ASC LIMIT ?
        """, (country_code.upper(), limit))
    elif account_type:
        c.execute("""
            SELECT * FROM accounts 
            WHERE account_type = ? AND status = 'available'
            ORDER BY price ASC LIMIT ?
        """, (account_type, limit))
    else:
        c.execute("""
            SELECT * FROM accounts 
            WHERE status = 'available'
            ORDER BY price ASC LIMIT ?
        """, (limit,))
    rows = c.fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    seed_demo_accounts()
    print("SQLite initialized and demo accounts seeded.")
