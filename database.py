import os
import psycopg2
from psycopg2 import pool
from datetime import datetime

# --- Block 1: The Cloud Connection (Updated for Render/IPv4 Compatibility) ---
# We use port 6543 (Transaction Pooler) because port 5432 is often IPv6-only
DB_URL = os.environ.get('DATABASE_URL', "postgresql://postgres:Bh8zQ953FOfPhKTT@db.zqqvqnlwbfivvqucziuu.supabase.co:6543/postgres?pgbouncer=true")

connection_pool = None

def init_pool():
    global connection_pool
    if connection_pool is None:
        try:
            # We add connect_timeout=10 to give the network time to establish the bridge
            connection_pool = psycopg2.pool.SimpleConnectionPool(1, 10, DB_URL, connect_timeout=10)
            print("✅ Connected to Supabase via Transaction Pooler (Port 6543)")
        except Exception as e:
            print(f"❌ Connection Error during initialization: {e}")

# Try to initialize immediately on startup
init_pool()

def get_db_connection():
    global connection_pool
    # If the pool failed at startup, try to fix it now
    if connection_pool is None:
        init_pool()
        
    if connection_pool is None:
        raise Exception("Database connection pool not initialized. Check your Render Environment 'DATABASE_URL'.")
    
    return connection_pool.getconn()

def return_connection(conn):
    if connection_pool and conn:
        connection_pool.putconn(conn)

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
             min_stock INTEGER DEFAULT 5,
             unit_cost FLOAT,
             last_updated DATE
        )
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
    cur.execute("SELECT id, name, category, price, stock, min_stock, unit_cost FROM plants ORDER BY name")
    plants = cur.fetchall()
    cur.close()
    return_connection(conn)
    return plants

def add_new_plant(name, category, price, unit_cost):
    conn = get_db_connection()
    cur = conn.cursor()
    today = datetime.now().date()
    cur.execute('''INSERT INTO plants (name, category, price, stock, min_stock, unit_cost, last_updated)
                      VALUES (%s, %s, %s, 0, 5, %s, %s)''', (name, category, price, unit_cost, today))
    conn.commit()
    cur.close()
    return_connection(conn)
    return True

def delete_plant_by_id(plant_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM plants WHERE id = %s", (plant_id,))
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

if __name__ == "__main__":
    create_database()



