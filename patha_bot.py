"""
🖤  P A T H A  B O T  v4.0
Именной принт · Душанбе 🇹🇯
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
    ReplyKeyboardRemove,
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

logging.basicConfig(
    format="%(asctime)s │ %(name)s │ %(levelname)s │ %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════
#  КОНФИГ
# ══════════════════════════════════════
BOT_TOKEN   = "8838090259:AAFMff5XZkaJgNQ3Q-_Akv1aVwwHbPUXhcw"
ADMIN_ID    = 6598665549
ORDERS_FILE = "patha_orders.json"

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

STATUS_NOTIFY: dict[str, str] = {
    "confirmed": (
        "✅ Заказ принят!\n\n"
        "Привет! Мы получили твой заказ #{id} 🖤\n\n"
        "Скоро позвоним и согласуем эскиз.\n"
        "Ожидай звонка!"
    ),
    "production": (
        "🔨 Твой заказ #{id} в работе!\n\n"
        "Уже печатаем принт.\n"
        "Скоро будет готово 💪"
    ),
    "ready": (
        "📦 Готово! Заказ #{id} ждёт тебя!\n\n"
        "Свяжемся насчёт доставки\n"
        "или самовывоза 🖤"
    ),
    "delivered": (
        "🚀 Доставлено!\n\n"
        "Заказ #{id} у тебя.\n\n"
        "Носи с гордостью! 🖤\n"
        "Будем рады отзыву → @patha.tj"
    ),
    "cancelled": (
        "❌ Заказ #{id} отменён.\n\n"
        "Если есть вопросы — напиши нам:\n"
        "→ @patha_tj"
    ),
}

# ══════════════════════════════════════
#  СОСТОЯНИЯ
# ══════════════════════════════════════
(
    WELCOME,
    PRODUCT,
    SIZE,
    PRINT_TYPE,
    FIGHTER_CHOICE,
    CUSTOM_FIGHTER_NAME,
    QUOTE_CHOICE,
    CUSTOM_TEXT,
    PRINT_PHOTO,
    PRINT_TEXT,
    PHONE,
    CONFIRM,
    EDIT_MENU,
    EDIT_SIZE,
    EDIT_TEXT,
    EDIT_PHONE,
) = range(16)

# ══════════════════════════════════════
#  БАЗА ДАННЫХ
# ══════════════════════════════════════

def _load_db() -> dict:
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
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
    order.update({
        "id":      oid,
        "status":  "new",
        "created": datetime.now().strftime("%d.%m.%Y %H:%M"),
    })
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
    else:
        logger.warning("db_update: заказ %s не найден", oid)


def db_all() -> list[dict]:
    return list(_load_db()["orders"].values())


def db_last_for_user(user_id: int) -> dict | None:
    user_orders = [o for o in db_all() if o.get("user_id") == user_id]
    return user_orders[-1] if user_orders else None

# ══════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════

def kb(*rows: list[str], nav: bool = False) -> ReplyKeyboardMarkup:
    buttons = [list(r) for r in rows]
    if nav:
        buttons.append(["⬅️ Назад", "🏠 Меню"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            ["🛍 Оформить заказ"],
            ["📸 Примеры", "📞 Контакты"],
            ["📦 Мой заказ"],
        ],
        resize_keyboard=True,
    )


# ══════════════════════════════════════
#  ДИЗАЙН СООБЩЕНИЙ — МОБИЛЬНЫЙ СТИЛЬ
#  Принципы топ-ботов:
#  • короткие строки (помещаются на экран телефона)
#  • крупные эмодзи как иконки
#  • чёткие разделители
#  • прогресс через точки •○○ (не ASCII-рамки)
#  • минимум текста — максимум ясности
# ══════════════════════════════════════

STEPS = ["", "товар", "размер", "принт", "детали", "надпись", "телефон"]

def step_header(n: int) -> str:
    """Красивый заголовок шага — стиль лучших shop-ботов."""
    dots = "●" * n + "○" * (6 - n)
    return f"[ {dots} ]  {n} из 6"


def fmt_order(o: dict, *, admin: bool = False) -> str:
    """Карточка заказа — чистый мобильный дизайн."""
    extra   = o.get("extra", 0)
    total   = o.get("price", 0) + extra
    photo   = "✅" if o.get("photo_id") else "❌"
    status  = ORDER_STATUSES.get(o.get("status", "new"), "🆕 Новый")
    icon    = "👕" if "Футболка" in o.get("product", "") else "🧥"
    athlete = o.get("athlete") or ""
    prod    = o.get("product", "—").replace("👕 ", "").replace("🧥 ", "")

    lines = [f"#{o['id']} · {status}"]
    lines.append("—" * 22)

    if admin:
        lines += [
            f"👤  {o.get('name', '—')}  {o.get('username', '')}",
            f"📱  {o.get('phone', '—')}",
            f"🕐  {o.get('created', '—')}",
            "·" * 22,
        ]

    lines += [
        f"{icon}  {prod}  •  размер {o.get('size', '—')}",
        f"🎨  {o.get('print_type', '—')}",
    ]
    if athlete and athlete not in ("—", ""):
        lines.append(f"🥊  {athlete}")

    lines += [
        f"📸  фото {photo}",
        f"✍️  {o.get('print_text', '—')}",
        "·" * 22,
        f"💰  {o.get('price', 0)} сом",
    ]
    if extra:
        lines.append(f"➕  +{extra} сом (свой боец)")
    lines.append(f"💵  итого  {total} сом")

    if admin:
        lines += [
            "—" * 22,
            f"tg://user?id={o.get('user_id', '')}",
        ]

    return "\n".join(lines)


def admin_kb(oid: int, status: str, user_id: int) -> InlineKeyboardMarkup:
    flow = {
        "new":        "confirmed",
        "confirmed":  "production",
        "production": "ready",
        "ready":      "delivered",
    }
    labels = {
        "confirmed":  "✅ Принять",
        "production": "🔨 В работу",
        "ready":      "📦 Готов",
        "delivered":  "🚀 Доставлен",
    }
    rows: list[list[InlineKeyboardButton]] = []

    if status in flow:
        nxt = flow[status]
        rows.append([
            InlineKeyboardButton(labels[nxt], callback_data=f"s:{oid}:{nxt}"),
            InlineKeyboardButton("❌ Отмена", callback_data=f"s:{oid}:cancelled"),
        ])

    rows.append([
        InlineKeyboardButton("💬 Написать клиенту", url=f"tg://user?id={user_id}"),
    ])
    return InlineKeyboardMarkup(rows)


# ══════════════════════════════════════
#  /start
# ══════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "🖤  P A T H A\n"
        "Именной принт · Душанбе\n\n"
        "👕  Футболка  —  от 150 сом\n"
        "🧥  Худи       —  от 280 сом\n\n"
        "Своя история на своей одежде ✊",
        reply_markup=main_kb(),
    )
    return WELCOME


async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text

    if t == "📸 Примеры":
        await update.message.reply_text(
            "📸  Примеры работ\n\n"
            "🦅  Хабиб · THE EAGLE\n"
            "🍀  МакГрегор · NOTORIOUS\n"
            "⚡  Забит · Artist of MMA\n"
            "👑  Ислам Махачев · Champion\n"
            "👫  Парные худи с фото\n"
            "👤  Портреты на заказ\n\n"
            "📲  @patha.tj в Instagram",
            reply_markup=main_kb(),
        )
        return WELCOME

    if t == "📞 Контакты":
        await update.message.reply_text(
            "📞  Контакты\n\n"
            "📸  Instagram · @patha.tj\n"
            "✈️  Telegram  · @patha_tj\n\n"
            "Оформи заказ — сами свяжемся 🖤",
            reply_markup=main_kb(),
        )
        return WELCOME

    if t == "📦 Мой заказ":
        return await show_my_order(update, context)

    if t in ("🛍 Оформить заказ", "🏠 Меню"):
        return await ask_product(update, context)

    await update.message.reply_text(
        "Привет! 👋  Я бот PATHA.\nНажми кнопку ниже 👇",
        reply_markup=main_kb(),
    )
    return WELCOME


# ══════════════════════════════════════
#  ШАГ 1 — ТОВАР
# ══════════════════════════════════════

async def ask_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"{step_header(1)}\n\n"
        "Что заказываешь?\n\n"
        "👕  Футболка  —  150 сом\n"
        "🧥  Худи       —  280 сом",
        reply_markup=kb(["👕 Футболка", "🧥 Худи"], ["🏠 Меню"]),
    )
    return PRODUCT


async def choose_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "🏠 Меню":
        return await start(update, context)
    if t not in PRICES:
        await update.message.reply_text("Выбери из кнопок 👇")
        return PRODUCT
    context.user_data.update(product=t, price=PRICES[t], extra=0)
    return await ask_size(update, context)


# ══════════════════════════════════════
#  ШАГ 2 — РАЗМЕР
# ══════════════════════════════════════

async def ask_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    p = context.user_data.get("product", "")
    await update.message.reply_text(
        f"{step_header(2)}\n\n"
        f"✅  {p}\n\n"
        "Выбери размер:",
        reply_markup=kb(["S", "M", "L"], ["XL", "XXL"], nav=True),
    )
    return SIZE


async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_product(update, context)
    if t not in SIZES:
        await update.message.reply_text("Выбери размер из кнопок 👇")
        return SIZE
    context.user_data["size"] = t
    return await ask_print_type(update, context)


# ══════════════════════════════════════
#  ШАГ 3 — ТИП ПРИНТА
# ══════════════════════════════════════

async def ask_print_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"{step_header(3)}\n\n"
        "Что печатаем?",
        reply_markup=kb(*[[pt] for pt in PRINT_TYPES], nav=True),
    )
    return PRINT_TYPE


async def choose_print_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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


# ══════════════════════════════════════
#  ШАГ 4а — БОЕЦ
# ══════════════════════════════════════

async def ask_fighter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"{step_header(4)}\n\n"
        "Выбери бойца:\n\n"
        "✏️  Свой вариант = +20 сом",
        reply_markup=kb(*[[f] for f in FIGHTERS.keys()], nav=True),
    )
    return FIGHTER_CHOICE


async def fighter_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
            "Доп. плата +20 сом\n"
            "(поиск фото + дизайн)",
            reply_markup=kb(["⬅️ Назад"]),
        )
        return CUSTOM_FIGHTER_NAME
    context.user_data.update(athlete_name=t, extra=0)
    return await ask_quote(update, context)


async def custom_fighter_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "⬅️ Назад":  return await ask_fighter(update, context)
    if t == "🏠 Меню":   return await start(update, context)
    name = t.strip()
    if not name:
        await update.message.reply_text("Напиши имя бойца 👇")
        return CUSTOM_FIGHTER_NAME
    context.user_data["athlete_name"] = name
    return await ask_quote(update, context)


# ══════════════════════════════════════
#  ШАГ 5а — ЦИТАТА
# ══════════════════════════════════════

async def ask_quote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    athlete = context.user_data.get("athlete_name", "")
    quotes  = FIGHTERS.get(athlete, [])
    q_text  = "\n".join(f"· {q}" for q in quotes) if quotes else ""

    body = f"{step_header(5)}\n\n🥊  {athlete}\n\nНадпись для принта:"
    if q_text:
        body += f"\n\n{q_text}"

    await update.message.reply_text(
        body,
        reply_markup=kb(
            *[[q] for q in quotes],
            ["✍️ Своя надпись"],
            ["🤝 Вы сами подберёте"],
            nav=True,
        ),
    )
    return QUOTE_CHOICE


async def quote_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":  return await ask_fighter(update, context)
    if t == "✍️ Своя надпись":
        await update.message.reply_text(
            "✍️  Напиши надпись:\n\n"
            "Имя · цитата · дата — любой текст",
            reply_markup=kb(["⬅️ Назад"]),
        )
        return CUSTOM_TEXT
    if t == "🤝 Вы сами подберёте":
        context.user_data.update(print_text="🤝 Подберёте сами", photo_id=None)
        return await ask_phone(update, context)
    athlete = context.user_data.get("athlete_name", "")
    valid   = FIGHTERS.get(athlete, [])
    if valid and t not in valid:
        await update.message.reply_text("Выбери из кнопок 👇")
        return QUOTE_CHOICE
    context.user_data.update(print_text=t, photo_id=None)
    return await ask_phone(update, context)


async def custom_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "⬅️ Назад":  return await ask_quote(update, context)
    if t == "🏠 Меню":   return await start(update, context)
    text = t.strip()
    if not text:
        await update.message.reply_text("Напиши надпись 👇")
        return CUSTOM_TEXT
    context.user_data.update(print_text=text, photo_id=None)
    return await ask_phone(update, context)


# ══════════════════════════════════════
#  ШАГ 4б — ФОТО
# ══════════════════════════════════════

async def ask_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"{step_header(4)}\n\n"
        "📷  Отправь фото для принта\n\n"
        "Или нажми «Без фото»",
        reply_markup=kb(["⏭ Без фото"], nav=True),
    )
    return PRINT_PHOTO


async def get_print_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text or ""
    if text == "🏠 Меню":   return await start(update, context)
    if text == "⬅️ Назад":  return await ask_print_type(update, context)
    if update.message.photo:
        context.user_data["photo_id"] = update.message.photo[-1].file_id
        await update.message.reply_text("✅  Фото получено!")
        return await ask_print_text(update, context, step=5)
    if text == "⏭ Без фото":
        context.user_data["photo_id"] = None
        return await ask_print_text(update, context, step=5)
    await update.message.reply_text(
        "📸  Отправь фото или нажми «Без фото»",
        reply_markup=kb(["⏭ Без фото"], nav=True),
    )
    return PRINT_PHOTO


async def ask_print_text(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    step: int = 5,
) -> int:
    await update.message.reply_text(
        f"{step_header(step)}\n\n"
        "✍️  Надпись для принта\n\n"
        "Напиши имя, цитату или дату.\n"
        "Нет надписи? Напиши: нет",
        reply_markup=kb(["⬅️ Назад"]),
    )
    return PRINT_TEXT


async def get_print_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == "⬅️ Назад":  return await ask_photo(update, context)
    if t == "🏠 Меню":   return await start(update, context)
    context.user_data["print_text"] = "—" if t.lower() == "нет" else t
    return await ask_phone(update, context)


# ══════════════════════════════════════
#  ШАГ 6 — ТЕЛЕФОН
# ══════════════════════════════════════

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"{step_header(6)}\n\n"
        "📱  Твой номер телефона\n\n"
        "Позвоним, сделаем эскиз\n"
        "и согласуем с тобой 🖤\n\n"
        "Формат: +992XXXXXXXXX",
        reply_markup=kb(["⬅️ Назад"]),
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text.strip()
    if t == "🏠 Меню":   return await start(update, context)
    if t == "⬅️ Назад":
        pt = context.user_data.get("print_type", "")
        if pt == "🥊 Спортсмен / Боец":
            return await ask_quote(update, context)
        elif pt == "✍️ Только надпись":
            return await ask_print_text(update, context, step=4)
        else:
            return await ask_print_text(update, context, step=5)
    digits = t.replace("+", "").replace(" ", "").replace("-", "")
    if not digits.isdigit() or not (7 <= len(digits) <= 15):
        await update.message.reply_text(
            "⚠️  Неверный номер.\n\nПример: +992901234567",
            reply_markup=kb(["⬅️ Назад"]),
        )
        return PHONE
    context.user_data["phone"] = t
    return await show_confirm(update, context)


# ══════════════════════════════════════
#  ПОДТВЕРЖДЕНИЕ
# ══════════════════════════════════════

async def show_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud      = context.user_data
    extra   = ud.get("extra", 0)
    total   = ud.get("price", 0) + extra
    photo   = "✅" if ud.get("photo_id") else "❌"
    athlete = ud.get("athlete_name", "")
    icon    = "👕" if "Футболка" in ud.get("product", "") else "🧥"
    prod    = ud.get("product", "—").replace("👕 ", "").replace("🧥 ", "")

    lines = [
        "Проверь заказ 👇",
        "",
        f"{icon}  {prod}  •  размер {ud.get('size', '—')}",
        f"🎨  {ud.get('print_type', '—')}",
    ]
    if athlete:
        lines.append(f"🥊  {athlete}")
    lines += [
        f"📸  фото {photo}",
        f"✍️  {ud.get('print_text', '—')}",
        f"📱  {ud.get('phone', '—')}",
        "",
        f"💰  {ud.get('price', 0)} сом",
    ]
    if extra:
        lines.append(f"➕  +{extra} сом")
    lines += [
        f"💵  итого  {total} сом",
        "",
        "Всё верно?",
    ]

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=kb(
            ["✅ Оформить заказ"],
            ["✏️ Изменить"],
            ["❌ Отменить"],
        ),
    )
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text

    if t == "✏️ Изменить":
        return await ask_product(update, context)

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

    new_order: dict = {
        "name":       user.first_name or "—",
        "username":   f"@{user.username}" if user.username else "—",
        "user_id":    user.id,
        "product":    ud.get("product", "—"),
        "size":       ud.get("size", "—"),
        "print_type": ud.get("print_type", "—"),
        "athlete":    ud.get("athlete_name", ""),
        "print_text": ud.get("print_text", "—"),
        "photo_id":   ud.get("photo_id"),
        "phone":      ud.get("phone", "—"),
        "price":      ud.get("price", 0),
        "extra":      extra,
    }

    oid   = db_add(new_order)
    order = db_get(oid)

    await update.message.reply_text(
        f"🎉  Заказ #{oid} оформлен!\n\n"
        f"Позвоним на {ud.get('phone', '—')}\n"
        "в ближайшее время.\n\n"
        "Сделаем эскиз → согласуем\n"
        "Напечатаем → доставим 🖤\n\n"
        "Спасибо что выбрал PATHA!",
        reply_markup=main_kb(),
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=fmt_order(order, admin=True),
            reply_markup=admin_kb(oid, "new", user.id),
        )
        if order.get("photo_id"):
            await context.bot.send_photo(
                chat_id=ADMIN_ID,
                photo=order["photo_id"],
                caption=f"📸  фото · заказ #{oid}",
            )
    except TelegramError as exc:
        logger.error("Ошибка отправки админу: %s", exc)

    context.user_data.clear()
    return WELCOME


# ══════════════════════════════════════
#  МОЙ ЗАКАЗ
# ══════════════════════════════════════

async def show_my_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text(
            "📭  Заказов пока нет.\n\nОформи первый! 👇",
            reply_markup=main_kb(),
        )
        return WELCOME
    await update.message.reply_text(
        fmt_order(o),
        reply_markup=kb(
            ["✏️ Изменить заказ"],
            ["🛍 Новый заказ"],
            ["🏠 Меню"],
        ),
    )
    return WELCOME


# ══════════════════════════════════════
#  РЕДАКТИРОВАНИЕ
# ══════════════════════════════════════

async def edit_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    o = db_last_for_user(update.message.from_user.id)
    if not o:
        await update.message.reply_text(
            "❌  Нет заказов для изменения.",
            reply_markup=main_kb(),
        )
        return WELCOME
    if o.get("status") in ("delivered", "cancelled"):
        await update.message.reply_text(
            f"⚠️  Заказ #{o['id']} нельзя изменить.\n"
            f"Статус: {ORDER_STATUSES.get(o['status'])}",
            reply_markup=main_kb(),
        )
        return WELCOME
    context.user_data["edit_oid"] = o["id"]
    await update.message.reply_text(
        f"✏️  Заказ #{o['id']}\n\nЧто меняем?",
        reply_markup=kb(
            ["📐 Размер", "✍️ Надпись"],
            ["📱 Телефон"],
            ["⬅️ К заказу"],
        ),
    )
    return EDIT_MENU


async def edit_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t in ("⬅️ К заказу", "🏠 Меню"):
        return await show_my_order(update, context)
    if t == "📐 Размер":
        await update.message.reply_text(
            "Выбери новый размер:",
            reply_markup=kb(["S", "M", "L"], ["XL", "XXL"], ["⬅️ Назад"]),
        )
        return EDIT_SIZE
    if t == "✍️ Надпись":
        await update.message.reply_text(
            "Напиши новую надпись\n(«нет» — чтобы убрать):",
            reply_markup=kb(["⬅️ Назад"]),
        )
        return EDIT_TEXT
    if t == "📱 Телефон":
        await update.message.reply_text(
            "Введи новый номер:\n+992XXXXXXXXX",
            reply_markup=kb(["⬅️ Назад"]),
        )
        return EDIT_PHONE
    return EDIT_MENU


async def edit_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    t = update.message.text
    if t == "⬅️ Назад":  return await edit_entry(update, context)
    if t == "🏠 Меню":   return await start(update, context)
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
    if t == "⬅️ Назад":  return await edit_entry(update, context)
    if t == "🏠 Меню":   return await start(update, context)
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
    if t == "⬅️ Назад":  return await edit_entry(update, context)
    if t == "🏠 Меню":   return await start(update, context)
    digits = t.replace("+", "").replace(" ", "").replace("-", "")
    if not digits.isdigit() or not (7 <= len(digits) <= 15):
        await update.message.reply_text(
            "⚠️  Неверный формат.\nПример: +992901234567",
            reply_markup=kb(["⬅️ Назад"]),
        )
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
    if not o:
        return
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"✏️  Изменение · заказ #{oid}\n\n"
                f"📝  {note}\n\n"
                f"👤  {o.get('name', '—')}  {o.get('username', '')}\n"
                f"📱  {o.get('phone', '—')}"
            ),
            reply_markup=admin_kb(oid, o.get("status", "new"), o.get("user_id", 0)),
        )
    except TelegramError as exc:
        logger.error("Ошибка уведомления: %s", exc)


# ══════════════════════════════════════
#  CALLBACK — СМЕНА СТАТУСА (АДМИН)
# ══════════════════════════════════════

async def status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q: CallbackQuery = update.callback_query

    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔  Нет доступа", show_alert=True)
        return

    await q.answer()

    parts = q.data.split(":")
    if len(parts) != 3 or not parts[1].isdigit():
        logger.warning("Некорректный callback: %s", q.data)
        return

    _, oid_str, new_status = parts
    oid = int(oid_str)

    if new_status not in ORDER_STATUSES:
        return

    db_update(oid, status=new_status)
    o = db_get(oid)

    if not o:
        await q.edit_message_text("⚠️  Заказ не найден.")
        return

    try:
        await q.edit_message_text(
            text=fmt_order(o, admin=True),
            reply_markup=admin_kb(oid, new_status, o.get("user_id", 0)),
        )
    except TelegramError as exc:
        logger.error("Ошибка обновления сообщения: %s", exc)

    template = STATUS_NOTIFY.get(new_status)
    uid      = o.get("user_id")
    if template and uid:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=template.replace("{id}", str(oid)),
            )
        except TelegramError as exc:
            logger.error("Ошибка уведомления клиента: %s", exc)


# ══════════════════════════════════════
#  КОМАНДЫ АДМИНА
# ══════════════════════════════════════

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_ID:
        return
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
    stat = "\n".join(
        f"  {ORDER_STATUSES.get(s, s)}: {c}"
        for s, c in sorted(counts.items())
    )
    await update.message.reply_text(
        f"📊  PATHA · заказы\n\n"
        f"Всего: {len(orders)}\n"
        f"Выручка: {revenue} сом\n\n"
        f"{stat}\n\n"
        f"Фильтр:\n"
        f"/admin new\n"
        f"/admin confirmed\n"
        f"/admin production\n"
        f"/admin ready\n\n"
        f"/order <номер>"
    )
    flt  = args[0] if args else None
    show = [o for o in orders if o.get("status") == flt] if flt else orders
    if not show:
        await update.message.reply_text(f"Нет заказов со статусом «{flt}».")
        return
    for o in reversed(show[-10:]):
        try:
            await update.message.reply_text(
                fmt_order(o, admin=True),
                reply_markup=admin_kb(o["id"], o.get("status", "new"), o.get("user_id", 0)),
            )
        except TelegramError as exc:
            logger.error("Ошибка отправки заказа #%s: %s", o["id"], exc)


async def order_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.from_user.id != ADMIN_ID:
        return
    args = context.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Использование: /order <номер>")
        return
    oid = int(args[0])
    o   = db_get(oid)
    if not o:
        await update.message.reply_text(f"⚠️  Заказ #{oid} не найден.")
        return
    await update.message.reply_text(
        fmt_order(o, admin=True),
        reply_markup=admin_kb(o["id"], o.get("status", "new"), o.get("user_id", 0)),
    )
    if o.get("photo_id"):
        await update.message.reply_photo(
            photo=o["photo_id"],
            caption=f"📸  фото · заказ #{o['id']}",
        )


# ══════════════════════════════════════
#  ЗАПУСК
# ══════════════════════════════════════

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    _cb = [CallbackQueryHandler(status_callback, pattern=r"^s:\d+:\w+$")]

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_handler),
        ],
        states={
            WELCOME:             _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, welcome_handler)],
            PRODUCT:             _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_product)],
            SIZE:                _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_size)],
            PRINT_TYPE:          _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_print_type)],
            FIGHTER_CHOICE:      _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, fighter_choice)],
            CUSTOM_FIGHTER_NAME: _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_fighter_name)],
            QUOTE_CHOICE:        _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, quote_choice)],
            CUSTOM_TEXT:         _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, custom_text)],
            PRINT_PHOTO:         _cb + [MessageHandler(filters.PHOTO | (filters.TEXT & ~filters.COMMAND), get_print_photo)],
            PRINT_TEXT:          _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, get_print_text)],
            PHONE:               _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM:             _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
            EDIT_MENU:           _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_menu_handler)],
            EDIT_SIZE:           _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_size)],
            EDIT_TEXT:           _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_text)],
            EDIT_PHONE:          _cb + [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_phone)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(status_callback, pattern=r"^s:\d+:\w+$"),
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(status_callback, pattern=r"^s:\d+:\w+$"))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("order", order_cmd))

    logger.info("🖤  PATHA бот v4.0 запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
