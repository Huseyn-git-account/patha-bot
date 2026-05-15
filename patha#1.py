import asyncio
import json
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

BOT_TOKEN = "8838090259:AAFMff5XZkaJgNQ3Q-_Akv1aVwwHbPUXhcw"
ADMIN_ID = 6598665549

PRICES = {
    "👕 Футболка": 150,
    "🧥 Худи": 280,
}
EXTRA_CUSTOM = 20

FIGHTERS = {
    "🦅 Хабиб Нурмагомедов": {
        "quotes": [
            "I am not in this sport to make friends",
            "Let's go champ · The Eagle",
            "29-0 · Undefeated · Retired",
            "Alhamdulillah · The Eagle",
        ]
    },
    "🍀 Конор МакГрегор": {
        "quotes": [
            "We're not here to take part, we're here to take over",
            "The Notorious · THE ONE THE ONLY",
            "I am the face of this company",
            "Precision beats power · timing beats speed",
        ]
    },
    "⚡ Забит Магомедшарипов": {
        "quotes": [
            "Zabit Magomedsharipov · The Stylebender of Eagles",
            "Born in Dagestan · Built for greatness",
            "Zabit · The Artist of MMA",
        ]
    },
    "👑 Ислам Махачев": {
        "quotes": [
            "Islam Makhachev · The Champion",
            "Dagestan · Never stops",
            "Islam · The New Era",
        ]
    },
    "🐉 Арман Царукян": {
        "quotes": [
            "Arman Tsarukyan · The Armenian Sniper",
            "Built different · Fighting for glory",
            "Tsarukyan · The Rise",
        ]
    },
    "✏️ Свой вариант бойца (+20 сомони)": {
        "quotes": []
    },
}

PRINT_CATEGORIES = {
    "🥊 Спортсмен / Боец": "Хабиб, МакГрегор, Забит...",
    "👫 Парный принт": "Ваши фото — идеальный подарок",
    "👤 Портрет": "Друг, семья, кумир",
    "✍️ Только надпись": "Имя, цитата, дата",
    "🖼 Своё фото": "Любое фото — мы сделаем принт",
}

orders = []
ORDER_COUNTER = 1

# Сохранение и загрузка телефонов клиентов
USER_PHONES_FILE = "/Users/air/patha/user_phones.json"

