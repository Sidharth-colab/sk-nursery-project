import os
import psycopg2
from datetime import datetime

# --- Block 1: The Cloud Connection (Updated for Render/IPv4 Compatibility) ---
# We use port 6543 (Transaction Pooler) because port 5432 is often IPv6-only
# --- Block 1: The Cloud Connection (Neon PostgreSQL) ---
DB_URL = os.environ.get('DATABASE_URL', "postgresql://neondb_owner:npg_XNBjnH9Oep7S@ep-frosty-cake-adiwskfg-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_db_connection():
    try:
        conn = psycopg2.connect(DB_URL, connect_timeout=10)
        return conn
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        raise e

def return_connection(conn):
    if conn:
        try:
            conn.close()
        except:
            pass

def init_pool():
    print("✅ Connected to Neon via Direct Connection")

init_pool()

# --- Block 2: Database Setup (All Tables Included) ---
def create_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Plants Table (Inventory)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS plants (
         id SERIAL PRIMARY KEY,
         name TEXT NOT NULL,
         category TEXT,
         price FLOAT,
         stock INTEGER,
         min_stock INTEGER DEFAULT 2,
         unit_cost FLOAT,
         last_updated DATE,
         image_url TEXT DEFAULT ''
           )
     ''')


    cur.execute('''
         CREATE TABLE IF NOT EXISTS plants (
         id SERIAL PRIMARY KEY,
         name TEXT NOT NULL,
         category TEXT,
         price FLOAT,
         stock INTEGER,
         min_stock INTEGER DEFAULT 2,
         unit_cost FLOAT,
         last_updated DATE,
         image_url TEXT DEFAULT '',
         is_visible INTEGER DEFAULT 1
        )
    ''')

    cur.execute('''
          ALTER TABLE plants ADD COLUMN IF NOT EXISTS is_visible INTEGER DEFAULT 1
    ''')
    
    cur.execute('''
    ALTER TABLE plants ADD COLUMN IF NOT EXISTS image_url TEXT DEFAULT ''
    ''')

    # 2. Sales Table (History & Analytics)
    cur.execute('''
            CREATE TABLE IF NOT EXISTS sales (
                id SERIAL PRIMARY KEY,
                plant_name TEXT,
                category TEXT,
                quantity INTEGER,
                revenue FLOAT,
                sale_date DATE,
                month INTEGER,
                is_weekend INTEGER,
                is_festival INTEGER DEFAULT 0
            )
    ''')

    # 3. Orders Table (Customer Requests)
    cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                customer_name TEXT,
                phone TEXT,
                plant_name TEXT,
                quantity INTEGER,
                total_price FLOAT,
                status TEXT DEFAULT 'pending',
                order_date DATE
            )
    ''')

    cur.execute('''
            ALTER TABLE orders ADD COLUMN IF NOT EXISTS address TEXT DEFAULT ''
    ''')


    cur.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            description TEXT NOT NULL,
            amount FLOAT NOT NULL,
            category TEXT DEFAULT 'General',
            expense_date DATE
          )
    ''')


    
    conn.commit()
    cur.close()
    return_connection(conn)
    print("✅ All Supabase Tables (Plants, Sales, Orders) Verified!")

# --- Block 3: Sale Recording (Weekend & Month Logic) ---
def record_real_sale(plant_id, quantity):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name, category, price, stock FROM plants WHERE id = %s", (plant_id,))
        plant = cur.fetchone()

        if plant and plant[3] >= quantity:
            name, cat, price, current_stock = plant
            new_stock = current_stock - quantity
            revenue = price * quantity
            today = datetime.now().date()
            current_month = datetime.now().month
            is_weekend = 1 if datetime.now().weekday() >= 5 else 0

            cur.execute("UPDATE plants SET stock = %s, last_updated = %s WHERE id = %s", (new_stock, today, plant_id))
            cur.execute('''INSERT INTO sales (plant_name, category, quantity, revenue, sale_date, month, is_weekend)
                              VALUES (%s, %s, %s, %s, %s, %s, %s)''', (name, cat, quantity, revenue, today, current_month, is_weekend))
            conn.commit()
            return True, f"Sold {quantity} {name}(s)."
        return False, "Insufficient stock."
    finally:
        cur.close()
        return_connection(conn)

# --- Block 4: Inventory & Management Helpers ---
def get_all_plants():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name, category, price, stock, min_stock, unit_cost, image_url, is_visible FROM plants ORDER BY name")
    plants = cur.fetchall()
    cur.close()
    return_connection(conn)
    return plants

def add_new_plant(name, category, price, unit_cost, image_url=''):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        today = datetime.now().date()
        cur.execute('''INSERT INTO plants (name, category, price, stock, min_stock, unit_cost, last_updated, image_url)
                          VALUES (%s, %s, %s, 0, 2, %s, %s, %s)''', (name, category, price, unit_cost, today, image_url))
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"❌ Error adding plant: {e}")
        raise e
    finally:
        if conn:
            return_connection(conn)

def delete_plant_by_id(plant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM plants WHERE id = %s", (plant_id,))
    conn.commit()
    cur.close()
    return_connection(conn)
    return True

def update_stock_manually(plant_id, new_stock):
    conn = get_db_connection()
    cur = conn.cursor()
    today = datetime.now().date()
    cur.execute(
        "UPDATE plants SET stock = %s, last_updated = %s WHERE id = %s",
        (new_stock, today, plant_id)
    )
    conn.commit()
    cur.close()
    return_connection(conn)
    return True

def toggle_plant_visibility(plant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE plants SET is_visible = CASE WHEN is_visible = 1 THEN 0 ELSE 1 END WHERE id = %s", (plant_id,))
    conn.commit()
    cur.close()
    return_connection(conn)
    return True

# --- Block 5: Financial Reporting (Day/Month Profit) ---
def get_financial_report(period='day'):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if period == 'day':
            date_val = datetime.now().date()
            cur.execute('''SELECT SUM(s.quantity), SUM(s.revenue), SUM(s.quantity * p.unit_cost)
                           FROM sales s JOIN plants p ON s.plant_name = p.name WHERE s.sale_date = %s''', (date_val,))
        else:
            month_val = datetime.now().month
            cur.execute('''SELECT SUM(s.quantity), SUM(s.revenue), SUM(s.quantity * p.unit_cost)
                           FROM sales s JOIN plants p ON s.plant_name = p.name WHERE s.month = %s''', (month_val,))

        result = cur.fetchone()
        if not result or result[0] is None: return 0, 0, 0
        qty, rev, cost = result
        return qty, rev, (rev - cost)
    finally:
        cur.close()
        return_connection(conn)

# --- Block 6: Performance Ranking ---
def get_top_performers(limit=10):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT s.plant_name, SUM(s.quantity), SUM(s.revenue - (s.quantity * p.unit_cost)) as profit
        FROM sales s JOIN plants p ON s.plant_name = p.name
        GROUP BY s.plant_name ORDER BY profit DESC LIMIT %s
    ''', (limit,))
    data = cur.fetchall()
    cur.close()
    return_connection(conn)
    return data


