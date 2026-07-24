import database
import random
from datetime import datetime, timedelta

def run_simulation():
    print("🌱 Starting SKGreenary Sales Simulation (with realistic seasonal patterns)...")

    database.create_database()

    conn = database.get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, category, price FROM plants")
    plants = cur.fetchall()

    if not plants:
        print("❌ No plants found! Add some plants via the Dashboard first.")
        database.return_connection(conn)
        return

    print("🧹 Cleaning old simulation data...")
    cur.execute("DELETE FROM sales")

    # Give each plant a fixed "personality" so patterns are consistent, not random noise
    plant_profiles = {}
    for p_id, name, cat, price in plants:
        plant_profiles[p_id] = {
            "base_rate": random.uniform(0.3, 1.5),  # average units/day baseline
        }

    monsoon_months = {6, 7, 8, 9}  # Jun-Sep

    today = datetime.now()
    total_sales_count = 0

    print("📊 Generating 180 days of sales history with realistic patterns...")
    for i in range(180, -1, -1):
        sale_date = today - timedelta(days=i)
        date_obj = sale_date.date()
        month_val = sale_date.month
        is_weekend = 1 if sale_date.weekday() >= 5 else 0
        is_monsoon = 1 if month_val in monsoon_months else 0

        for p_id, p_name, p_cat, p_price in plants:
            base_rate = plant_profiles[p_id]["base_rate"]

            multiplier = 1.0
            if p_cat == "Indoor" and is_weekend:
                multiplier *= 1.8
            if p_cat in ("Outdoor", "Vegetable") and is_monsoon:
                multiplier *= 2.0

            expected_qty = base_rate * multiplier
            # Poisson gives realistic whole-number sales counts around that average
            qty_sold = min(5, max(0, round(random.gauss(expected_qty, expected_qty * 0.4 + 0.1))))

            if qty_sold > 0:
                rev = qty_sold * p_price
                cur.execute('''
                    INSERT INTO sales (plant_name, category, quantity, revenue, sale_date, month, is_weekend, is_festival)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (p_name, p_cat, qty_sold, rev, date_obj, month_val, is_weekend, is_monsoon))
                total_sales_count += 1

    conn.commit()
    cur.close()
    database.return_connection(conn)

    print(f"✅ Success! Inserted {total_sales_count} realistic simulated sales over 180 days.")
    print("🚀 Patterns: Indoor plants peak on weekends. Outdoor/Vegetables peak in monsoon (Jun-Sep).")

if __name__ == "__main__":
    run_simulation()
