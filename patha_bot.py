"""
🖤  P A T H A  B O T  v5.1
Именной принт · Душанбе
"""

import json
import logging
import os
from datetime import datetime

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── КОНФИГ ───────────────────────────────────────────
BOT_TOKEN   = "8838090259:AAFMff5XZkaJgNQ3Q-_Akv1aVwwHbPUXhcw"
ADMIN_ID    = 6598665549
ORDERS_FILE = "patha_orders.json"

# Кнопки — ОДИН пробел после эмодзи, без лишних пробелов
BTN_ORDER    = "🛍 Заказать принт"
BTN_EXAMPLES = "📸 Примеры работ"
BTN_CONTACTS = "📞 Контакты"
BTN_MYORDER  = "📦 Мой заказ"
BTN_BACK     = "⬅️ Назад"
BTN_HOME     = "🏠 Меню"
BTN_TSHIRT   = "👕 Футболка"
BTN_HOODIE   = "🧥 Худи"
BTN_NOPHOTO  = "⏭ Без фото"
BTN_CONFIRM  = "✅ Оформить заказ"
BTN_EDIT     = "✏️ Изменить"
BTN_CANCEL   = "❌ Отменить"
BTN_MYEDIT   = "✏️ Изменить заказ"
BTN_NEWORDER = "🛍 Новый заказ"
BTN_OWN_SIZE = "📐 Размер"
BTN_OWN_TEXT = "✍️ Надпись"
BTN_OWN_PHONE= "📱 Телефон"
BTN_BACK2ORDER="⬅️ К заказу"
BTN_OWN_QUOTE= "✍️ Своя надпись"
BTN_THEY_PICK= "🤝 Вы подберёте сами"

PRICES = {
    BTN_TSHIRT: 150,
    BTN_HOODIE: 280,
}
EXTRA_CUSTOM = 20

FIGHTERS = {
    "🦅 Хабиб Нурмагомедов": [
        "I am not in this sport to make friends",
        "Alhamdulillah · The Eagle Has Landed",
        "Делай дело — и Всевышний даст всё",
        "Деньги уходят, честь остаётся",
    ],
    "🍀 Конор МакГрегор": [
        "We're not here to take part — we're here to take over",
        "Talent doesn't exist — only obsession",
        "Champ champ does what he wants",
    ],
    "⚡ Забит Магомедшарипов": [
        "The Stylebender of Eagles",
        "Born in Dagestan · Built for greatness",
        "Zabit · The Artist of MMA",
    ],
    "👑 Ислам Махачев": [
        "Islam Makhachev · The Champion",
        "Dagestan never stops",
        "The New Era of MMA",
    ],
    "🐉 Арман Царукян": [
        "The Armenian Sniper",
        "Built different · Fighting for glory",
        "Tsarukyan · The Rise",
    ],
    "✏️ Свой боец (+20 сом)": [],
}

PRINT_TYPES = [
    "🥊 Спортсмен / Боец",
    "👫 Парный принт",
    "👤 Портрет",
    "✍️ Только надпись",
    "🖼 Своё фото",
]

SIZES = ["S", "M", "L", "XL", "XXL"]

STATUSES = {
    "new":        "🆕 Новый",
    "confirmed":  "✅ Принят",
    "production": "🔨 В работе",
    "ready":      "📦 Готов",
    "delivered":  "🚀 Доставлен",
    "cancelled":  "❌ Отменён",
}

STATUS_FLOW = {
    "new":        ("confirmed",  "✅ Принять"),
    "confirmed":  ("production", "🔨 В работу"),
    "production": ("ready",      "📦 Готово"),
    "ready":      ("delivered",  "🚀 Доставлен"),
}

