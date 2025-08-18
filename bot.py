import os
import re
import math
import telebot
from telebot import types
from flask import Flask, request, jsonify

# =======================
# 🔧 НАСТРОЙКИ
# =======================
# Токен уже подставлен по твоей просьбе
TOKEN = "8225106462:AAF1lwaxNmFT3H9jtxATDDgF8V-krfUa3zI"
FX_EUR_UAH = 49.0  # курс €→₴ по ТЗ
MANAGER_HANDLE = "@alex_digital_beauty"

# =======================
# ♻️ ХРАНИЛИЩЕ СОСТОЯНИЙ
# =======================
USER_STATE = {}  # user_id -> dict

def reset_state(user_id: int):
    USER_STATE[user_id] = {
        "device": None,
        "cost_eur": None,
        "procedures_per_month": None,
        "price_uah": None,
        "salary_percent": None,
    }

def get_state(user_id: int):
    if user_id not in USER_STATE:
        reset_state(user_id)
    return USER_STATE[user_id]

def parse_number(text: str) -> float | None:
    """Парсим числа: '27 000€', '3500 грн', '2,5' -> float"""
    try:
        cleaned = re.sub(r"[^\d,.\-]", "", text).replace(",", ".")
        if cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "", cleaned.count(".") - 1)
        return float(cleaned)
    except Exception:
        return None

def round1(x: float) -> float:
    return math.floor(x * 10 + 0.5) / 10.0

# =======================
# 🎛 КЛАВИАТУРЫ
# =======================
def main_menu_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🧮 Розрахувати окупність апарату")
    kb.row(f"🗣️ Звʼязок з менеджером ({MANAGER_HANDLE})")
    return kb

def back_or_manager_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton(text="✉️ Звʼязок з менеджером", url=f"https://t.me/{MANAGER_HANDLE.removeprefix('@')}"))
    ikb.add(types.InlineKeyboardButton(text="⬅️ Повернутись в меню", callback_data="back_to_menu"))
    return ikb

def devices_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("IPL A-Tone", callback_data="dev__IPL A-Tone"))
    ikb.add(types.InlineKeyboardButton("Finexel CO2", callback_data="dev__Finexel CO2"))
    ikb.add(types.InlineKeyboardButton("10THERMA", callback_data="dev__10THERMA"))
    ikb.add(types.InlineKeyboardButton("⬅️ Назад у меню", callback_data="back_to_menu"))
    return ikb

def q1_cost_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("27000€", callback_data="cost__27000"))
    ikb.add(types.InlineKeyboardButton("✍️ Ввести іншу вартість", callback_data="cost__other"))
    return ikb

def q2_qty_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("200 процедур", callback_data="qty__200"))
    ikb.add(types.InlineKeyboardButton("✍️ Ввести іншу кількість", callback_data="qty__other"))
    return ikb

def q3_price_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("3500 грн", callback_data="price__3500"))
    ikb.add(types.InlineKeyboardButton("✍️ Ввести іншу вартість", callback_data="price__other"))
    return ikb

def q4_salary_kb():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(types.InlineKeyboardButton("15% від вартості послуги", callback_data="sal__15"))
    ikb.add(types.InlineKeyboardButton("✍️ Введіть інший %", callback_data="sal__other"))
    return ikb

# =======================
# 🚀 ИНИЦИАЛИЗАЦИЯ
# =======================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# =======================
# 📲 ХЭНДЛЕРЫ
# =======================
@bot.message_handler(commands=["start", "menu"])
def cmd_start(message: types.Message):
    reset_state(message.from_user.id)
    text = (
        "👋 Привіт! Я бот для розрахунку окупності обладнання.\n\n"
        "Оберіть дію нижче:"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu_kb())

@bot.message_handler(func=lambda m: m.text and "Звʼязок з менеджером" in m.text)
def contact_manager(message: types.Message):
    bot.send_message(
        message.chat.id,
        f"Для звʼязку з менеджером пишіть сюди: {MANAGER_HANDLE}",
        reply_markup=back_or_manager_kb()
    )