def load_user_phones():
    if os.path.exists(USER_PHONES_FILE):
        try:
            with open(USER_PHONES_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_user_phones(phones):
    with open(USER_PHONES_FILE, 'w') as f:
        json.dump(phones, f, indent=2)

user_phones = load_user_phones()

(WELCOME, PRODUCT, SIZE, PRINT_TYPE,
 FIGHTER_CHOICE, CUSTOM_FIGHTER_NAME,
 QUOTE_CHOICE, CUSTOM_TEXT,
 PRINT_PHOTO, PRINT_TEXT,
 PHONE, CONFIRM) = range(12)

(EDIT_MENU, EDIT_SIZE, EDIT_TEXT, EDIT_PHONE, EDIT_CONFIRM) = range(12, 17)


def header(title):
    return f"╔═══ {title} ═══╗\n\n"


def find_last_order_for_user(user_id):
    for o in reversed(orders):
        if o['user_id'] == user_id:
            return o
    return None


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать главное меню"""
    await update.message.reply_text(
        header("PATHA МЕНЮ") +
        "🎨 ИМЕННОЙ ПРИНТ · ДУШАНБЕ 🇹🇯\n\n"
        "Выбери действие:",
        reply_markup=ReplyKeyboardMarkup(
            [["🖤 Новый заказ"], ["📸 Примеры", "☎️ Контакты"], ["📦 Мой заказ", "✏️ Изменить"]],
            resize_keyboard=True
        )
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_main_menu(update, context)
    return WELCOME


async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📦 Мой заказ" or text == "/myorder":
        return await myorder_command(update, context)

    if text == "✏️ Изменить" or text == "/edit":
        return await edit_entry(update, context)

    if text == "📸 Примеры":
        await update.message.reply_text(
            header("НАШИ РАБОТЫ") +
            "  🥊  Хабиб · THE EAGLE\n"
            "  🥊  МакГрегор · THE NOTORIOUS\n"
            "  🥊  Забит Магомедшарипов\n"
            "  🥊  Ислам Махачев\n"
            "  👫  Парные худи с фото\n"
            "  👤  Портреты на заказ\n\n"
            "📲 Instagram: @patha.tj",
            reply_markup=ReplyKeyboardMarkup(
                [["🖤 Новый заказ"], ["☎️ Контакты"]],
                resize_keyboard=True
            )
        )
        return WELCOME

    if text == "☎️ Контакты":
        await update.message.reply_text(
            header("КОНТАКТЫ") +
            "📲 Instagram: @patha.tj\n"
            "💬 Telegram: напиши в чат\n\n"
            "Или оформи заказ — мы сами напишем!",
            reply_markup=ReplyKeyboardMarkup(
                [["🖤 Новый заказ"]],
                resize_keyboard=True
            )
        )
        return WELCOME

    if text == "🖤 Новый заказ":
        context.user_data.clear()
        await update.message.reply_text(
            header("ШАГ 1 из 6") +
            "Что заказываешь?\n\n"
            "👕 Футболка — от 150 сом\n"
            "🧥 Худи — от 280 сом",
            reply_markup=ReplyKeyboardMarkup(
                [["👕 Футболка", "🧥 Худи"], ["🏠 Меню"]],
                resize_keyboard=True
            )
        )
        return PRODUCT

    # Меню по кнопке "Меню"
    if text == "🏠 Меню":
        await show_main_menu(update, context)
        return WELCOME

    await show_main_menu(update, context)
    return WELCOME


async def choose_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🏠 Меню":
        await show_main_menu(update, context)
        return WELCOME
    
    if text not in PRICES:
        await update.message.reply_text("Выбери товар из кнопок 👇")
        return PRODUCT

    context.user_data['product'] = text
    context.user_data['price'] = PRICES[text]
    context.user_data['extra'] = 0

    await update.message.reply_text(
        header("ШАГ 2 из 6") +
        f"✅ Выбрано: {text}\n💰 Цена: от {PRICES[text]} сом\n\n"
        "Теперь размер:",
        reply_markup=ReplyKeyboardMarkup(
            [["S", "M", "L"], ["XL", "XXL"], ["🏠 Меню"]],
            resize_keyboard=True
        )
    )
    return SIZE


async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    size = update.message.text
    
    if size == "🏠 Меню":
        await show_main_menu(update, context)
        return WELCOME
    
    if size not in ["S", "M", "L", "XL", "XXL"]:
        await update.message.reply_text("Выбери размер из кнопок 👇")
        return SIZE

    context.user_data['size'] = size
    buttons = [[cat] for cat in PRINT_CATEGORIES.keys()]

    await update.message.reply_text(
        header("ШАГ 3 из 6") +
        f"✅ Размер: {size}\n\n"
        "Выбери тип принта:",
        reply_markup=ReplyKeyboardMarkup(buttons + [["🏠 Меню"]], resize_keyboard=True)
    )
    return PRINT_TYPE


async def choose_print_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🏠 Меню":
        await show_main_menu(update, context)
        return WELCOME
    
    if text not in PRINT_CATEGORIES:
        await update.message.reply_text("Выбери тип принта из кнопок 👇")
        return PRINT_TYPE

    context.user_data['print_type'] = text

    if text == "🥊 Спортсмен / Боец":
        buttons = [[name] for name in FIGHTERS.keys()]
        await update.message.reply_text(
            header("ШАГ 4 из 6") +
            "Выбери бойца:",
            reply_markup=ReplyKeyboardMarkup(buttons + [["🏠 Меню"]], resize_keyboard=True)
        )
        return FIGHTER_CHOICE

    if text == "✍️ Только надпись":
        context.user_data['photo_id'] = None
        context.user_data['athlete_name'] = ''
        await update.message.reply_text(
            header("ШАГ 4 из 6") +
            "Напиши текст для принта:",
            reply_markup=ReplyKeyboardRemove()
        )
        return PRINT_TEXT

    context.user_data['athlete_name'] = ''
    await update.message.reply_text(
        header("ШАГ 4 из 6") +
        "Отправь фото для принта (или нажми Без фото)",
        reply_markup=ReplyKeyboardMarkup(
            [["⏭ Без фото"], ["🏠 Меню"]], resize_keyboard=True
        )
    )
    return PRINT_PHOTO


async def fighter_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🏠 Меню":
        await show_main_menu(update, context)
        return WELCOME

    if text not in FIGHTERS:
        await update.message.reply_text("Выбери бойца из кнопок 👇")
        return FIGHTER_CHOICE

    if text == "✏️ Свой вариант бойца (+20 сомони)":
        context.user_data['extra'] = EXTRA_CUSTOM
        await update.message.reply_text(
            header("ШАГ 4 из 6") +
            "Напиши имя бойца:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CUSTOM_FIGHTER_NAME

    context.user_data['athlete_name'] = text
    context.user_data['extra'] = 0
    quotes = FIGHTERS[text]["quotes"]
    buttons = [[q] for q in quotes]
    buttons.append(["✍️ Своя надпись"])
    buttons.append(["🤝 Выберёте сами"])

    await update.message.reply_text(
        header("ШАГ 5 из 6") +
        f"✅ Боец: {text}\n\n"
        "Выбери надпись:",
        reply_markup=ReplyKeyboardMarkup(buttons + [["🏠 Меню"]], resize_keyboard=True)
    )
    return QUOTE_CHOICE


async def custom_fighter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data['athlete_name'] = name

    buttons = [
        ["✍️ Своя надпись"],
        ["🤝 Выберёте сами"],
        ["🏠 Меню"],
    ]
    await update.message.reply_text(
        header("ШАГ 5 из 6") +
        f"✅ Боец: {name}\n💰 Доп. плата: +{EXTRA_CUSTOM} сом\n\n"
        "Выбери надпись:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    )
    return QUOTE_CHOICE


async def quote_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🏠 Меню":
        await show_main_menu(update, context)
        return WELCOME

    if text == "✍️ Своя надпись":
        await update.message.reply_text(
            header("ШАГ 5 из 6") +
            "Напиши надпись:",
            reply_markup=ReplyKeyboardRemove()
        )
        return CUSTOM_TEXT

    if text == "🤝 Выберёте сами":
        context.user_data['print_text'] = "🤝 Подберём сами"
        context.user_data['photo_id'] = None
        await _ask_phone(update, context)
        return PHONE

    context.user_data['print_text'] = text
    context.user_data['photo_id'] = None
    await _ask_phone(update, context)
    return PHONE


async def custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['print_text'] = update.message.text.strip()
    context.user_data['photo_id'] = None
    await _ask_phone(update, context)
    return PHONE


async def get_print_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        context.user_data['photo_id'] = update.message.photo[-1].file_id
        await update.message.reply_text(
            header("ШАГ 5 из 6") +
            "✅ Фото получено.\n\nНапиши надпись (или напиши: нет):",
            reply_markup=ReplyKeyboardRemove()
        )
        return PRINT_TEXT

    if update.message.text == "⏭ Без фото":
        context.user_data['photo_id'] = None
        await update.message.reply_text(
            header("ШАГ 5 из 6") +
            "Напиши надпись (или напиши: нет):",
            reply_markup=ReplyKeyboardRemove()
        )
        return PRINT_TEXT

    await update.message.reply_text(
        "Отправь фото или нажми кнопку ⏭",
        reply_markup=ReplyKeyboardMarkup([["⏭ Без фото"]], resize_keyboard=True)
    )
    return PRINT_PHOTO


async def get_print_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data['print_text'] = "—" if text.lower() == "нет" else text
    await _ask_phone(update, context)
    return PHONE


async def _ask_phone(update, context):
    user_id = str(update.message.from_user.id)
    saved_phone = user_phones.get(user_id, "")
    
    if saved_phone:
        msg = (
            header("ШАГ 6 из 6") +
            f"Номер телефона:\n\n"
            f"☎️ Сохранённый: {saved_phone}\n\n"
            "Или напиши новый номер:"
        )
    else:
        msg = (
            header("ШАГ 6 из 6") +
            "Номер телефона.\nФормат: +992901234567"
        )
    
    await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    digits = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    if not digits.isdigit() or len(digits) < 7:
        await update.message.reply_text("❌ Номер неверный. Пример: +992901234567")
        return PHONE

    context.user_data['phone'] = phone
    user_id = str(update.message.from_user.id)
    user_phones[user_id] = phone
    save_user_phones(user_phones)

    product    = context.user_data['product']
    size       = context.user_data['size']
    print_type = context.user_data['print_type']
    athlete    = context.user_data.get('athlete_name', '')
    print_text = context.user_data.get('print_text', '—')
    has_photo  = "✅" if context.user_data.get('photo_id') else "❌"
    price      = context.user_data['price']
    extra      = context.user_data.get('extra', 0)
    total      = price + extra

    athlete_line = f"👤 Боец: {athlete}\n" if athlete else ""
    extra_line   = f"💰 Доп: +{extra} сом\n" if extra else ""

    await update.message.reply_text(
        header("ПРОВЕРЬ ЗАКАЗ") +
        f"👕 {product} · {size}\n"
        f"📌 Тип: {print_type}\n"
        f"{athlete_line}"
        f"🖼 Фото: {has_photo}\n"
        f"✍️ Надпись: {print_text}\n"
        f"☎️ Тел: {phone}\n\n"
        f"💰 Цена: {price} сом\n"
        f"{extra_line}"
        f"📊 ИТОГО: {total} сом\n\n"
        "Всё правильно?",
        reply_markup=ReplyKeyboardMarkup(
            [["✅ Заказать", "❌ Отмена"]],
            resize_keyboard=True
        )
    )
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global ORDER_COUNTER
    
    if update.message.text == "✅ Заказать":
        user = update.message.from_user
        order_id = ORDER_COUNTER
        ORDER_COUNTER += 1
        extra  = context.user_data.get('extra', 0)
        price  = context.user_data['price']
        total  = price + extra

        order = {
            'id':         order_id,
            'name':       user.first_name or "—",
            'username':   f"@{user.username}" if user.username else "—",
            'user_id':    user.id,
            'product':    context.user_data['product'],
            'size':       context.user_data['size'],
            'print_type': context.user_data['print_type'],
            'athlete':    context.user_data.get('athlete_name', '—'),
            'print_text': context.user_data.get('print_text', '—'),
            'photo_id':   context.user_data.get('photo_id'),
            'phone':      context.user_data['phone'],
            'price':      price,
            'extra':      extra,
            'total':      total,
        }
        orders.append(order)

        has_photo    = "✅" if order['photo_id'] else "❌"
        athlete_line = f"👤 Боец: {order['athlete']}\n" if order['athlete'] not in ['—', ''] else ""
        extra_line   = f"💰 Доп: +{extra} сом\n" if extra else ""

        admin_msg = (
            f"🔔 НОВЫЙ ЗАКАЗ #{order['id']}\n"
            f"{'-' * 40}\n"
            f"👤 Клиент: {order['name']} {order['username']}\n"
            f"☎️ Тел: {order['phone']}\n\n"
            f"👕 {order['product']} · {order['size']}\n"
            f"📌 Тип: {order['print_type']}\n"
            f"{athlete_line}"
            f"🖼 Фото: {has_photo}\n"
            f"✍️ Надпись: {order['print_text']}\n\n"
            f"💰 Цена: {order['price']} сом\n"
            f"{extra_line}"
            f"📊 ИТОГО: {order['total']} сом\n"
            f"{'-' * 40}\n"
            f"👤 Профиль: tg://user?id={order['user_id']}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
            if order['photo_id']:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=order['photo_id'],
                    caption=f"📸 Фото заказа #{order_id}"
                )
        except Exception as e:
            print(f"Ошибка: {e}")

        await update.message.reply_text(
            header("✅ ЗАКАЗ ПРИНЯТ") +
            f"Заказ #{order_id} оформлен!\n"
            f"Мы позвоним по {order['phone']}\n\n"
            "Спасибо за заказ! 🖤",
            reply_markup=ReplyKeyboardMarkup(
                [["🖤 Новый заказ"], ["📦 Мой заказ", "✏️ Изменить"]],
                resize_keyboard=True
            )
        )
    else:
        await update.message.reply_text(
            "❌ Заказ отменён.",
            reply_markup=ReplyKeyboardMarkup(
                [["🖤 Новый заказ"]],
                resize_keyboard=True
            )
        )

    context.user_data.clear()
    return WELCOME


async def myorder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    o = find_last_order_for_user(user.id)
    if not o:
        await update.message.reply_text(
            "❌ У тебя ещё нет заказов.",
            reply_markup=ReplyKeyboardMarkup([["🖤 Новый заказ"]], resize_keyboard=True)
        )
        return WELCOME

    has_photo = "✅" if o['photo_id'] else "❌"
    athlete_line = f"👤 Боец: {o['athlete']}\n" if o['athlete'] not in ['—', ''] else ""
    extra_line   = f"💰 Доп: +{o['extra']} сом\n" if o['extra'] else ""

    await update.message.reply_text(
        header(f"ЗАКАЗ #{o['id']}") +
        f"👕 {o['product']} · {o['size']}\n"
        f"📌 Тип: {o['print_type']}\n"
        f"{athlete_line}"
        f"🖼 Фото: {has_photo}\n"
        f"✍️ Надпись: {o['print_text']}\n"
        f"☎️ Тел: {o['phone']}\n\n"
        f"📊 ИТОГО: {o['total']} сом\n",
        reply_markup=ReplyKeyboardMarkup([["✏️ Изменить"], ["🖤 Новый заказ"]], resize_keyboard=True)
    )
    return WELCOME


async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    o = find_last_order_for_user(user.id)
    if not o:
        await update.message.reply_text(
            "❌ Нет заказов для редактирования.",
            reply_markup=ReplyKeyboardMarkup([["🖤 Новый заказ"]], resize_keyboard=True)
        )
        return WELCOME

    context.user_data['edit_order_id'] = o['id']
    await update.message.reply_text(
        header(f"ИЗМЕНИТЬ ЗАКАЗ #{o['id']}") +
        "Что менять?",
        reply_markup=ReplyKeyboardMarkup(
            [["Размер"], ["Надпись"], ["Телефон"], ["◀️ Назад"]],
            resize_keyboard=True
        )
    )
    return EDIT_MENU


async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "◀️ Назад":
        return await welcome_handler(update, context)
    
    if text == "Размер":
        await update.message.reply_text(
            "Новый размер:",
            reply_markup=ReplyKeyboardMarkup([["S","M","L"],["XL","XXL"],["◀️ Назад"]], resize_keyboard=True)
        )
        return EDIT_SIZE
    if text == "Надпись":
        await update.message.reply_text(
            "Новая надпись (или напиши: нет):",
            reply_markup=ReplyKeyboardRemove()
        )
        return EDIT_TEXT
    if text == "Телефон":
        await update.message.reply_text(
            "Новый номер телефона:",
            reply_markup=ReplyKeyboardRemove()
        )
        return EDIT_PHONE
    
    return EDIT_MENU


async def edit_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    size = update.message.text
    
    if size == "◀️ Назад":
        return await edit_entry(update, context)
    
    if size not in ["S", "M", "L", "XL", "XXL"]:
        await update.message.reply_text("Выбери размер из кнопок 👇")
        return EDIT_SIZE

    oid = context.user_data.get('edit_order_id')
    for o in orders:
        if o['id'] == oid:
            old_size = o['size']
            o['size'] = size
            await notify_admin_change(context, oid, f"Размер: {old_size} → {size}")
            break

    await update.message.reply_text(
        "✅ Размер изменён!",
        reply_markup=ReplyKeyboardMarkup([["📦 Мой заказ"], ["🖤 Новый заказ"]], resize_keyboard=True)
    )
    return WELCOME


async def edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    new_text = "—" if text.lower() == "нет" else text
    oid = context.user_data.get('edit_order_id')
    
    for o in orders:
        if o['id'] == oid:
            old_text = o['print_text']
            o['print_text'] = new_text
            await notify_admin_change(context, oid, f"Надпись: '{old_text}' → '{new_text}'")
            break

    await update.message.reply_text(
        "✅ Надпись изменена!",
        reply_markup=ReplyKeyboardMarkup([["📦 Мой заказ"], ["🖤 Новый заказ"]], resize_keyboard=True)
    )
    return WELCOME


async def edit_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    digits = phone.replace("+", "").replace(" ", "").replace("-", "")
    
    if not digits.isdigit() or len(digits) < 7:
        await update.message.reply_text("❌ Номер неверный.")
        return EDIT_PHONE

    oid = context.user_data.get('edit_order_id')
    for o in orders:
        if o['id'] == oid:
            old_phone = o['phone']
            o['phone'] = phone
            user_id = str(o['user_id'])
            user_phones[user_id] = phone
            save_user_phones(user_phones)
            await notify_admin_change(context, oid, f"Телефон: {old_phone} → {phone}")
            break

    await update.message.reply_text(
        "✅ Телефон изменён!",
        reply_markup=ReplyKeyboardMarkup([["📦 Мой заказ"], ["🖤 Новый заказ"]], resize_keyboard=True)
    )
    return WELCOME


async def notify_admin_change(context: ContextTypes.DEFAULT_TYPE, order_id: int, note: str):
    try:
        o = next((x for x in orders if x['id'] == order_id), None)
        if not o:
            return
        msg = (
            f"✏️ ИЗМЕНЕНИЕ ЗАКАЗА #{o['id']}\n"
            f"{'-' * 40}\n"
            f"📝 {note}\n\n"
            f"👕 {o['product']} · {o['size']}\n"
            f"✍️ Надпись: {o['print_text']}\n"
            f"☎️ Тел: {o['phone']}\n"
            f"👤 Клиент: {o['name']} tg://user?id={o['user_id']}"
        )
        await context.bot.send_message(chat_id=ADMIN_ID, text=msg)
    except Exception as e:
        print(f"Ошибка уведомления: {e}")


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return
    if not orders:
        await update.message.reply_text("📭 Заказов пока нет.")
        return

    msg = f"📊 ПАНЕЛЬ АДМИНИСТРАТОРА\n{'-' * 50}\n\n"
    msg += f"Всего заказов: {len(orders)}\n\n"
    
    for o in orders:
        has_photo    = "✅" if o['photo_id'] else "❌"
        athlete_line = f"👤 Боец: {o['athlete']}\n" if o['athlete'] not in ['—', ''] else ""
        extra_line   = f"💰 Доп: +{o['extra']} сом\n" if o['extra'] else ""
        
        msg += (
            f"🔹 ЗАКАЗ #{o['id']}\n"
            f"👤 {o['name']} {o['username']}\n"
            f"☎️ {o['phone']}\n"
            f"👕 {o['product']} · {o['size']}\n"
            f"📌 Тип: {o['print_type']}\n"
            f"{athlete_line}"
            f"✍️ Надпись: {o['print_text']}\n"
            f"🖼 Фото: {has_photo}\n"
            f"💰 Сумма: {o['price']} сом\n"
            f"{extra_line}"
            f"📊 ИТОГО: {o['total']} сом\n"
            f"{'-' * 50}\n\n"
        )

    for i in range(0, len(msg), 4000):
        await update.message.reply_text(msg[i:i+4000])


app = Application.builder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start), MessageHandler(filters.TEXT, welcome_handler)],
    states={
        WELCOME:            [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_handler)],
        PRODUCT:            [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_product)],
        SIZE:               [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_size)],
        PRINT_TYPE:         [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_print_type)],
        FIGHTER_CHOICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, fighter_choice)],
        CUSTOM_FIGHTER_NAME:[MessageHandler(filters.TEXT & ~filters.COMMAND, custom_fighter_name)],
        QUOTE_CHOICE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, quote_choice)],
        CUSTOM_TEXT:        [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_text)],
        PRINT_PHOTO:        [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_print_photo)],
        PRINT_TEXT:         [MessageHandler(filters.TEXT & ~filters.COMMAND, get_print_text)],
        PHONE:              [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CONFIRM:            [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
        EDIT_MENU:          [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choice)],
        EDIT_SIZE:          [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_size)],
        EDIT_TEXT:          [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
        EDIT_PHONE:         [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_phone)],
        EDIT_CONFIRM:       [],
    },
    fallbacks=[CommandHandler('start', start)]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler('admin', admin_cmd))
app.add_handler(CommandHandler('myorder', myorder_command))
app.add_handler(CommandHandler('edit', edit_entry))

print("🖤 PATHA бот запущен!")
app.run_polling()