CLIENT_NOTIFY = {
    "confirmed":  "🖤 PATHA\n━━━━━━━━━━━━━━━━\n✅ Заказ #{id} принят!\n\nСкоро позвоним и согласуем эскиз 🎨\nОжидай звонка!",
    "production": "🖤 PATHA\n━━━━━━━━━━━━━━━━\n🔨 Заказ #{id} в работе!\n\nУже печатаем твой принт 💪",
    "ready":      "🖤 PATHA\n━━━━━━━━━━━━━━━━\n📦 Заказ #{id} готов!\n\nСвяжемся насчёт доставки 🛵",
    "delivered":  "🖤 PATHA\n━━━━━━━━━━━━━━━━\n🚀 Заказ #{id} доставлен!\n\nНоси с гордостью! 🖤\nОтзыв → @patha.tj",
    "cancelled":  "🖤 PATHA\n━━━━━━━━━━━━━━━━\n❌ Заказ #{id} отменён.\n\nВопросы → @patha_tj",
}

# ─── СОСТОЯНИЯ ────────────────────────────────────────
(
    WELCOME, PRODUCT, SIZE, PRINT_TYPE,
    FIGHTER_CHOICE, CUSTOM_FIGHTER, QUOTE_CHOICE, CUSTOM_TEXT,
    PRINT_PHOTO, PRINT_TEXT, PHONE, CONFIRM,
    EDIT_MENU, EDIT_SIZE, EDIT_TEXT, EDIT_PHONE,
) = range(16)

# ─── БД ───────────────────────────────────────────────
def _load():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("БД load: %s", e)
    return {"next_id": 1, "orders": {}}

def _save(data):
    tmp = ORDERS_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ORDERS_FILE)
    except Exception as e:
        logger.error("БД save: %s", e)

def db_add(order):
    data = _load()
    oid = data["next_id"]
    order.update({"id": oid, "status": "new", "created": datetime.now().strftime("%d.%m.%Y %H:%M")})
    data["orders"][str(oid)] = order
    data["next_id"] = oid + 1
    _save(data)
    return oid

def db_get(oid):
    return _load()["orders"].get(str(oid))

def db_update(oid, **kw):
    data = _load()
    if str(oid) in data["orders"]:
        data["orders"][str(oid)].update(kw)
        _save(data)

def db_all():
    return list(_load()["orders"].values())

def db_last(user_id):
    orders = [o for o in db_all() if o.get("user_id") == user_id]
    return orders[-1] if orders else None

# ─── КЛАВИАТУРЫ ───────────────────────────────────────
def main_kb():
    return ReplyKeyboardMarkup([
        [BTN_ORDER],
        [BTN_EXAMPLES, BTN_CONTACTS],
        [BTN_MYORDER],
    ], resize_keyboard=True)

def kb(*rows):
    return ReplyKeyboardMarkup([list(r) for r in rows], resize_keyboard=True)

def nav(*rows):
    """Добавляет ряд Назад/Меню."""
    return ReplyKeyboardMarkup([list(r) for r in rows] + [[BTN_BACK, BTN_HOME]], resize_keyboard=True)

def progress(step, total=6):
    return "●" * step + "○" * (total - step) + f"  {step}/{total}"

# ─── ФОРМАТИРОВАНИЕ ───────────────────────────────────
def fmt_client(o):
    icon  = "👕" if "Футболка" in o.get("product","") else "🧥"
    prod  = o.get("product","—").replace("👕 ","").replace("🧥 ","")
    extra = o.get("extra", 0)
    total = o.get("price", 0) + extra
    photo = "✅" if o.get("photo_id") else "нет"
    ath   = o.get("athlete","")
    stat  = STATUSES.get(o.get("status","new"), "🆕 Новый")
    lines = [
        f"🖤 Заказ #{o['id']}",
        f"━━━━━━━━━━━━━━━━",
        f"{stat}",
        f"",
        f"{icon} {prod}  •  размер {o.get('size','—')}",
        f"🎨 {o.get('print_type','—')}",
    ]
    if ath: lines.append(f"🥊 {ath}")
    lines += [
        f"📸 фото: {photo}",
        f"✍️ {o.get('print_text','—')}",
        f"📱 {o.get('phone','—')}",
        f"",
        f"💵 итого: {total} сом",
        f"🕐 {o.get('created','—')}",
    ]
    return "\n".join(lines)

