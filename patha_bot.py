"""
🖤  P A T H A  B O T  v4.0
Именной принт · Душанбе 🇹🇯
"""

import json
import logging
import os
from datetime import datetime

from telegram import (
    ReplyKeyboardMarkup,
    Update,
)
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

PRICES: dict[str, int] = {
    "👕 Футболка": 150,
    "🧥 Худи":     280,
}
EXTRA_CUSTOM = 20

FIGHTERS: dict[str, list[str]] = {
    "🦅 Хабиб Нурмагомедов": [
        "I am not in this sport to make friends",
        "Занимайся, делай дело — и Всевышний даст всё",
        "Деньги приходят и уходят, а честь остаётся",
        "Alhamdulillah · The Eagle Has Landed",
    ],
    "🍀 Конор МакГрегор": [
        "Мы здесь не для участия — мы здесь, чтобы захватить всё",
        "Таланта не существует. Есть только одержимость",
        "Победители думают о победе. Проигравшие — о победителях",
        "Двойной чемпион делает всё, что хочет!",
    ],
    "⚡ Забит Магомедшарипов": [
        "The Stylebender of Eagles",
        "Born in Dagestan · Built for greatness",
        "Zabit · The Artist of MMA",
    ],
    "👑 Ислам Махачев": [
        "Islam Makhachev · The Champion",
        "Dagestan · Never stops",
        "The New Era of MMA",
        "Makhachev · The Future",
    ],
    "🐉 Арман Царукян": [
        "The Armenian Sniper",
        "Built different · Fighting for glory",
        "Tsarukyan · The Rise",
    ],
    "✏️ Свой боец  (+20 сом)": [],
}

PRINT_TYPES: list[str] = [
    "🥊 Спортсмен / Боец",
    "👫 Парный принт",
    "👤 Портрет",
    "✍️ Только надпись",
    "🖼 Своё фото",
]

SIZES: list[str] = ["S", "M", "L", "XL", "XXL"]

ORDER_STATUSES: dict[str, str] = {
    "new":        "🆕 Новый",
    "confirmed":  "✅ Принят",
    "production": "🔨 В работе",
    "ready":      "📦 Готов",
    "delivered":  "🚀 Доставлен",
    "cancelled":  "❌ Отменён",
}

(
    WELCOME, PRODUCT, SIZE, PRINT_TYPE,
    FIGHTER_CHOICE, CUSTOM_FIGHTER_NAME,
    QUOTE_CHOICE, CUSTOM_TEXT,
    PRINT_PHOTO, PRINT_TEXT,
    PHONE, CONFIRM,
    EDIT_MENU, EDIT_SIZE, EDIT_TEXT, EDIT_PHONE,
) = range(16)

def _load_db() -> dict:
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Ошибка загрузки БД: %s", exc)
    return {"next_id": 1, "orders": {}}

def _save_db(data: dict) -> None:
    tmp = ORDERS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ORDERS_FILE)
    except OSError as exc:
        logger.error("Ошибка сохранения БД: %s", exc)

def db_add(order: dict) -> int:
    data = _load_db()
    oid  = data["next_id"]
    order.update({"id": oid, "status": "new", "created": datetime.now().strftime("%d.%m.%Y %H:%M")})
    data["orders"][str(oid)] = order
    data["next_id"] = oid + 1
    _save_db(data)
    return oid

def db_get(oid: int) -> dict | None:
    return _load_db()["orders"].get(str(oid))

def db_update(oid: int, **kwargs) -> None:
    data = _load_db()
    key  = str(oid)
    if key in data["orders"]:
        data["orders"][key].update(kwargs)
        _save_db(data)

def db_all() -> list[dict]:
    return list(_load_db()["orders"].values())

def db_last_for_user(user_id: int) -> dict | None:
    orders = [o for o in db_all() if o.get("user_id") == user_id]
    return orders[-1] if orders else None