# --- Block 7: Expense Tracking ---
def add_expense(description, amount, category):
    conn = get_db_connection()
    cur = conn.cursor()
    today = datetime.now().date()
    cur.execute('''INSERT INTO expenses (description, amount, category, expense_date)
                  VALUES (%s, %s, %s, %s)''', (description, amount, category, today))
    conn.commit()
    cur.close()
    return_connection(conn)
    return True

def get_expenses(period='month'):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if period == 'month':
            cur.execute('''SELECT id, description, amount, category, expense_date
                          FROM expenses
                          WHERE EXTRACT(MONTH FROM expense_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                          AND EXTRACT(YEAR FROM expense_date) = EXTRACT(YEAR FROM CURRENT_DATE)
                          ORDER BY expense_date DESC''')
        else:
            cur.execute('''SELECT id, description, amount, category, expense_date
                          FROM expenses
                          ORDER BY expense_date DESC LIMIT 50''')
        return cur.fetchall()
    finally:
        cur.close()
        return_connection(conn)

def get_total_expenses(period='month'):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if period == 'month':
            cur.execute('''SELECT COALESCE(SUM(amount), 0) FROM expenses
                          WHERE EXTRACT(MONTH FROM expense_date) = EXTRACT(MONTH FROM CURRENT_DATE)
                          AND EXTRACT(YEAR FROM expense_date) = EXTRACT(YEAR FROM CURRENT_DATE)''')
        else:
            cur.execute('SELECT COALESCE(SUM(amount), 0) FROM expenses')
        return cur.fetchone()[0]
    finally:
        cur.close()
        return_connection(conn)

def delete_expense(expense_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    cur.close()
    return_connection(conn)
    return True
    
if __name__ == "__main__":
    create_database()









