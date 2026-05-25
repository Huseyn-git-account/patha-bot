"""
🖤  P A T H A  B O T  v4.0
Именной принт · Душанбе 🇹🇯
"""

import json
import logging
import os
from datetime import datetime

from telegram import ReplyKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN   = os.getenv("BOT_TOKEN", "8838090259:AAFMff5XZkaJgNQ3Q-_Akv1aVwwHbPUXhcw")
ADMIN_IDS   = {6598665549, 1270534837}
ORDERS_FILE = "patha_orders.json"
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://worker-production-1270.up.railway.app")

PRICES = {"👕 Футболка": 150, "🧥 Худи": 280}
SIZES = ["S", "M", "L", "XL", "XXL"]
PRINT_TYPES = ["🥊 Спортсмен / Боец", "👫 Парный принт", "👤 Портрет", "✍️ Только надпись", "🖼 Своё фото"]

(WELCOME, PRODUCT, SIZE, PRINT_TYPE, FIGHTER_CHOICE, CUSTOM_FIGHTER_NAME, QUOTE_CHOICE, CUSTOM_TEXT, PRINT_PHOTO, PRINT_TEXT, PHONE, CONFIRM, EDIT_MENU, EDIT_SIZE, EDIT_TEXT, EDIT_PHONE) = range(16)

# --- БД ---
def _load_db():
    if os.path.exists(ORDERS_FILE):
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"next_id": 1, "orders": {}}

def _save_db(data):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def db_add(order):
    data = _load_db()
    oid = data["next_id"]
    order.update({"id": oid, "status": "new", "created": datetime.now().strftime("%d.%m.%Y %H:%M")})
    data["orders"][str(oid)] = order
    data["next_id"] = oid + 1
    _save_db(data)
    return oid

def db_last_for_user(user_id):
    orders = [o for o in _load_db()["orders"].values() if o.get("user_id") == user_id]
    return orders[-1] if orders else None

def db_update(oid, **kwargs):
    data = _load_db()
    if str(oid) in data["orders"]:
        data["orders"][str(oid)].update(kwargs)
        _save_db(data)

# --- UI ---
def main_kb():
    return ReplyKeyboardMarkup([["🛍 Оформить заказ"], ["📸 Примеры", "📞 Контакты"], ["📦 Мой заказ"]], resize_keyboard=True)

def kb(*rows, nav=False):
    buttons = [list(r) for r in rows]
    if nav: buttons.append(["⬅️ Назад", "🏠 Меню"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# --- ХЕНДЛЕРЫ ---
async def start(update, context):
    await update.message.reply_text("🖤 PATHA · Именной принт", reply_markup=main_kb())
    return WELCOME

async def show_my_order(update, context):
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text("Заказов нет.", reply_markup=main_kb())
        return WELCOME
    
    # Кнопки для раздела заказа
    await update.message.reply_text(f"Ваш заказ #{o['id']}", reply_markup=kb(["❌ Отменить заказ"], ["🏠 Меню"]))
    return WELCOME

async def welcome_handler(update, context):
    t = update.message.text
    if t == "❌ Отменить заказ":
        o = db_last_for_user(update.message.from_user.id)
        if o and o.get("status") != "cancelled":
            db_update(o["id"], status="cancelled")
            await update.message.reply_text("🗑 Заказ отменен.", reply_markup=main_kb())
        return WELCOME
    if t == "🛍 Оформить заказ":
        await update.message.reply_text("Что заказываешь?", reply_markup=kb(["👕 Футболка", "🧥 Худи"], ["🏠 Меню"]))
        return PRODUCT
    if t == "📦 Мой заказ":
        return await show_my_order(update, context)
    return WELCOME

async def choose_product(update, context):
    context.user_data["product"] = update.message.text
    await update.message.reply_text("Выбери размер:", reply_markup=kb(SIZES, nav=True))
    return SIZE

async def choose_size(update, context):
    context.user_data["size"] = update.message.text
    await update.message.reply_text("Что печатаем?", reply_markup=kb(*[[pt] for pt in PRINT_TYPES], nav=True))
    return PRINT_TYPE

# --- ЗАПУСК ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ПРАВИЛЬНЫЙ ConversationHandler
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WELCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_handler)],
            PRODUCT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_product)],
            SIZE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_size)],
            # Остальные состояния...
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv)
    PORT = int(os.environ.get("PORT", 8443))
    app.run_webhook(listen="0.0.0.0", port=PORT, url_path=BOT_TOKEN, webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == "__main__":
    main()