def kb(*rows, nav: bool = False) -> ReplyKeyboardMarkup:
    buttons = [list(r) for r in rows]
    if nav:
        buttons.append(["⬅️ Назад", "🏠 Меню"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [["🛍 Оформить заказ"], ["📸 Примеры", "📞 Контакты"], ["📦 Мой заказ"]],
        resize_keyboard=True,
    )

def step_header(n: int) -> str:
    return f"[ {'●' * n}{'○' * (6 - n)} ]  {n} из 6"

def fmt_order(o: dict, *, admin: bool = False) -> str:
    extra   = o.get("extra", 0)
    total   = o.get("price", 0) + extra
    photo   = "✅" if o.get("photo_id") else "❌"
    status  = ORDER_STATUSES.get(o.get("status", "new"), "🆕 Новый")
    icon    = "👕" if "Футболка" in o.get("product", "") else "🧥"
    athlete = o.get("athlete") or ""
    prod    = o.get("product", "—").replace("👕 ", "").replace("🧥 ", "")

    lines = [f"#{o['id']} · {status}", "—" * 22]
    if admin:
        lines += [
            f"👤  {o.get('name', '—')}  {o.get('username', '')}",
            f"📱  {o.get('phone', '—')}",
            f"🕐  {o.get('created', '—')}",
            "·" * 22,
        ]
    lines += [f"{icon}  {prod}  •  размер {o.get('size', '—')}", f"🎨  {o.get('print_type', '—')}"]
    if athlete and athlete not in ("—", ""):
        lines.append(f"🥊  {athlete}")
    lines += [f"📸  фото {photo}", f"✍️  {o.get('print_text', '—')}", "·" * 22, f"💰  {o.get('price', 0)} сом"]
    if extra:
        lines.append(f"➕  +{extra} сом (свой боец)")
    lines.append(f"💵  итого  {total} сом")
    return "\n".join(lines)

# ══════════════════════════════════════
# ХЕНДЛЕРЫ
# ══════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "🖤  P A T H A\nИменной принт · Душанбе\n\n"
        "👕  Футболка  —  от 150 сом\n🧥  Худи       —  от 280 сом\n\n"
        "Своя история на своей одежде ✊",
        reply_markup=main_kb(),
    )
    return WELCOME

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    
    # Блок отмены
    if t == "❌ Отменить заказ":
        o = db_last_for_user(update.message.from_user.id)
        if o and o.get("status") not in ("delivered", "cancelled"):
            db_update(o["id"], status="cancelled")
            await update.message.reply_text("🗑 Заказ успешно отменен.", reply_markup=main_kb())
            for aid in ADMIN_IDS:
                try: await context.bot.send_message(chat_id=aid, text=f"❌ Заказ #{o['id']} отменен пользователем.")
                except: pass
        else:
            await update.message.reply_text("Этот заказ уже нельзя отменить.")
        return WELCOME

    if t == "📸 Примеры":
        WORK_PHOTOS: list[dict] = [
            {"file_id": "AgACAgIAAxkBAAFKlHJqFAghVWRIUAvNxE45WcGwT5ouuQACcxtrG5MYoUhC-WLFbqAT8wEAAwIAA3kAAzsE", "caption": "🖤 PATHA · работа 1"},
            {"file_id": "AgACAgIAAxkBAAFKlIdqFAiuO64CuqaOTOueYzB5mVRZPQACdBtrG5MYoUiKZx8mcTk6bAEAAwIAA3kAAzsE", "caption": "🖤 PATHA · работа 2"},
            {"file_id": "AgACAgIAAxkBAAFKlI9qFAjJGX65sXbcOWhEwGB7W47umwACdhtrG5MYoUip2zNh8izFnAEAAwIAA3kAAzsE", "caption": "🖤 PATHA · работа 3"},
            {"file_id": "AgACAgIAAxkBAAFKlJFqFAjdytl8BxUm2HIkeQABxCv7QM4AAncbaxuTGKFILmTVTb-kR9kBAAMCAAN5AAM7BA", "caption": "🖤 PATHA · работа 4"},
        ]
        if WORK_PHOTOS:
            from telegram import InputMediaPhoto
            media = [InputMediaPhoto(media=p["file_id"], caption=p.get("caption", "")) for p in WORK_PHOTOS]
            try: await update.message.reply_media_group(media=media)
            except Exception as exc: logger.warning("Ошибка отправки фото: %s", exc)
        await update.message.reply_text("📸  Наши работы...\n🖤  Хочешь такой же? Жми «Оформить заказ»!", reply_markup=main_kb())
        return WELCOME
    
    if t == "📞 Контакты":
        await update.message.reply_text("📞  Контакты PATHA...\nОформи заказ прямо здесь — сами свяжемся 🖤", reply_markup=main_kb())
        return WELCOME
        
    if t == "📦 Мой заказ":
        return await show_my_order(update, context)
        
    if t in ("🛍 Оформить заказ", "🏠 Меню", "🛍 Новый заказ") or t in PRICES:
        return await ask_product(update, context)
        
    await update.message.reply_text("Привет! 👋  Я бот PATHA.\nНажми кнопку ниже 👇", reply_markup=main_kb())
    return WELCOME

