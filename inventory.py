import database  # This now handles our cloud connection pool


def get_low_stock_alerts():
    """Finds plants that are running low so Mom can reorder."""
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        # PostgreSQL uses %s for parameters, but here we are just selecting
        cur.execute("SELECT name, stock, min_stock FROM plants WHERE stock <= min_stock")
        alerts = cur.fetchall()
        return alerts
    finally:
        cur.close()
        database.return_connection(conn)


def get_inventory_summary():
    """Calculates quick stats for the Dashboard top cards."""
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        # Total Plants count (Species count)
        cur.execute("SELECT COUNT(*) FROM plants")
        total_plants = cur.fetchone()[0] or 0

        # Total stock value (Investment sitting in the garden)
        cur.execute("SELECT SUM(stock * unit_cost) FROM plants")
        investment = cur.fetchone()[0] or 0

        return {
            "total_count": total_plants,
            "total_investment": investment
        }
    finally:
        cur.close()
        database.return_connection(conn)


def update_price_by_category(category, percentage_increase):
    """Business tool: Bulk update prices (e.g., 10% hike for all Indoor plants)."""
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        # Calculate the multiplier
        multiplier = 1 + (percentage_increase / 100)

        # In PostgreSQL (Supabase), we use %s instead of ?
        cur.execute("UPDATE plants SET price = price * %s WHERE category = %s", (multiplier, category))

        conn.commit()
        return f"Updated all {category} prices by {percentage_increase}%"
    finally:
        cur.close()
        database.return_connection(conn)