def fmt_admin(o):
    icon  = "👕" if "Футболка" in o.get("product","") else "🧥"
    prod  = o.get("product","—").replace("👕 ","").replace("🧥 ","")
    extra = o.get("extra", 0)
    total = o.get("price", 0) + extra
    photo = "✅" if o.get("photo_id") else "❌"
    ath   = o.get("athlete","")
    stat  = STATUSES.get(o.get("status","new"), "🆕 Новый")
    lines = [
        f"🖤 PATHA · Заказ #{o['id']}",
        f"━━━━━━━━━━━━━━━━",
        f"{stat}  •  {o.get('created','—')}",
        f"",
        f"👤 {o.get('name','—')}",
        f"📱 {o.get('phone','—')}",
        f"✈️ {o.get('username','—')}",
        f"",
        f"━━━━━━━━━━━━━━━━",
        f"{icon} {prod}  •  размер {o.get('size','—')}",
        f"🎨 {o.get('print_type','—')}",
    ]
    if ath: lines.append(f"🥊 {ath}")
    lines += [
        f"📸 фото: {photo}",
        f"✍️ {o.get('print_text','—')}",
        f"",
        f"💰 {o.get('price',0)} сом",
    ]
    if extra: lines.append(f"➕ +{extra} сом (свой боец)")
    lines += [
        f"💵 итого: {total} сом",
        f"",
        f"━━━━━━━━━━━━━━━━",
        f"tg://user?id={o.get('user_id',0)}",
    ]
    return "\n".join(lines)

