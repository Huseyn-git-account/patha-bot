import json
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, ConversationHandler
)

# ═══════════════════════════════════════
#  КОНФИГ
# ═══════════════════════════════════════
BOT_TOKEN   = "8838090259:AAFMff5XZkaJgNQ3Q-_Akv1aVwwHbPUXhcw"
ADMIN_ID    = 6598665549
ORDERS_FILE = "orders.json"

PRICES = {
    "👕 Футболка": 150,
    "🧥 Худи":     280,
}
EXTRA_CUSTOM = 20

FIGHTERS = {
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

PRINT_TYPES = [
    "🥊 Спортсмен / Боец",
    "👫 Парный принт",
    "👤 Портрет",
    "✍️ Только надпись",
    "🖼 Своё фото",
]

SIZES = ["S", "M", "L", "XL", "XXL"]

ORDER_STATUSES = {
    "new":        "🆕 Новый",
    "confirmed":  "✅ Принят",
    "production": "🔨 В работе",
    "ready":      "📦 Готов",
    "delivered":  "🚀 Доставлен",
    "cancelled":  "❌ Отменён",
}

STATUS_NOTIFY = {
    "confirmed":  "✅ Заказ #{id} принят!\n\nСкоро свяжемся для согласования эскиза 🖤",
    "production": "🔨 Заказ #{id} в работе!\n\nПечатаем твой принт, скоро будет готово.",
    "ready":      "📦 Заказ #{id} готов!\n\nСвяжемся насчёт доставки.",
    "delivered":  "🚀 Заказ #{id} доставлен!\n\nСпасибо что выбрал PATHA 🖤",
    "cancelled":  "❌ Заказ #{id} отменён.\n\nЕсли есть вопросы — напиши нам.",
}

# ═══════════════════════════════════════
#  СОСТОЯНИЯ
# ═══════════════════════════════════════
(
    WELCOME, PRODUCT, SIZE, PRINT_TYPE,
    FIGHTER_CHOICE, CUSTOM_FIGHTER_NAME,
    QUOTE_CHOICE, CUSTOM_TEXT,
    PRINT_PHOTO, PRINT_TEXT,
    PHONE, CONFIRM,
    EDIT_MENU, EDIT_SIZE, EDIT_TEXT, EDIT_PHONE,
) = range(16)

# ═══════════════════════════════════════
#  ХРАНЕНИЕ ЗАКАЗОВ (JSON)
# ═══════════════════════════════════════
def _load() -> dict:
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"next_id": 1, "orders": {}}

def _save(data: dict):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def db_add(order: dict) -> int:
    data = _load()
    oid  = data["next_id"]
    order.update({"id": oid, "status": "new",
                  "created": datetime.now().strftime("%d.%m.%Y %H:%M")})
    data["orders"][str(oid)] = order
    data["next_id"] = oid + 1
    _save(data)
    return oid

def db_get(oid: int) -> dict | None:
    return _load()["orders"].get(str(oid))

def db_update(oid: int, **kwargs):
    data = _load()
    if str(oid) in data["orders"]:
        data["orders"][str(oid)].update(kwargs)
        _save(data)

def db_all() -> list:
    return list(_load()["orders"].values())

def db_last_for_user(user_id: int) -> dict | None:
    orders = [o for o in db_all() if o.get("user_id") == user_id]
    return orders[-1] if orders else None

# ═══════════════════════════════════════
#  UI HELPERS
# ═══════════════════════════════════════
def kb(*rows, nav=False):
    btn = [list(r) for r in rows]
    if nav:
        btn.append(["⬅️ Назад", "🏠 Меню"])
    return ReplyKeyboardMarkup(btn, resize_keyboard=True)

def main_kb():
    return kb(
        ["🛍 Оформить заказ"],
        ["📸 Примеры работ", "📞 Контакты"],
        ["📦 Мой заказ"],
    )

def msg_step(n: int, title: str, body: str = "") -> str:
    dots = "●" * n + "○" * (6 - n)
    return (
        f"[ {dots} ]  Шаг {n} из 6\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{title}\n"
        + (f"\n{body}" if body else "")
    )

