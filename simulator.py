import database  # Connects to your Supabase/PostgreSQL logic
import random
from datetime import datetime, timedelta

def run_simulation():
    print("🌱 Starting SKGreenary Sales Simulation on Supabase...")

    # 1. Ensure DB exists (Creates tables if they aren't there)
    database.create_database()

    conn = database.get_db_connection()
    cur = conn.cursor()

    # Get the plants from your Supabase table
    cur.execute("SELECT id, name, category, price FROM plants")
    plants = cur.fetchall()

    if not plants:
        print("❌ No plants found in Supabase! Add some plants via the Dashboard first.")
        database.return_connection(conn)
        return

    # 2. Clear old sales to start fresh (Optional - remove if you want to keep real sales)
    print("🧹 Cleaning old simulation data...")
    cur.execute("DELETE FROM sales")

    # 3. Generate 180 days of back-dated sales
    today = datetime.now()
    total_sales_count = 0

    print("📊 Generating 180 days of sales history...")
    for i in range(180, -1, -1):
        sale_date = today - timedelta(days=i)
        # PostgreSQL handles date objects directly, but we'll use the date part
        date_obj = sale_date.date()
        month_val = sale_date.month
        is_weekend = 1 if sale_date.weekday() >= 5 else 0

        # Randomly decide how many sales happened this day (0 to 5)
        daily_transactions = random.randint(0, 5)

        for _ in range(daily_transactions):
            plant = random.choice(plants)
            p_id, p_name, p_cat, p_price = plant

            qty = random.randint(1, 3)
            rev = qty * p_price

            # Using %s for PostgreSQL instead of ?
            cur.execute('''
                INSERT INTO sales (plant_name, category, quantity, revenue, sale_date, month, is_weekend)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (p_name, p_cat, qty, rev, date_obj, month_val, is_weekend))
            total_sales_count += 1

    conn.commit()
    cur.close()
    database.return_connection(conn)
    
    print(f"✅ Success! Inserted {total_sales_count} simulated sales over 180 days.")
    print("🚀 Your Dashboard and AI Forecaster are now populated with data!")

if __name__ == "__main__":
    run_simulation()
