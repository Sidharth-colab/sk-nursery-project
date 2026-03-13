import logging
import asyncio
import database
import datetime
import os
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Block 0: The "Stay Awake" Flask Server ---
# This keeps the bot alive on Render's free tier
app = Flask('')


@app.route('/')
def home():
    return "SKGreenary Bot is Online!", 200

@app.route('/health')
def health():
    return "OK", 200


def run_flask():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


# --- Block 1: Bot Setup ---
TOKEN = os.environ.get('BOT_TOKEN', '8793225838:AAFNb8kz1qzVDKSnDssZ91ie17Cn5wplPa0')
OWNER_CHAT_ID = 8791438325

async def send_low_stock_alert(context, plant_name, remaining_stock):
    message = (
        f"⚠️ *Low Stock Alert!*\n\n"
        f"🌿 *{plant_name}* is running low!\n"
        f"📦 Only *{remaining_stock}* units remaining.\n\n"
        f"Please restock soon! 🙏"
    )
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=message,
        parse_mode='Markdown'
    )

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# --- Start & Main Menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'basket' not in context.user_data:
        context.user_data['basket'] = {}

    basket_count = sum(context.user_data['basket'].values())
    keyboard = [
        [InlineKeyboardButton("🏠 Indoor Plants", callback_data="cat_Indoor"),
         InlineKeyboardButton("☀️ Outdoor Plants", callback_data="cat_Outdoor")],
        [InlineKeyboardButton("🥬 Vegetables", callback_data="cat_Vegetable")],
        [InlineKeyboardButton(f"🛒 View Basket ({basket_count})", callback_data="view_basket")],
        [InlineKeyboardButton("📊 Business Report", callback_data="run_report")]
    ]

    msg = "🌿 *SKGreenary POS*\nSelect a category to start:"

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=msg,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def report(update, context):
    d_qty, d_rev, d_profit = database.get_financial_report('day')
    m_qty, m_rev, m_profit = database.get_financial_report('month')
    msg = (
        f"📊 *SKGreenary Report*\n\n"
        f"*Today:*\n"
        f"🛒 Units Sold: {d_qty}\n"
        f"💰 Revenue: ₹{d_rev}\n"
        f"📈 Profit: ₹{round(d_profit, 2)}\n\n"
        f"*This Month:*\n"
        f"🛒 Units Sold: {m_qty}\n"
        f"💰 Revenue: ₹{m_rev}\n"
        f"📈 Profit: ₹{round(m_profit, 2)}"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')


async def stock(update, context):
    low = database.get_all_plants()
    msg = "📦 *Current Stock:*\n\n"
    for p in low:
        status = "⚠️" if p[4] <= 2 else "✅"
        msg += f"{status} {p[1]}: *{p[4]}* units\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- Top Sellers Command ---
async def top(update, context):
    data = database.get_top_performers(5)
    if not data:
        await update.message.reply_text("No sales data yet!")
        return
    msg = "🏆 *Top 5 Best Sellers:*\n\n"
    for i, (name, qty, profit) in enumerate(data, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        msg += f"{medal} *{name}*\n"
        msg += f"   Sold: {qty} units | Profit: ₹{round(profit, 2)}\n\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

# --- Daily 8PM Summary ---
async def send_daily_summary(context):
    d_qty, d_rev, d_profit = database.get_financial_report('day')
    m_qty, m_rev, m_profit = database.get_financial_report('month')
    msg = (
        f"🌙 *SKGreenary Daily Summary*\n\n"
        f"*Today's Performance:*\n"
        f"🛒 Units Sold: {d_qty}\n"
        f"💰 Revenue: ₹{d_rev}\n"
        f"📈 Profit: ₹{round(d_profit, 2)}\n\n"
        f"*This Month So Far:*\n"
        f"🛒 Units Sold: {m_qty}\n"
        f"💰 Revenue: ₹{m_rev}\n"
        f"📈 Profit: ₹{round(m_profit, 2)}\n\n"
        f"Have a great evening! 🌿"
    )
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID,
        text=msg,
        parse_mode='Markdown'
    )    


# --- Weekly Monday Summary ---
async def send_weekly_summary(context):
    conn = database.get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT SUM(quantity), SUM(revenue)
            FROM sales
            WHERE sale_date >= CURRENT_DATE - INTERVAL '7 days'
        ''')
        result = cur.fetchone()
        qty = result[0] or 0
        rev = result[1] or 0

        top = database.get_top_performers(3)
        top_msg = ""
        for i, (name, q, profit) in enumerate(top, 1):
            top_msg += f"{i}. {name} — ₹{round(profit, 2)} profit\n"

        msg = (
            f"📅 *SKGreenary Weekly Summary*\n\n"
            f"🛒 Total Units Sold: {qty}\n"
            f"💰 Total Revenue: ₹{rev}\n\n"
            f"🏆 *Top Performers:*\n{top_msg}\n"
            f"Have a great week ahead! 🌿"
        )
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=msg,
            parse_mode='Markdown'
        )
    finally:
        cur.close()
        database.return_connection(conn)


# --- Counter Interface ---
async def show_plant_counter(query, plant_id, current_qty=1):
    plants = database.get_all_plants()
    # In the Supabase database.py, ID is at index 0
    p = next((x for x in plants if x[0] == plant_id), None)
    if not p: return

    total_price = p[3] * current_qty
    text = (
        f"🌿 *{p[1]}*\n"
        f"📦 Stock: {p[4]}\n"
        f"💰 Price: ₹{p[3]}\n\n"
        f"🔢 Quantity: *{current_qty}*\n"
        f"💵 Subtotal: *₹{total_price}*"
    )

    keyboard = [
        [
            InlineKeyboardButton("➖", callback_data=f"adj_{p[0]}_{current_qty - 1}"),
            InlineKeyboardButton(f"{current_qty}", callback_data="none"),
            InlineKeyboardButton("➕", callback_data=f"adj_{p[0]}_{current_qty + 1}")
        ],
        [InlineKeyboardButton(f"📥 Add to Basket", callback_data=f"add_{p[0]}_{current_qty}")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


# --- Master Callback Handler ---
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    action = data[0]

    if action == "cat":
        category = data[1]
        plants = [p for p in database.get_all_plants() if p[2] == category]
        if category == "Indoor":
            next_cat = "Outdoor"
        elif category == "Outdoor":
            next_cat = "Vegetable"
        else:
             next_cat = "Indoor"

        await query.message.reply_text(f"📋 *{category} Plants:*", parse_mode='Markdown')
        for p in plants:
            keyboard = [[InlineKeyboardButton(f"Select {p[1]}", callback_data=f"adj_{p[0]}_1")]]
            await query.message.reply_text(f"🌿 {p[1]} | ₹{p[3]}", reply_markup=InlineKeyboardMarkup(keyboard))

        chain = [[InlineKeyboardButton(f"➡️ Go to {next_cat}", callback_data=f"cat_{next_cat}")]]
        await query.message.reply_text(f"Switch category?", reply_markup=InlineKeyboardMarkup(chain))

    elif action == "adj":
        await show_plant_counter(query, int(data[1]), max(1, int(data[2])))

    elif action == "add":
        plant_id, qty = int(data[1]), int(data[2])
        context.user_data['basket'][plant_id] = context.user_data['basket'].get(plant_id, 0) + qty
        await query.message.reply_text(f"✅ Added to basket!")
        await start(update, context)

    elif action == "view":
        basket = context.user_data.get('basket', {})
        if not basket:
            await query.message.reply_text("🛒 Basket is empty!")
            return

        summary = "🛒 *CURRENT BASKET*\n"
        total = 0
        plants = database.get_all_plants()
        for p_id, qty in basket.items():
            p = next((x for x in plants if x[0] == p_id), None)
            if p:
                total += (p[3] * qty)
                summary += f"• {p[1]} x{qty} = ₹{p[3] * qty}\n"

        summary += f"\n💰 *Total: ₹{total}*"
        keyboard = [[InlineKeyboardButton("✅ CONFIRM SALE", callback_data="final")]]
        await query.message.reply_text(summary, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif action == "final":
        basket = context.user_data.get('basket', {})
        for p_id, qty in basket.items():
            database.record_real_sale(p_id, qty)
            plants = database.get_all_plants()
            plant = next((x for x in plants if x[0] == p_id), None)
            if plant:
                remaining = plant[4]
                min_stock = plant[5]
                if remaining <= min_stock:
                    await send_low_stock_alert(context, plant[1], remaining)
        context.user_data['basket'] = {}
        await query.message.reply_text("✅ *Sale Processed!* Data synced to Neon.")
        await asyncio.sleep(2)
        await start(update, context)
    

    elif action == "run":
        d_qty, d_rev, d_profit = database.get_financial_report('day')
        await query.message.reply_text(f"📊 *Today's Report*\nQty: {d_qty}\nRevenue: ₹{d_rev}\nProfit: ₹{d_profit}")


if __name__ == '__main__':
    # Start the Flask "Heartbeat" in a separate thread
    Thread(target=run_flask).start()

    # Start the Telegram Bot
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CommandHandler('stock', stock))
    application.add_handler(CommandHandler('top', top))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Schedule daily 8PM summary (IST = UTC+5:30, so 8PM IST = 14:30 UTC)
    application.job_queue.run_daily(
        send_daily_summary,
        time=datetime.time(14, 30, 0)
    )

    # Schedule weekly Monday 9AM summary (IST = UTC+5:30, so 9AM IST = 3:30 UTC)
    application.job_queue.run_daily(
         send_weekly_summary,
         time=datetime.time(3, 30, 0),
         days=(0,)  # 0 = Monday
)

    application.run_polling(drop_pending_updates=True)






