import os
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import database
import inventory
import forecaster

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'skgreenary2026secure')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'nursery2525')

database.create_database()

# --- Login Required Decorator ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated



@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            error = "Wrong password! Try again."
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



# --- ADMIN DASHBOARD ---
@app.route('/')
@login_required
def index():
    try:
        # 1. Get Financial Stats
        d_qty, d_rev, d_profit = database.get_financial_report('day')
        m_qty, m_rev, m_profit = database.get_financial_report('month')

        # 2. Get AI Forecasts
        ai_predictions = forecaster.get_ai_inventory_advice()

        # 3. Get Low Stock Alerts
        low_stock = inventory.get_low_stock_alerts()

        # 4. Get Inventory Summary
        inv_summary = inventory.get_inventory_summary()

        # 5. Fetch last 7 days of revenue for Chart
        conn = database.get_db_connection()
        cur = conn.cursor()
        query = """
            SELECT sale_date, SUM(revenue)
            FROM sales
            GROUP BY sale_date
            ORDER BY sale_date DESC
            LIMIT 7
        """
        cur.execute(query)
        chart_data = cur.fetchall()[::-1] 
        cur.close()
        database.return_connection(conn)

        # Process labels and values safely
        labels = [row[0].strftime('%Y-%m-%d') if row[0] else "No Date" for row in chart_data] if chart_data else ["No Data"]
        values = [row[1] for row in chart_data] if chart_data else [0]

        return render_template('dashboard.html',
                               today_profit=d_profit,
                               month_profit=m_profit,
                               total_plants=inv_summary.get('total_count', 0),
                               predictions=ai_predictions,
                               low_stock=low_stock,
                               labels=labels,
                               values=values)

    except Exception as e:
        # Log the error so you can see it in Render Logs
        print(f"⚠️ Dashboard Load Error: {e}")
        
        # Fallback: Load the dashboard with Zeros/Empty lists so it doesn't 500
        return render_template('dashboard.html',
                               today_profit=0,
                               month_profit=0,
                               total_plants=0,
                               predictions=[],
                               low_stock=[],
                               labels=["No Data"],
                               values=[0])

# --- INVENTORY MANAGEMENT ---

@app.route('/manage')
@login_required
def manage():
    """Allows Mom to see the full list of plants and manage them visually."""
    all_plants = database.get_all_plants()
    return render_template('inventory.html', plants=all_plants)

@app.route('/add_plant', methods=['POST'])
@login_required
def add_plant():
    """Web form for adding new plants."""
    name = request.form.get('name')
    cat = request.form.get('category')
    price = float(request.form.get('price'))
    cost = float(request.form.get('cost'))
    database.add_new_plant(name, cat, price, cost)
    return redirect(url_for('manage'))

@app.route('/update_stock', methods=['POST'])
@login_required
def update_stock():
    """Web form for updating stock."""
    p_id = int(request.form.get('id'))
    qty = int(request.form.get('qty'))
    database.update_stock_manually(p_id, qty)
    return redirect(url_for('manage'))

@app.route('/delete/<int:id>')
@login_required
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


@app.route('/run-simulator-sk2026')
def run_simulator():
    try:
        import simulator
        simulator.run_simulation()
        return "✅ Simulation complete! 180 days of sales data generated."
    except Exception as e:
        return f"❌ Error: {e}"


if __name__ == '__main__':
    app.run(debug=True)