def admin_inline(oid, status, user_id):
    rows = []
    if status in STATUS_FLOW:
        nxt, label = STATUS_FLOW[status]
        rows.append([
            InlineKeyboardButton(label, callback_data=f"s:{oid}:{nxt}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"s:{oid}:cancelled"),
        ])
    rows.append([InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={user_id}")])
    return InlineKeyboardMarkup(rows)

# ─── /start ───────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.clear()
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"🖤 P A T H A\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"Привет, {name}! 👋\n\n"
        f"Именной принт на одежде\n"
        f"твоей мечты 🔥\n\n"
        f"👕 Футболка  —  150 сом\n"
        f"🧥 Худи       —  280 сом\n\n"
        f"Выбери действие 👇",
        reply_markup=main_kb(),
    )
    return WELCOME

# ─── WELCOME ──────────────────────────────────────────
async def welcome(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text

    if t == BTN_EXAMPLES:
        await update.message.reply_text(
            "📸 Примеры наших работ\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "🦅 Хабиб · The Eagle\n"
            "🍀 МакГрегор · Notorious\n"
            "⚡ Забит · Artist of MMA\n"
            "👑 Ислам Махачев · Champion\n"
            "👫 Парные худи с фото\n"
            "👤 Портреты на заказ\n\n"
            "📲 Instagram → @patha.tj",
            reply_markup=main_kb(),
        )
        return WELCOME

    if t == BTN_CONTACTS:
        await update.message.reply_text(
            "📞 Контакты PATHA\n"
            "━━━━━━━━━━━━━━━━\n\n"
            "📸 Instagram → @patha.tj\n"
            "✈️ Telegram  → @patha_tj\n\n"
            "Оформи заказ — сами\n"
            "свяжемся с тобой 🖤",
            reply_markup=main_kb(),
        )
        return WELCOME

    if t == BTN_MYORDER:
        return await show_my_order(update, ctx)

    if t == BTN_MYEDIT:
        return await edit_entry(update, ctx)

    if t == BTN_NEWORDER or t == BTN_ORDER or t == BTN_HOME:
        return await ask_product(update, ctx)

    # Первое сообщение или неизвестный текст
    return await cmd_start(update, ctx)

# ─── ШАГ 1 — ТОВАР ────────────────────────────────────
async def ask_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"🛍 Новый заказ\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(1)}\n\n"
        f"Что заказываем?\n\n"
        f"👕 Футболка  —  150 сом\n"
        f"🧥 Худи       —  280 сом",
        reply_markup=kb([BTN_TSHIRT, BTN_HOODIE], [BTN_HOME]),
    )
    return PRODUCT

async def choose_product(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_HOME: return await cmd_start(update, ctx)
    if t not in PRICES:
        await update.message.reply_text("Выбери товар из кнопок 👇")
        return PRODUCT
    ctx.user_data.update(product=t, price=PRICES[t], extra=0)
    return await ask_size(update, ctx)

# ─── ШАГ 2 — РАЗМЕР ───────────────────────────────────
async def ask_size(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    prod = ctx.user_data.get("product","")
    await update.message.reply_text(
        f"📐 Размер\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(2)}\n\n"
        f"Товар: {prod}\n\n"
        f"Выбери размер:",
        reply_markup=nav(["S", "M", "L"], ["XL", "XXL"]),
    )
    return SIZE

async def choose_size(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    if t == BTN_BACK:  return await ask_product(update, ctx)
    if t not in SIZES:
        await update.message.reply_text("Выбери размер из кнопок 👇")
        return SIZE
    ctx.user_data["size"] = t
    return await ask_print_type(update, ctx)

# ─── ШАГ 3 — ТИП ПРИНТА ───────────────────────────────
async def ask_print_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"🎨 Тип принта\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(3)}\n\n"
        f"Что будем печатать?",
        reply_markup=nav(*[[pt] for pt in PRINT_TYPES]),
    )
    return PRINT_TYPE

async def choose_print_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    if t == BTN_BACK:  return await ask_size(update, ctx)
    if t not in PRINT_TYPES:
        await update.message.reply_text("Выбери из кнопок 👇")
        return PRINT_TYPE
    ctx.user_data.update(print_type=t, athlete="")
    if t == "🥊 Спортсмен / Боец":
        return await ask_fighter(update, ctx)
    if t == "✍️ Только надпись":
        ctx.user_data["photo_id"] = None
        return await ask_print_text(update, ctx, step=4)
    return await ask_photo(update, ctx)

# ─── ШАГ 4а — БОЕЦ ────────────────────────────────────
async def ask_fighter(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"🥊 Выбери бойца\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(4)}\n\n"
        f"Свой вариант = +20 сом 💸",
        reply_markup=nav(*[[f] for f in FIGHTERS.keys()]),
    )
    return FIGHTER_CHOICE

async def fighter_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    if t == BTN_BACK:  return await ask_print_type(update, ctx)
    if t not in FIGHTERS:
        await update.message.reply_text("Выбери бойца из кнопок 👇")
        return FIGHTER_CHOICE
    if t == "✏️ Свой боец (+20 сом)":
        ctx.user_data["extra"] = EXTRA_CUSTOM
        await update.message.reply_text(
            f"✏️ Свой боец\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"Напиши имя бойца:\n\n"
            f"Доп. плата: +20 сом\n"
            f"(поиск фото + дизайн)",
            reply_markup=kb([BTN_BACK, BTN_HOME]),
        )
        return CUSTOM_FIGHTER
    ctx.user_data.update(athlete=t, extra=0)
    return await ask_quote(update, ctx)

async def custom_fighter(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_BACK:  return await ask_fighter(update, ctx)
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    name = t.strip()
    if not name:
        await update.message.reply_text("Напиши имя бойца 👇")
        return CUSTOM_FIGHTER
    ctx.user_data["athlete"] = name
    return await ask_quote(update, ctx)

# ─── ШАГ 5 — ЦИТАТА ───────────────────────────────────
async def ask_quote(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    athlete = ctx.user_data.get("athlete","")
    quotes  = FIGHTERS.get(athlete, [])
    body = (
        f"💬 Надпись для принта\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(5)}\n\n"
        f"🥊 {athlete}\n\n"
        f"Выбери цитату или напиши свою:"
    )
    rows = [[q] for q in quotes]
    rows.append([BTN_OWN_QUOTE])
    rows.append([BTN_THEY_PICK])
    await update.message.reply_text(body, reply_markup=nav(*rows))
    return QUOTE_CHOICE

async def quote_choice(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    if t == BTN_BACK:  return await ask_fighter(update, ctx)
    if t == BTN_OWN_QUOTE:
        await update.message.reply_text(
            f"✍️ Своя надпись\n"
            f"━━━━━━━━━━━━━━━━\n\n"
            f"Напиши имя, цитату\nили любой текст:",
            reply_markup=kb([BTN_BACK, BTN_HOME]),
        )
        return CUSTOM_TEXT
    if t == BTN_THEY_PICK:
        ctx.user_data.update(print_text="🤝 Подберёте сами", photo_id=None)
        return await ask_phone(update, ctx)
    athlete = ctx.user_data.get("athlete","")
    valid   = FIGHTERS.get(athlete, [])
    if valid and t not in valid:
        await update.message.reply_text("Выбери из кнопок 👇")
        return QUOTE_CHOICE
    ctx.user_data.update(print_text=t, photo_id=None)
    return await ask_phone(update, ctx)

async def custom_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_BACK:  return await ask_quote(update, ctx)
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    text = t.strip()
    if not text:
        await update.message.reply_text("Напиши текст 👇")
        return CUSTOM_TEXT
    ctx.user_data.update(print_text=text, photo_id=None)
    return await ask_phone(update, ctx)

# ─── ШАГ 4б — ФОТО ────────────────────────────────────
async def ask_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"📷 Фото для принта\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(4)}\n\n"
        f"Отправь фото 📸\n\n"
        f"Или нажми «Без фото»",
        reply_markup=nav([BTN_NOPHOTO]),
    )
    return PRINT_PHOTO

async def get_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text or ""
    if text == BTN_HOME:    return await cmd_start(update, ctx)
    if text == BTN_BACK:    return await ask_print_type(update, ctx)
    if update.message.photo:
        ctx.user_data["photo_id"] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Фото получено!")
        return await ask_print_text(update, ctx, step=5)
    if text == BTN_NOPHOTO:
        ctx.user_data["photo_id"] = None
        return await ask_print_text(update, ctx, step=5)
    await update.message.reply_text(
        "📸 Отправь фото\nили нажми «Без фото» 👇",
        reply_markup=nav([BTN_NOPHOTO]),
    )
    return PRINT_PHOTO

async def ask_print_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE, step=5) -> int:
    await update.message.reply_text(
        f"✍️ Надпись\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(step)}\n\n"
        f"Напиши имя, цитату или дату.\n\n"
        f"Нет надписи? Напиши: нет",
        reply_markup=kb([BTN_BACK, BTN_HOME]),
    )
    return PRINT_TEXT

async def get_print_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == BTN_BACK:  return await ask_photo(update, ctx)
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    ctx.user_data["print_text"] = "—" if t.lower() == "нет" else t
    return await ask_phone(update, ctx)

# ─── ШАГ 6 — ТЕЛЕФОН ──────────────────────────────────
async def ask_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"📱 Твой номер\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{progress(6)}\n\n"
        f"Позвоним — согласуем\n"
        f"эскиз и детали 🖤\n\n"
        f"Формат: +992XXXXXXXXX",
        reply_markup=kb([BTN_BACK, BTN_HOME]),
    )
    return PHONE

async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == BTN_HOME:  return await cmd_start(update, ctx)
    if t == BTN_BACK:
        pt = ctx.user_data.get("print_type","")
        if pt == "🥊 Спортсмен / Боец":  return await ask_quote(update, ctx)
        elif pt == "✍️ Только надпись":   return await ask_print_text(update, ctx, step=4)
        else:                              return await ask_print_text(update, ctx, step=5)
    digits = t.replace("+","").replace(" ","").replace("-","")
    if not digits.isdigit() or not (7 <= len(digits) <= 15):
        await update.message.reply_text(
            "⚠️ Неверный номер\n\nПример: +992901234567",
            reply_markup=kb([BTN_BACK, BTN_HOME]),
        )
        return PHONE
    ctx.user_data["phone"] = t
    return await show_confirm(update, ctx)

# ─── ПОДТВЕРЖДЕНИЕ ────────────────────────────────────
async def show_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ud    = ctx.user_data
    extra = ud.get("extra", 0)
    total = ud.get("price", 0) + extra
    photo = "✅" if ud.get("photo_id") else "нет"
    ath   = ud.get("athlete","")
    icon  = "👕" if "Футболка" in ud.get("product","") else "🧥"
    prod  = ud.get("product","—").replace("👕 ","").replace("🧥 ","")

    lines = [
        "📋 Проверь заказ",
        "━━━━━━━━━━━━━━━━",
        "",
        f"{icon} {prod}  •  размер {ud.get('size','—')}",
        f"🎨 {ud.get('print_type','—')}",
    ]
    if ath: lines.append(f"🥊 {ath}")
    lines += [
        f"📸 фото: {photo}",
        f"✍️ {ud.get('print_text','—')}",
        f"📱 {ud.get('phone','—')}",
        "",
        f"💰 {ud.get('price',0)} сом",
    ]
    if extra: lines.append(f"➕ +{extra} сом (свой боец)")
    lines += [f"💵 итого: {total} сом", "", "Всё верно? 👇"]

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=kb([BTN_CONFIRM], [BTN_EDIT], [BTN_CANCEL]),
    )
    return CONFIRM

async def confirm_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_EDIT:   return await ask_product(update, ctx)
    if t == BTN_CANCEL:
        ctx.user_data.clear()
        await update.message.reply_text("❌ Заказ отменён.", reply_markup=main_kb())
        return WELCOME
    if t != BTN_CONFIRM:
        await update.message.reply_text("Выбери действие 👇")
        return CONFIRM

    user = update.effective_user
    ud   = ctx.user_data
    new_order = {
        "name":       user.first_name or "—",
        "username":   f"@{user.username}" if user.username else "—",
        "user_id":    user.id,
        "product":    ud.get("product","—"),
        "size":       ud.get("size","—"),
        "print_type": ud.get("print_type","—"),
        "athlete":    ud.get("athlete",""),
        "print_text": ud.get("print_text","—"),
        "photo_id":   ud.get("photo_id"),
        "phone":      ud.get("phone","—"),
        "price":      ud.get("price",0),
        "extra":      ud.get("extra",0),
    }
    oid   = db_add(new_order)
    order = db_get(oid)

    await update.message.reply_text(
        f"🎉 Готово!\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Заказ #{oid} оформлен 🖤\n\n"
        f"📱 Позвоним на {ud.get('phone','—')}\n\n"
        f"🎨 Сделаем эскиз\n"
        f"✅ Согласуем с тобой\n"
        f"🖨 Напечатаем\n"
        f"🛵 Доставим\n\n"
        f"Спасибо что выбрал PATHA! 🖤",
        reply_markup=main_kb(),
    )
    try:
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=fmt_admin(order),
            reply_markup=admin_inline(oid, "new", user.id),
        )
        if order.get("photo_id"):
            await ctx.bot.send_photo(chat_id=ADMIN_ID, photo=order["photo_id"], caption=f"📸 Фото · заказ #{oid}")
    except TelegramError as e:
        logger.error("Отправка админу: %s", e)

    ctx.user_data.clear()
    return WELCOME

# ─── МОЙ ЗАКАЗ ────────────────────────────────────────
async def show_my_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    o = db_last(update.effective_user.id)
    if not o:
        await update.message.reply_text("📭 Заказов пока нет.\n\nОформи первый! 🖤", reply_markup=main_kb())
        return WELCOME
    await update.message.reply_text(
        fmt_client(o),
        reply_markup=kb([BTN_MYEDIT], [BTN_NEWORDER], [BTN_HOME]),
    )
    return WELCOME

# ─── РЕДАКТИРОВАНИЕ ───────────────────────────────────
async def edit_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    o = db_last(update.effective_user.id)
    if not o:
        await update.message.reply_text("❌ Нет заказов для изменения.", reply_markup=main_kb())
        return WELCOME
    if o.get("status") in ("delivered", "cancelled"):
        await update.message.reply_text(
            f"⚠️ Заказ #{o['id']} нельзя изменить\nСтатус: {STATUSES.get(o['status'])}",
            reply_markup=main_kb(),
        )
        return WELCOME
    ctx.user_data["edit_oid"] = o["id"]
    await update.message.reply_text(
        f"✏️ Редактирование\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"Заказ #{o['id']}\n\nЧто меняем?",
        reply_markup=kb([BTN_OWN_SIZE, BTN_OWN_TEXT], [BTN_OWN_PHONE], [BTN_BACK2ORDER]),
    )
    return EDIT_MENU

async def edit_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t in (BTN_BACK2ORDER, BTN_HOME): return await show_my_order(update, ctx)
    if t == BTN_OWN_SIZE:
        await update.message.reply_text("📐 Новый размер:", reply_markup=nav(["S","M","L"],["XL","XXL"]))
        return EDIT_SIZE
    if t == BTN_OWN_TEXT:
        await update.message.reply_text("✍️ Новая надпись\n(«нет» — чтобы убрать):", reply_markup=kb([BTN_BACK, BTN_HOME]))
        return EDIT_TEXT
    if t == BTN_OWN_PHONE:
        await update.message.reply_text("📱 Новый номер:\n+992XXXXXXXXX", reply_markup=kb([BTN_BACK, BTN_HOME]))
        return EDIT_PHONE
    return EDIT_MENU

async def edit_size(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == BTN_BACK: return await edit_entry(update, ctx)
    if t == BTN_HOME: return await cmd_start(update, ctx)
    if t not in SIZES:
        await update.message.reply_text("Выбери из кнопок 👇")
        return EDIT_SIZE
    oid = ctx.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o["size"] if o else "?"
    db_update(oid, size=t)
    await _notify_edit(ctx, oid, f"Размер: {old} → {t}")
    await update.message.reply_text("✅ Размер изменён!", reply_markup=main_kb())
    return WELCOME

async def edit_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == BTN_BACK: return await edit_entry(update, ctx)
    if t == BTN_HOME: return await cmd_start(update, ctx)
    new_text = "—" if t.lower() == "нет" else t
    oid = ctx.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o.get("print_text","?") if o else "?"
    db_update(oid, print_text=new_text)
    await _notify_edit(ctx, oid, f"Надпись: «{old}» → «{new_text}»")
    await update.message.reply_text("✅ Надпись изменена!", reply_markup=main_kb())
    return WELCOME

async def edit_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == BTN_BACK: return await edit_entry(update, ctx)
    if t == BTN_HOME: return await cmd_start(update, ctx)
    digits = t.replace("+","").replace(" ","").replace("-","")
    if not digits.isdigit() or not (7 <= len(digits) <= 15):
        await update.message.reply_text("⚠️ Неверный формат.\nПример: +992901234567", reply_markup=kb([BTN_BACK, BTN_HOME]))
        return EDIT_PHONE
    oid = ctx.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o.get("phone","?") if o else "?"
    db_update(oid, phone=t)
    await _notify_edit(ctx, oid, f"Телефон: {old} → {t}")
    await update.message.reply_text("✅ Телефон изменён!", reply_markup=main_kb())
    return WELCOME

async def _notify_edit(ctx, oid, note):
    o = db_get(oid)
    if not o: return
    try:
        await ctx.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"✏️ Изменение · заказ #{oid}\n"
                f"━━━━━━━━━━━━━━━━\n\n"
                f"📝 {note}\n\n"
                f"👤 {o.get('name','—')}\n"
                f"📱 {o.get('phone','—')}\n"
                f"✈️ {o.get('username','—')}"
            ),
            reply_markup=admin_inline(oid, o.get("status","new"), o.get("user_id",0)),
        )
    except TelegramError as e:
        logger.error("notify_edit: %s", e)

# ─── CALLBACK СТАТУС ──────────────────────────────────
async def status_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔ Нет доступа", show_alert=True)
        return
    await q.answer()
    parts = q.data.split(":")
    if len(parts) != 3 or not parts[1].isdigit(): return
    _, oid_str, new_status = parts
    oid = int(oid_str)
    if new_status not in STATUSES: return
    db_update(oid, status=new_status)
    o = db_get(oid)
    if not o:
        await q.edit_message_text("⚠️ Заказ не найден.")
        return
    try:
        await q.edit_message_text(text=fmt_admin(o), reply_markup=admin_inline(oid, new_status, o.get("user_id",0)))
    except TelegramError as e:
        logger.error("edit_message: %s", e)
    template = CLIENT_NOTIFY.get(new_status)
    uid = o.get("user_id")
    if template and uid:
        try:
            await ctx.bot.send_message(chat_id=uid, text=template.replace("{id}", str(oid)))
        except TelegramError as e:
            logger.error("notify_client: %s", e)

# ─── КОМАНДЫ АДМИНА ───────────────────────────────────
async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID: return
    args   = ctx.args or []
    orders = db_all()
    if not orders:
        await update.message.reply_text("📭 Заказов нет.")
        return
    counts, revenue = {}, 0
    for o in orders:
        s = o.get("status","new")
        counts[s] = counts.get(s,0) + 1
        revenue += o.get("price",0) + o.get("extra",0)
    stat = "\n".join(f"{STATUSES.get(s,s)}: {c}" for s,c in sorted(counts.items()))
    await update.message.reply_text(
        f"📊 PATHA · Статистика\n"
        f"━━━━━━━━━━━━━━━━\n\n"
        f"📦 Заказов: {len(orders)}\n"
        f"💵 Выручка: {revenue} сом\n\n"
        f"{stat}\n\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"/admin new | confirmed | production | ready\n"
        f"/order <номер>"
    )
    flt  = args[0] if args else None
    show = [o for o in orders if o.get("status") == flt] if flt else orders
    if flt and not show:
        await update.message.reply_text(f"Нет заказов: «{flt}»")
        return
    for o in reversed(show[-10:]):
        try:
            await update.message.reply_text(
                fmt_admin(o),
                reply_markup=admin_inline(o["id"], o.get("status","new"), o.get("user_id",0)),
            )
        except TelegramError as e:
            logger.error("admin send #%s: %s", o["id"], e)

async def cmd_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID: return
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /order <номер>")
        return
    oid = int(args[0])
    o   = db_get(oid)
    if not o:
        await update.message.reply_text(f"⚠️ Заказ #{oid} не найден.")
        return
    await update.message.reply_text(fmt_admin(o), reply_markup=admin_inline(o["id"], o.get("status","new"), o.get("user_id",0)))
    if o.get("photo_id"):
        await update.message.reply_photo(photo=o["photo_id"], caption=f"📸 Фото · заказ #{o['id']}")

# ─── ЗАПУСК ───────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    CB = [CallbackQueryHandler(status_cb, pattern=r"^s:\d+:\w+$")]

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, welcome),
        ],
        states={
            WELCOME:        CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome)],
            PRODUCT:        CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_product)],
            SIZE:           CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_size)],
            PRINT_TYPE:     CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_print_type)],
            FIGHTER_CHOICE: CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, fighter_choice)],
            CUSTOM_FIGHTER: CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_fighter)],
            QUOTE_CHOICE:   CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, quote_choice)],
            CUSTOM_TEXT:    CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_text)],
            PRINT_PHOTO:    CB + [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_photo)],
            PRINT_TEXT:     CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, get_print_text)],
            PHONE:          CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM:        CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
            EDIT_MENU:      CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_menu)],
            EDIT_SIZE:      CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_size)],
            EDIT_TEXT:      CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_PHONE:     CB + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_phone)],
        },
        fallbacks=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(status_cb, pattern=r"^s:\d+:\w+$"),
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(status_cb, pattern=r"^s:\d+:\w+$"))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("order", cmd_order))

    logger.info("🖤 PATHA Bot v5.1 — запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