def fmt_order(o: dict, admin=False) -> str:
    athlete = o.get("athlete", "")
    extra   = o.get("extra", 0)
    photo   = "✅ Есть" if o.get("photo_id") else "❌ Нет"
    status  = ORDER_STATUSES.get(o.get("status", "new"), "🆕")
    total   = o["price"] + extra
    icon    = "👕" if "Футболка" in o["product"] else "🧥"

    lines = [f"📋  ЗАКАЗ #{o['id']}  ·  {status}",
             "━━━━━━━━━━━━━━━━━━━━"]
    if admin:
        lines += [
            f"👤  {o.get('name','—')}  {o.get('username','')}",
            f"📱  {o.get('phone','—')}",
            f"🕐  {o.get('created','—')}",
            "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        ]
    lines += [
        f"{icon}  {o['product']}  ·  {o['size']}",
        f"🎨  {o['print_type']}",
    ]
    if athlete and athlete not in ("—", ""):
        lines.append(f"🥊  {athlete}")
    lines += [
        f"📸  Фото: {photo}",
        f"✍️   {o.get('print_text','—')}",
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        f"💰  Базовая:  {o['price']} сом",
    ]
    if extra:
        lines.append(f"➕  Доп.:     +{extra} сом")
    lines += [f"💵  ИТОГО:    {total} сом",
              "━━━━━━━━━━━━━━━━━━━━"]
    if admin:
        lines.append(f"💬  tg://user?id={o.get('user_id','')}")
    return "\n".join(lines)

def admin_kb(oid: int, status: str, user_id: int) -> InlineKeyboardMarkup:
    flow   = {"new":"confirmed","confirmed":"production","production":"ready","ready":"delivered"}
    labels = {"confirmed":"✅ Принять","production":"🔨 В работу","ready":"📦 Готов","delivered":"🚀 Доставлен"}
    rows   = []
    if status in flow:
        nxt = flow[status]
        rows.append([
            InlineKeyboardButton(labels[nxt], callback_data=f"s:{oid}:{nxt}"),
            InlineKeyboardButton("❌ Отменить", callback_data=f"s:{oid}:cancelled"),
        ])
    rows.append([InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={user_id}")])
    return InlineKeyboardMarkup(rows)

# ═══════════════════════════════════════
#  /start и главное меню
# ═══════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🖤  P A T H A\n"
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        "Именной принт · Душанбе 🇹🇯\n\n"
        "👕  Футболка  —  от 150 сом\n"
        "🧥  Худи       —  от 280 сом\n"
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
        "Твоя история на твоей одежде ✊",
        reply_markup=main_kb()
    )
    return WELCOME

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text

    if t == "📸 Примеры работ":
        await update.message.reply_text(
            "📸  НАШИ РАБОТЫ\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "🥊  Хабиб · THE EAGLE\n"
            "🥊  МакГрегор · THE NOTORIOUS\n"
            "🥊  Забит · The Artist of MMA\n"
            "🥊  Ислам Махачев · Champion\n"
            "👫  Парные худи с фото\n"
            "👤  Портреты на заказ\n\n"
            "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            "📲  Instagram: @patha.tj",
            reply_markup=main_kb()
        )
        return WELCOME

    if t == "📞 Контакты":
        await update.message.reply_text(
            "📞  КОНТАКТЫ\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "📸  Instagram · @patha.tj\n"
            "✈️   Telegram  · @patha_tj\n\n"
            "Или оформи заказ — мы сами\n"
            "свяжемся с тобой 🖤",
            reply_markup=main_kb()
        )
        return WELCOME

    if t == "📦 Мой заказ":
        return await show_my_order(update, context)

    if t in ("🛍 Оформить заказ", "🏠 Меню"):
        return await ask_product(update, context)

    await update.message.reply_text(
        "👋  Привет! Я бот PATHA.\n\nНажми кнопку ниже 👇",
        reply_markup=main_kb()
    )
    return WELCOME

# ═══════════════════════════════════════
#  ШАГ 1 — ТОВАР
# ═══════════════════════════════════════
async def ask_product(update, context):
    await update.message.reply_text(
        msg_step(1, "Что заказываешь?",
                 "👕  Футболка  —  от 150 сом\n"
                 "🧥  Худи       —  от 280 сом"),
        reply_markup=kb(["👕 Футболка", "🧥 Худи"], ["🏠 Меню"])
    )
    return PRODUCT

async def choose_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "🏠 Меню":
        return await start(update, context)
    if t not in PRICES:
        await update.message.reply_text("Выбери из кнопок 👇")
        return PRODUCT
    context.user_data.update(product=t, price=PRICES[t], extra=0)
    return await ask_size(update, context)

# ═══════════════════════════════════════
#  ШАГ 2 — РАЗМЕР
# ═══════════════════════════════════════
async def ask_size(update, context):
    p = context.user_data["product"]
    await update.message.reply_text(
        msg_step(2, "Выбери размер", f"Товар: {p}"),
        reply_markup=kb(["S", "M", "L"], ["XL", "XXL"], nav=True)
    )
    return SIZE

async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_product(update, context)
    if t not in SIZES:
        await update.message.reply_text("Выбери размер из кнопок 👇")
        return SIZE
    context.user_data["size"] = t
    return await ask_print_type(update, context)

# ═══════════════════════════════════════
#  ШАГ 3 — ТИП ПРИНТА
# ═══════════════════════════════════════
async def ask_print_type(update, context):
    await update.message.reply_text(
        msg_step(3, "Тип принта",
                 "🥊  Спортсмен / Боец\n"
                 "👫  Парный принт\n"
                 "👤  Портрет\n"
                 "✍️   Только надпись\n"
                 "🖼  Своё фото"),
        reply_markup=kb(*[[t] for t in PRINT_TYPES], nav=True)
    )
    return PRINT_TYPE

async def choose_print_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_size(update, context)
    if t not in PRINT_TYPES:
        await update.message.reply_text("Выбери из кнопок 👇")
        return PRINT_TYPE
    context.user_data.update(print_type=t, athlete_name="")
    if t == "🥊 Спортсмен / Боец":
        return await ask_fighter(update, context)
    if t == "✍️ Только надпись":
        context.user_data["photo_id"] = None
        return await ask_print_text(update, context, step=4)
    return await ask_photo(update, context)

# ═══════════════════════════════════════
#  ШАГ 4а — БОЕЦ
# ═══════════════════════════════════════
async def ask_fighter(update, context):
    await update.message.reply_text(
        msg_step(4, "Выбери бойца",
                 "✏️ Свой боец = доп. +20 сом"),
        reply_markup=kb(*[[f] for f in FIGHTERS.keys()], nav=True)
    )
    return FIGHTER_CHOICE

async def fighter_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_print_type(update, context)
    if t not in FIGHTERS:
        await update.message.reply_text("Выбери бойца из кнопок 👇")
        return FIGHTER_CHOICE
    if t == "✏️ Свой боец  (+20 сом)":
        context.user_data["extra"] = EXTRA_CUSTOM
        await update.message.reply_text(
            "✏️  Напиши имя бойца:\n\n"
            "⚠️  Доп. плата +20 сом\n"
            "(поиск фото + оформление дизайна)",
            reply_markup=kb(["⬅️ Назад"])
        )
        return CUSTOM_FIGHTER_NAME
    context.user_data.update(athlete_name=t, extra=0)
    return await ask_quote(update, context)

async def custom_fighter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "⬅️ Назад":
        return await ask_fighter(update, context)
    context.user_data["athlete_name"] = t.strip()
    return await ask_quote(update, context)

# ═══════════════════════════════════════
#  ШАГ 5а — ЦИТАТА
# ═══════════════════════════════════════
async def ask_quote(update, context):
    athlete = context.user_data.get("athlete_name", "")
    quotes  = FIGHTERS.get(athlete, [])
    q_list  = "\n".join(f"· {q}" for q in quotes) if quotes else "(нет стандартных)"
    await update.message.reply_text(
        msg_step(5, f"Надпись для принта", f"Боец: {athlete}\n\nГотовые варианты:\n{q_list}"),
        reply_markup=kb(
            *[[q] for q in quotes],
            ["✍️ Своя надпись"],
            ["🤝 Вы сами подберёте"],
            nav=True
        )
    )
    return QUOTE_CHOICE

async def quote_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_fighter(update, context)
    if t == "✍️ Своя надпись":
        await update.message.reply_text(
            "✍️  Напиши свою надпись:\n\nЛюбой текст · имя · цитата · дата",
            reply_markup=kb(["⬅️ Назад"])
        )
        return CUSTOM_TEXT
    if t == "🤝 Вы сами подберёте":
        context.user_data.update(print_text="🤝 Подберёте сами", photo_id=None)
        return await ask_phone(update, context)
    # готовая цитата
    context.user_data.update(print_text=t, photo_id=None)
    return await ask_phone(update, context)

async def custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "⬅️ Назад":
        return await ask_quote(update, context)
    context.user_data.update(print_text=t.strip(), photo_id=None)
    return await ask_phone(update, context)

# ═══════════════════════════════════════
#  ШАГ 4б — ФОТО
# ═══════════════════════════════════════
async def ask_photo(update, context):
    await update.message.reply_text(
        msg_step(4, "Отправь фото для принта",
                 "· Фото человека\n"
                 "· Совместное фото\n"
                 "· Любая картинка\n\n"
                 "Или нажми «Без фото»"),
        reply_markup=kb(["⏭ Без фото"], nav=True)
    )
    return PRINT_PHOTO

async def get_print_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text if update.message.text else ""
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_print_type(update, context)
    if update.message.photo:
        context.user_data["photo_id"] = update.message.photo[-1].file_id
        return await ask_print_text(update, context, step=5)
    if t == "⏭ Без фото":
        context.user_data["photo_id"] = None
        return await ask_print_text(update, context, step=5)
    await update.message.reply_text(
        "📸  Отправь фото или нажми «Без фото»",
        reply_markup=kb(["⏭ Без фото"], nav=True)
    )
    return PRINT_PHOTO

async def ask_print_text(update, context, step=5):
    await update.message.reply_text(
        msg_step(step, "Надпись для принта",
                 "Примеры:\n"
                 "· Имя человека\n"
                 "· Любимая цитата\n"
                 "· Дата — 29.10.2022\n\n"
                 "Нет надписи? Напиши: нет"),
        reply_markup=kb(["⬅️ Назад"])
    )
    return PRINT_TEXT

async def get_print_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    if t == "⬅️ Назад":
        return await ask_photo(update, context)
    context.user_data["print_text"] = "—" if t.lower() == "нет" else t
    return await ask_phone(update, context)

# ═══════════════════════════════════════
#  ШАГ 6 — ТЕЛЕФОН
# ═══════════════════════════════════════
async def ask_phone(update, context):
    await update.message.reply_text(
        msg_step(6, "Твой номер телефона",
                 "Мы позвоним, сделаем эскиз\n"
                 "и согласуем с тобой 🖤\n\n"
                 "Формат: +992XXXXXXXXX"),
        reply_markup=kb(["⬅️ Назад"])
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()

    if t == "⬅️ Назад":
        pt = context.user_data.get("print_type", "")
        if pt == "🥊 Спортсмен / Боец":
            return await ask_quote(update, context)
        elif pt == "✍️ Только надпись":
            return await ask_print_text(update, context, step=4)
        else:
            return await ask_print_text(update, context, step=5)

    digits = t.replace("+","").replace(" ","").replace("-","")
    if not digits.isdigit() or len(digits) < 7:
        await update.message.reply_text(
            "⚠️  Неверный формат\n\nПример: +992901234567"
        )
        return PHONE

    context.user_data["phone"] = t
    return await show_confirm(update, context)

# ═══════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ
# ═══════════════════════════════════════
async def show_confirm(update, context):
    ud      = context.user_data
    extra   = ud.get("extra", 0)
    total   = ud["price"] + extra
    photo   = "✅ Есть" if ud.get("photo_id") else "❌ Нет"
    athlete = ud.get("athlete_name", "")
    icon    = "👕" if "Футболка" in ud["product"] else "🧥"

    lines = [
        "📋  ПРОВЕРЬ ЗАКАЗ",
        "━━━━━━━━━━━━━━━━━━━━",
        f"{icon}  {ud['product']}  ·  {ud['size']}",
        f"🎨  {ud['print_type']}",
    ]
    if athlete:
        lines.append(f"🥊  {athlete}")
    lines += [
        f"📸  Фото:    {photo}",
        f"✍️   Надпись: {ud.get('print_text','—')}",
        f"📱  Тел:     {ud['phone']}",
        "┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄",
        f"💰  Цена:    от {ud['price']} сом",
    ]
    if extra:
        lines.append(f"➕  Доп.:    +{extra} сом")
    lines += [
        f"💵  ИТОГО:   от {total} сом",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "Всё верно?",
    ]
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=kb(
            ["✅ Оформить заказ"],
            ["✏️ Изменить параметры"],
            ["❌ Отменить"],
        )
    )
    return CONFIRM

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text

    if t == "✏️ Изменить параметры":
        return await edit_entry(update, context)

    if t == "❌ Отменить":
        context.user_data.clear()
        await update.message.reply_text("❌  Заказ отменён.", reply_markup=main_kb())
        return WELCOME

    if t != "✅ Оформить заказ":
        await update.message.reply_text("Выбери действие 👇")
        return CONFIRM

    user  = update.message.from_user
    ud    = context.user_data
    extra = ud.get("extra", 0)

    order = {
        "name":       user.first_name or "—",
        "username":   f"@{user.username}" if user.username else "—",
        "user_id":    user.id,
        "product":    ud["product"],
        "size":       ud["size"],
        "print_type": ud["print_type"],
        "athlete":    ud.get("athlete_name", ""),
        "print_text": ud.get("print_text", "—"),
        "photo_id":   ud.get("photo_id"),
        "phone":      ud["phone"],
        "price":      ud["price"],
        "extra":      extra,
    }
    oid   = db_add(order)
    order = db_get(oid)

    await update.message.reply_text(
        f"🎉  ЗАКАЗ #{oid} ОФОРМЛЕН!\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Мы позвоним на {ud['phone']}\n"
        "в ближайшее время.\n\n"
        "Сделаем эскиз → согласуем\n"
        "Напечатаем → доставим 🖤\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Спасибо что выбрал PATHA!",
        reply_markup=main_kb()
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=fmt_order(order, admin=True),
            reply_markup=admin_kb(oid, "new", user.id)
        )
        if order.get("photo_id"):
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=order["photo_id"],
                caption=f"📸 Фото · Заказ #{oid}"
            )
    except Exception as e:
        print(f"Ошибка отправки админу: {e}")

    context.user_data.clear()
    return WELCOME

# ═══════════════════════════════════════
#  МОЙ ЗАКАЗ
# ═══════════════════════════════════════
async def show_my_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text(
            "📭  У тебя пока нет заказов.\n\nОформи первый! 👇",
            reply_markup=main_kb()
        )
        return WELCOME
    await update.message.reply_text(
        fmt_order(o),
        reply_markup=kb(["✏️ Изменить заказ"], ["🛍 Оформить заказ"], ["🏠 Меню"])
    )
    return WELCOME

# ═══════════════════════════════════════
#  РЕДАКТИРОВАНИЕ
# ═══════════════════════════════════════
async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text("❌  Нет заказов для изменения.", reply_markup=main_kb())
        return WELCOME
    context.user_data["edit_oid"] = o["id"]
    await update.message.reply_text(
        f"✏️  ИЗМЕНИТЬ ЗАКАЗ #{o['id']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Что хочешь изменить?",
        reply_markup=kb(
            ["📐 Размер", "✍️ Надпись"],
            ["📱 Телефон"],
            ["⬅️ Назад к заказу"],
        )
    )
    return EDIT_MENU

async def edit_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "⬅️ Назад к заказу":
        return await show_my_order(update, context)
    if t == "📐 Размер":
        await update.message.reply_text(
            "Выбери новый размер:",
            reply_markup=kb(["S","M","L"], ["XL","XXL"], ["⬅️ Назад"])
        )
        return EDIT_SIZE
    if t == "✍️ Надпись":
        await update.message.reply_text(
            "Напиши новую надпись\n(нет — чтобы убрать):",
            reply_markup=kb(["⬅️ Назад"])
        )
        return EDIT_TEXT
    if t == "📱 Телефон":
        await update.message.reply_text(
            "Введи новый номер:\nФормат: +992XXXXXXXXX",
            reply_markup=kb(["⬅️ Назад"])
        )
        return EDIT_PHONE
    return EDIT_MENU

async def edit_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t == "⬅️ Назад":
        return await edit_entry(update, context)
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

async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    if t == "⬅️ Назад":
        return await edit_entry(update, context)
    new_text = "—" if t.lower() == "нет" else t
    oid = context.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o["print_text"] if o else "?"
    db_update(oid, print_text=new_text)
    await _notify_change(context, oid, f"Надпись: «{old}» → «{new_text}»")
    await update.message.reply_text("✅  Надпись изменена!", reply_markup=main_kb())
    return WELCOME

async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    t = update.message.text.strip()
    if t == "⬅️ Назад":
        return await edit_entry(update, context)
    digits = t.replace("+","").replace(" ","").replace("-","")
    if not digits.isdigit() or len(digits) < 7:
        await update.message.reply_text("⚠️  Неверный формат. Пример: +992901234567")
        return EDIT_PHONE
    oid = context.user_data.get("edit_oid")
    o   = db_get(oid)
    old = o["phone"] if o else "?"
    db_update(oid, phone=t)
    await _notify_change(context, oid, f"Телефон: {old} → {t}")
    await update.message.reply_text("✅  Телефон изменён!", reply_markup=main_kb())
    return WELCOME

async def _notify_change(context, oid, note):
    o = db_get(oid)
    if not o:
        return
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(f"✏️  ИЗМЕНЕНИЕ · Заказ #{oid}\n"
                  f"━━━━━━━━━━━━━━━━━━━━\n"
                  f"📝  {note}\n\n"
                  f"👤  {o.get('name','—')}  {o.get('username','')}\n"
                  f"📱  {o.get('phone','—')}"),
            reply_markup=admin_kb(oid, o.get("status","new"), o.get("user_id",0))
        )
    except Exception as e:
        print(f"Ошибка: {e}")

