import logging
import asyncio
import database
from flask import Flask
from threading import Thread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Block 0: The "Stay Awake" Flask Server ---
# This keeps the bot alive on Render's free tier
app = Flask('')


@app.route('/')
def home():
    return "SKGreenary Bot is Online and Syncing with Supabase!"


def run_flask():
    app.run(host='0.0.0.0', port=8080)


# --- Block 1: Bot Setup ---
TOKEN = '8793225838:AAFNb8kz1qzVDKSnDssZ91ie17Cn5wplPa0'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# --- Start & Main Menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'basket' not in context.user_data:
        context.user_data['basket'] = {}

    basket_count = sum(context.user_data['basket'].values())
    keyboard = [
        [InlineKeyboardButton("🏠 Indoor Plants", callback_data="cat_Indoor"),
         InlineKeyboardButton("☀️ Outdoor Plants", callback_data="cat_Outdoor")],
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
        next_cat = "Outdoor" if category == "Indoor" else "Indoor"

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
        context.user_data['basket'] = {}
        await query.message.reply_text("✅ *Sale Processed!* Data synced to Supabase.")
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
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.run_polling()