# --- Остальные функции (ask_product, choose_product, и т.д.) без изменений, 
# --- кроме show_my_order (замени её ниже):

async def show_my_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text("📭  Заказов пока нет.\n\nОформи первый! 👇", reply_markup=main_kb())
        return WELCOME
    
    buttons = [["✏️ Изменить заказ", "🛍 Новый заказ"], ["❌ Отменить заказ"], ["🏠 Меню"]]
    await update.message.reply_text(
        fmt_order(o), 
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return WELCOME

# ... (оставшаяся логика остаётся прежней, просто скопируй всё в файл)

async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text("❌  Нет заказов для изменения.", reply_markup=main_kb())
        return WELCOME
    if o.get("status") in ("delivered", "cancelled"):
        await update.message.reply_text(f"⚠️  Заказ #{o['id']} нельзя изменить.\nСтатус: {ORDER_STATUSES.get(o['status'])}", reply_markup=main_kb())
        return WELCOME
    context.user_data["edit_oid"] = o["id"]
    await update.message.reply_text(f"✏️  Заказ #{o['id']}\n\nЧто меняем?", reply_markup=kb(["📐 Размер", "✍️ Надпись"], ["📱 Телефон"], ["⬅️ К заказу"]))
    return EDIT_MENU

async def edit_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t in ("⬅️ К заказу", "🏠 Меню"): return await show_my_order(update, context)
    if t == "📐 Размер":
        await update.message.reply_text("Выбери новый размер:", reply_markup=kb(["S", "M", "L"], ["XL", "XXL"], ["⬅️ Назад"]))
        return EDIT_SIZE
    if t == "✍️ Надпись":
        await update.message.reply_text("Напиши новую надпись\n(«нет» — чтобы убрать):", reply_markup=kb(["⬅️ Назад"]))
        return EDIT_TEXT
    if t == "📱 Телефон":
        await update.message.reply_text("Введи новый номер:\n+992XXXXXXXXX", reply_markup=kb(["⬅️ Назад"]))
        return EDIT_PHONE
    return EDIT_MENU

async def edit_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "⬅️ Назад": return await edit_entry(update, context)
    if t == "🏠 Меню":  return await start(update, context)
    if t not in SIZES:
        await update.message.reply_text("Выбери из кнопок 👇")
        return EDIT_SIZE
    oid = context.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o["size"] if o else "?"
    db_update(oid, size=t)
    await _notify_change(context, oid, f"Размер: {old} → {t}")
    await update.message.reply_text("✅  Размер изменён!", reply_markup=main_kb())
    return WELCOME

async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == "⬅️ Назад": return await edit_entry(update, context)
    if t == "🏠 Меню":  return await start(update, context)
    new_text = "—" if t.lower() == "нет" else t
    oid = context.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o.get("print_text", "?") if o else "?"
    db_update(oid, print_text=new_text)
    await _notify_change(context, oid, f"Надпись: «{old}» → «{new_text}»")
    await update.message.reply_text("✅  Надпись изменена!", reply_markup=main_kb())
    return WELCOME

async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == "⬅️ Назад": return await edit_entry(update, context)
    if t == "🏠 Меню":  return await start(update, context)
    digits = t.replace("+", "").replace(" ", "").replace("-", "")
    if not digits.isdigit() or not (7 <= len(digits) <= 15):
        await update.message.reply_text("⚠️  Неверный формат.\nПример: +992901234567", reply_markup=kb(["⬅️ Назад"]))
        return EDIT_PHONE
    oid = context.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o.get("phone", "?") if o else "?"
    db_update(oid, phone=t)
    await _notify_change(context, oid, f"Телефон: {old} → {t}")
    await update.message.reply_text("✅  Телефон изменён!", reply_markup=main_kb())
    return WELCOME

async def _notify_change(context: ContextTypes.DEFAULT_TYPE, oid: int, note: str) -> None:
    o = db_get(oid)
    if not o: return
    try:
        for aid in ADMIN_IDS:
            await context.bot.send_message(
                chat_id=aid,
                text=f"✏️  Изменение · заказ #{oid}\n\n📝  {note}\n\n👤  {o.get('name', '—')}  {o.get('username', '')}\n📱  {o.get('phone', '—')}",
            )
    except TelegramError as exc:
        logger.error("Ошибка уведомления: %s", exc)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id not in ADMIN_IDS: return
    args   = context.args or []
    orders = db_all()
    if not orders:
        await update.message.reply_text("📭  Заказов пока нет.")
        return
    counts: dict[str, int] = {}
    revenue = 0
    for o in orders:
        s = o.get("status", "new")
        counts[s] = counts.get(s, 0) + 1
        revenue   += o.get("price", 0) + o.get("extra", 0)
    stat = "\n".join(f"  {ORDER_STATUSES.get(s, s)}: {c}" for s, c in sorted(counts.items()))
    await update.message.reply_text(
        f"📊  PATHA · заказы\n\nВсего: {len(orders)}\nВыручка: {revenue} сом\n\n{stat}\n\n"
        f"Фильтр:\n/admin new\n/admin confirmed\n/admin production\n/admin ready\n\n/order <номер>"
    )
    flt  = args[0] if args else None
    show = [o for o in orders if o.get("status") == flt] if flt else orders
    if not show:
        await update.message.reply_text(f"Нет заказов со статусом «{flt}».")
        return
    for o in reversed(show[-10:]):
        try:
            await update.message.reply_text(fmt_order(o, admin=True))
        except TelegramError as exc:
            logger.error("Ошибка отправки заказа #%s: %s", o["id"], exc)

async def order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id not in ADMIN_IDS: return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /order <номер>")
        return
    oid = int(args[0])
    o   = db_get(oid)
    if not o:
        await update.message.reply_text(f"⚠️  Заказ #{oid} не найден.")
        return
    await update.message.reply_text(fmt_order(o, admin=True))
    if o.get("photo_id"):
        await update.message.reply_photo(photo=o["photo_id"], caption=f"📸  фото · заказ #{o['id']}")

# ══════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WELCOME:             [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_handler)],
            PRODUCT:             [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_product)],
            SIZE:                [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_size)],
            PRINT_TYPE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_print_type)],
            FIGHTER_CHOICE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, fighter_choice)],
            CUSTOM_FIGHTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_fighter_name)],
            QUOTE_CHOICE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, quote_choice)],
            CUSTOM_TEXT:         [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_text)],
            PRINT_PHOTO:         [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_print_photo)],
            PRINT_TEXT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, get_print_text)],
            PHONE:               [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM:             [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
            EDIT_MENU:           [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_menu_handler)],
            EDIT_SIZE:           [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_size)],
            EDIT_TEXT:           [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_PHONE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_phone)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("order", order_cmd))

    logger.info("🖤  PATHA бот v4.0 запущен!")
    
    PORT = int(os.environ.get("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=BOT_TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{BOT_TOKEN}",
    )

if __name__ == "__main__":
    main()
