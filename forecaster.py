import pandas as pd
from datetime import datetime
import database  # Connects to your Supabase/PostgreSQL logic

def get_ai_inventory_advice():
    """
    Analyzes historical data from Supabase to predict how many of each plant
    Mom needs to have in stock for the next 7 days.
    """
    # 1. Use the cloud connection from database.py
    conn = database.get_db_connection()

    # 2. Load historical sales into a DataFrame
    # Using PostgreSQL syntax for Supabase
    query = "SELECT plant_name, quantity, is_weekend FROM sales"

    try:
        # Utilizing pandas to read the sql query directly
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        print(f"Error reading sales from Supabase: {e}")
        return []
    finally:
        # Return the connection back to the pool
        database.return_connection(conn)

    if df.empty:
        return []

    # 3. Calculate the 'Velocity' of each plant
    summary = df.groupby('plant_name')['quantity'].sum().reset_index()

    # 4. Forecast for next 7 days
    # (Total Sold / 180 days) * 7 days = Expected Demand
    summary['demand_forecast'] = (summary['quantity'] / 180) * 7

    # 5. Add a 'Buffer' (Safety Stock)
    # AI Rule: Always keep 20% extra for unexpected customers
    summary['suggested_stock'] = (summary['demand_forecast'] * 1.2).round(0)

    # 6. Convert to a readable list for the Dashboard/Bot
    forecast_list = []
    for index, row in summary.iterrows():
        forecast_list.append({
            "plant": row['plant_name'],
            "predicted_sales": int(row['demand_forecast']),
            "order_total": int(row['suggested_stock'])
        })

    return forecast_list

if __name__ == "__main__":
    # Test the AI logic
    predictions = get_ai_inventory_advice()
    print("🤖 AI 7-DAY DEMAND FORECAST (Cloud Sync):")
    if isinstance(predictions, list):
        for p in predictions:
            print(f"🌿 {p['plant']}: Expecting {p['predicted_sales']} sales -> Maintain {p['order_total']} in stock.")
    else:
        print(predictions)