# ═══════════════════════════════════════
#  CALLBACK — СМЕНА СТАТУСА
# ═══════════════════════════════════════
async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔ Нет доступа", show_alert=True)
        return
    _, oid_str, new_status = q.data.split(":")
    oid = int(oid_str)
    db_update(oid, status=new_status)
    o = db_get(oid)
    if not o:
        await q.edit_message_text("⚠️ Заказ не найден")
        return
    await q.edit_message_text(
        text=fmt_order(o, admin=True),
        reply_markup=admin_kb(oid, new_status, o.get("user_id", 0))
    )
    msg = STATUS_NOTIFY.get(new_status)
    if msg and o.get("user_id"):
        try:
            await context.bot.send_message(
                chat_id=o["user_id"],
                text=msg.replace("{id}", str(oid))
            )
        except Exception as e:
            print(f"Ошибка уведомления: {e}")

# ═══════════════════════════════════════
#  КОМАНДЫ АДМИНА
# ═══════════════════════════════════════
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    args   = context.args
    orders = db_all()
    if not orders:
        await update.message.reply_text("📭 Заказов пока нет.")
        return
    counts = {}
    for o in orders:
        s = o.get("status","new")
        counts[s] = counts.get(s,0) + 1
    stat = "\n".join(f"  {ORDER_STATUSES.get(s,s)}: {c}" for s,c in counts.items())
    await update.message.reply_text(
        f"📊  ПАНЕЛЬ ЗАКАЗОВ\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Всего: {len(orders)}\n\n{stat}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Фильтр: /admin new · confirmed · production · ready"
    )
    flt  = args[0] if args else None
    show = [o for o in orders if o.get("status")==flt] if flt else orders
    for o in reversed(show[-10:]):
        await update.message.reply_text(
            fmt_order(o, admin=True),
            reply_markup=admin_kb(o["id"], o.get("status","new"), o.get("user_id",0))
        )

async def order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /order <номер>")
        return
    o = db_get(int(args[0]))
    if not o:
        await update.message.reply_text(f"⚠️ Заказ #{args[0]} не найден.")
        return
    await update.message.reply_text(
        fmt_order(o, admin=True),
        reply_markup=admin_kb(o["id"], o.get("status","new"), o.get("user_id",0))
    )
    if o.get("photo_id"):
        await update.message.reply_photo(
            photo=o["photo_id"],
            caption=f"📸 Фото · Заказ #{o['id']}"
        )

# ═══════════════════════════════════════
#  ЗАПУСК
# ═══════════════════════════════════════
app = Application.builder().token(BOT_TOKEN).build()

conv = ConversationHandler(
    entry_points=[
        CommandHandler("start", start),
        MessageHandler(filters.TEXT & ~filters.COMMAND, start),
    ],
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
app.add_handler(CallbackQueryHandler(status_callback, pattern=r"^s:\d+:\w+$"))
app.add_handler(CommandHandler("admin", admin_cmd))
app.add_handler(CommandHandler("order", order_cmd))

print("🖤 PATHA бот запущен!")
app.run_polling()
