import os
from flask import Flask, render_template, request, redirect, url_for
import database
import inventory
import forecaster

app = Flask(__name__)

# --- ADMIN DASHBOARD ---
@app.route('/')
def index():
    # 1. Get Financial Stats (Preserved)
    d_qty, d_rev, d_profit = database.get_financial_report('day')
    m_qty, m_rev, m_profit = database.get_financial_report('month')

    # 2. Get AI Forecasts (Preserved)
    ai_predictions = forecaster.get_ai_inventory_advice()

    # 3. Get Low Stock Alerts (Preserved)
    low_stock = inventory.get_low_stock_alerts()

    # 4. Get Inventory Summary (Preserved)
    inv_summary = inventory.get_inventory_summary()

    # 5. Fetch last 7 days of revenue (Updated for PostgreSQL/Supabase)
    conn = database.get_db_connection()
    cur = conn.cursor()
    query = """
        SELECT sale_date, SUM(revenue)
        FROM sales
        GROUP BY sale_date
        ORDER BY sale_date DESC
        LIMIT 7
    """
    try:
        cur.execute(query)
        chart_data = cur.fetchall()[::-1] 
    except Exception as e:
        print(f"Chart Data Error: {e}")
        chart_data = []
    finally:
        cur.close()
        database.return_connection(conn)

    labels = [row[0].strftime('%Y-%m-%d') if row[0] else "No Date" for row in chart_data] if chart_data else ["No Data"]
    values = [row[1] for row in chart_data] if chart_data else [0]

    return render_template('dashboard.html',
                           today_profit=d_profit,
                           month_profit=m_profit,
                           total_plants=inv_summary['total_count'],
                           predictions=ai_predictions,
                           low_stock=low_stock,
                           labels=labels,
                           values=values)

# --- INVENTORY MANAGEMENT ---

@app.route('/manage')
def manage():
    """Allows Mom to see the full list of plants and manage them visually."""
    all_plants = database.get_all_plants()
    return render_template('inventory.html', plants=all_plants)

@app.route('/add_plant', methods=['POST'])
def add_plant():
    """Web form for adding new plants."""
    name = request.form.get('name')
    cat = request.form.get('category')
    price = float(request.form.get('price'))
    cost = float(request.form.get('cost'))
    database.add_new_plant(name, cat, price, cost)
    return redirect(url_for('manage'))

@app.route('/update_stock', methods=['POST'])
def update_stock():
    """Web form for updating stock."""
    p_id = int(request.form.get('id'))
    qty = int(request.form.get('qty'))
    database.update_stock_manually(p_id, qty)
    return redirect(url_for('manage'))

@app.route('/delete/<int:id>')
def delete_plant(id):
    """Web button for deleting plants."""
    database.delete_plant_by_id(id)
    return redirect(url_for('manage'))

# --- PUBLIC CUSTOMER STORE (Preserved) ---
@app.route('/store')
def store():
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT name, category, price, stock FROM plants WHERE stock > 0")
        public_plants = cur.fetchall()
        whatsapp_number = "919744958548"
        return render_template('store.html', plants=public_plants, phone=whatsapp_number)
    finally:
        cur.close()
        database.return_connection(conn)

if __name__ == '__main__':
    app.run(debug=True)
