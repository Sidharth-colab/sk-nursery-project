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

        # 5. All DB queries
        conn = database.get_db_connection()
        cur = conn.cursor()

        # 7-day revenue chart
        cur.execute("""
            SELECT sale_date, SUM(revenue)
            FROM sales
            GROUP BY sale_date
            ORDER BY sale_date DESC
            LIMIT 7
        """)
        chart_data = cur.fetchall()[::-1]

        # Category wise sales
        cur.execute("""
            SELECT category, SUM(revenue)
            FROM sales
            GROUP BY category
        """)
        category_data = cur.fetchall()

        # Recent 10 sales
        cur.execute("""
            SELECT plant_name, quantity, revenue, sale_date
            FROM sales
            ORDER BY sale_date DESC, id DESC
            LIMIT 10
        """)
        recent_sales = cur.fetchall()

        # Top performers
        cur.execute("""
            SELECT s.plant_name, SUM(s.quantity), SUM(s.revenue - (s.quantity * p.unit_cost)) as profit
            FROM sales s JOIN plants p ON s.plant_name = p.name
            GROUP BY s.plant_name ORDER BY profit DESC LIMIT 5
        """)
        top_plants = cur.fetchall()

        # Monthly comparison
        cur.execute("""
            SELECT SUM(revenue) FROM sales
            WHERE EXTRACT(MONTH FROM sale_date) = EXTRACT(MONTH FROM CURRENT_DATE)
            AND EXTRACT(YEAR FROM sale_date) = EXTRACT(YEAR FROM CURRENT_DATE)
        """)
        this_month_rev = cur.fetchone()[0] or 0

        cur.execute("""
            SELECT SUM(revenue) FROM sales
            WHERE EXTRACT(MONTH FROM sale_date) = EXTRACT(MONTH FROM CURRENT_DATE - INTERVAL '1 month')
            AND EXTRACT(YEAR FROM sale_date) = EXTRACT(YEAR FROM CURRENT_DATE - INTERVAL '1 month')
        """)
        last_month_rev = cur.fetchone()[0] or 0

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
                               values=values,
                               category_data=category_data,
                               recent_sales=recent_sales,
                               top_plants=top_plants,
                               this_month_rev=this_month_rev,
                               last_month_rev=last_month_rev)

    except Exception as e:
        print(f"⚠️ Dashboard Load Error: {e}")
        return render_template('dashboard.html',
                               today_profit=0,
                               month_profit=0,
                               total_plants=0,
                               predictions=[],
                               low_stock=[],
                               labels=["No Data"],
                               values=[0],
                               category_data=[],
                               recent_sales=[],
                               top_plants=[],
                               this_month_rev=0,
                               last_month_rev=0)

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
    name = request.form.get('name')
    cat = request.form.get('category')
    price = float(request.form.get('price'))
    cost = float(request.form.get('cost'))
    image_url = request.form.get('image_url', '')
    database.add_new_plant(name, cat, price, cost, image_url)
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





if __name__ == '__main__':
    app.run(debug=True)