@bot.message_handler(func=lambda m: m.text == "🧮 Розрахувати окупність апарату")
def start_calc(message: types.Message):
    st = get_state(message.from_user.id)
    st["device"] = None
    bot.send_message(
        message.chat.id,
        "🔧 <b>Оберіть апарат</b>",
        reply_markup=types.ReplyKeyboardRemove()
    )
    bot.send_message(message.chat.id, "Доступні моделі:", reply_markup=devices_kb())

@bot.callback_query_handler(func=lambda c: c.data == "back_to_menu")
def cb_back_to_menu(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, "Повертаюсь до головного меню…", reply_markup=main_menu_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("dev__"))
def cb_choose_device(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    device = call.data.split("__", 1)[1]
    st = get_state(call.from_user.id)
    st["device"] = device

    if device != "IPL A-Tone":
        bot.send_message(
            call.message.chat.id,
            f"ℹ️ Поки що детальний майстер-розрахунок налаштований для <b>IPL A-Tone</b>.\n"
            f"Запущу розрахунок у цьому ж форматі для <b>{device}</b>."
        )

    bot.send_message(call.message.chat.id, "💶 <b>Вартість апарату</b>", reply_markup=q1_cost_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("cost__"))
def cb_q1_cost(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    st = get_state(call.from_user.id)
    _, val = call.data.split("__", 1)
    if val == "other":
        msg = bot.send_message(call.message.chat.id, "Введіть вартість апарату в € (наприклад: 27000):")
        bot.register_next_step_handler(msg, handle_cost_custom)
    else:
        st["cost_eur"] = float(val)
        ask_q2(call.message)

def handle_cost_custom(message: types.Message):
    st = get_state(message.from_user.id)
    num = parse_number(message.text)
    if num is None or num <= 0:
        msg = bot.send_message(message.chat.id, "Некоректне число. Спробуйте ще раз (тільки число в €):")
        bot.register_next_step_handler(msg, handle_cost_custom)
        return
    st["cost_eur"] = float(num)
    ask_q2(message)

def ask_q2(msg_or_message):
    chat_id = msg_or_message.chat.id
    bot.send_message(chat_id, "📈 <b>Кількість процедур на місяць</b>", reply_markup=q2_qty_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("qty__"))
def cb_q2_qty(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    st = get_state(call.from_user.id)
    _, val = call.data.split("__", 1)
    if val == "other":
        msg = bot.send_message(call.message.chat.id, "Введіть кількість процедур на місяць (наприклад: 200):")
        bot.register_next_step_handler(msg, handle_qty_custom)
    else:
        st["procedures_per_month"] = int(val)
        ask_q3(call.message)

def handle_qty_custom(message: types.Message):
    st = get_state(message.from_user.id)
    num = parse_number(message.text)
    if num is None or num <= 0:
        msg = bot.send_message(message.chat.id, "Некоректне число. Спробуйте ще раз (тільки ціле число):")
        bot.register_next_step_handler(msg, handle_qty_custom)
        return
    st["procedures_per_month"] = int(num)
    ask_q3(message)

def ask_q3(msg_or_message):
    chat_id = msg_or_message.chat.id
    bot.send_message(chat_id, "💵 <b>Вартість процедури</b>", reply_markup=q3_price_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("price__"))
def cb_q3_price(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    st = get_state(call.from_user.id)
    _, val = call.data.split("__", 1)
    if val == "other":
        msg = bot.send_message(call.message.chat.id, "Введіть вартість однієї процедури в грн (наприклад: 3500):")
        bot.register_next_step_handler(msg, handle_price_custom)
    else:
        st["price_uah"] = float(val)
        ask_q4(call.message)

def handle_price_custom(message: types.Message):
    st = get_state(message.from_user.id)
    num = parse_number(message.text)
    if num is None or num <= 0:
        msg = bot.send_message(message.chat.id, "Некоректне число. Спробуйте ще раз (тільки число в грн):")
        bot.register_next_step_handler(msg, handle_price_custom)
        return
    st["price_uah"] = float(num)
    ask_q4(message)

def ask_q4(msg_or_message):
    chat_id = msg_or_message.chat.id
    bot.send_message(chat_id, "👩‍⚕️ <b>Заробітня плата фахівця</b>", reply_markup=q4_salary_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("sal__"))
def cb_q4_salary(call: types.CallbackQuery):
    bot.answer_callback_query(call.id)
    st = get_state(call.from_user.id)
    _, val = call.data.split("__", 1)
    if val == "other":
        msg = bot.send_message(call.message.chat.id, "Введіть % від вартості послуги (наприклад: 15):")
        bot.register_next_step_handler(msg, handle_salary_custom)
    else:
        st["salary_percent"] = float(val)
        finish_and_show(call.message)

def handle_salary_custom(message: types.Message):
    st = get_state(message.from_user.id)
    num = parse_number(message.text)
    if num is None or num < 0 or num >= 100:
        msg = bot.send_message(message.chat.id, "Некоректний %. Введіть число від 0 до 99:")
        bot.register_next_step_handler(msg, handle_salary_custom)
        return
    st["salary_percent"] = float(num)
    finish_and_show(message)

# =======================
# 🧮 РАСЧЁТ И ВЫВОД
# =======================
def finish_and_show(message: types.Message):
    st = get_state(message.from_user.id)
    device = st["device"] or "Невідомий апарат"
    cost_eur = st["cost_eur"]
    qty = st["procedures_per_month"]
    price = st["price_uah"]
    percent = st["salary_percent"]

    if None in (cost_eur, qty, price, percent):
        bot.send_message(message.chat.id, "Дані неповні. Спробуйте почати спочатку: /start")
        return

    total_cost_uah = cost_eur * FX_EUR_UAH
    specialist_per_proc = price * (percent / 100.0)
    net_per_month = (price - specialist_per_proc) * qty
    months = total_cost_uah / net_per_month if net_per_month > 0 else float("inf")
    months_rounded = round1(months)

    result_text = (
        f"📊 <b>Результат розрахунку окупності</b>\n\n"
        f"• Апарат: <b>{device}</b>\n"
        f"• Вартість апарату: <b>{int(cost_eur):,}€</b> × курс {int(FX_EUR_UAH)} = <b>{int(total_cost_uah):,} грн</b>\n"
        f"• Кількість процедур в місяць: <b>{qty}</b>\n"
        f"• Вартість процедури: <b>{int(price):,} грн</b>\n"
        f"• Заробітня плата фахівця: <b>{percent:.0f}%</b> "
        f"(з процедури: <b>{int(round(specialist_per_proc)):,} грн</b>)\n\n"
        f"• 🟢 Окупність апарату: <b>{months_rounded} місяця</b>\n\n"
        f"Для звʼязку з менеджером пишіть сюди {MANAGER_HANDLE}"
    ).replace(",", " ")

    bot.send_message(message.chat.id, result_text, reply_markup=back_or_manager_kb())

# =======================
# 🌐 ВЕБХУКИ ДЛЯ RENDER
# =======================
app = Flask(__name__)

@app.route("/", methods=["GET"])
def health():
    return jsonify(ok=True), 200

@app.route(f"/{TOKEN}", methods=["POST"])
def tg_webhook():
    try:
        update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
        bot.process_new_updates([update])
    except Exception as e:
        print("Webhook error:", e)
    return "ok", 200

def setup_webhook():
    try:
        base_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("WEBHOOK_URL")
        if base_url:
            wh_url = f"{base_url.rstrip('/')}/{TOKEN}"
            bot.remove_webhook()
            bot.set_webhook(url=wh_url, max_connections=20, allowed_updates=["message", "callback_query"])
            print("Webhook set:", wh_url)
        else:
            print("⚠️ Не задан RENDER_EXTERNAL_URL/WEBHOOK_URL — локально запускайте polling.")
    except Exception as e:
        print("Webhook setup failed:", e)

# =======================
# ▶️ ТОЧКИ ВХОДА
# =======================
if __name__ == "__main__":
    # Локально — polling
    print("Running in polling mode (local dev)…")
    bot.infinity_polling(skip_pending=True, timeout=60)
else:
    # На Render — вебхук
    setup_webhook()
