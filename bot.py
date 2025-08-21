import os
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ID администратора (замени на свой)
ADMIN_ID = 535869416

# Конфигурация
config = {
    "USD_UAH": 49,  # курс по умолчанию
    "devices": {
        "IPL A-Tone": 27000,
        "Finexel CO2": 30000,
        "10THERMA": 25000
    }
}

# Словарь для хранения данных пользователя
user_data = {}

# Главное меню
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📊 Розрахувати окупність апарату"),
        types.KeyboardButton("👨‍💼 Звʼязок з менеджером")
    )
    return markup

# Старт
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привіт! Обери дію:", reply_markup=main_menu())

# Контакт менеджера
@bot.message_handler(func=lambda m: m.text == "👨‍💼 Звʼязок з менеджером")
def contact_manager(message):
    bot.send_message(message.chat.id, "Для звʼязку з менеджером пишіть сюди: @alex_digital_beauty")

# Выбор аппарата
@bot.message_handler(func=lambda m: m.text == "📊 Розрахувати окупність апарату")
def choose_device(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for dev in config["devices"].keys():
        markup.add(dev)
    markup.add("⬅️ Повернутись в меню")
    bot.send_message(message.chat.id, "Оберіть апарат:", reply_markup=markup)

# Вопросы по шагам
def ask_question_step(chat_id, step):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if step == 1:
        default_price = f"{config['devices'][user_data[chat_id]['device']]}€"
        markup.add(default_price, "Ввести іншу вартість", "⬅️ Повернутись в меню")
        bot.send_message(chat_id, "Вартість апарату:", reply_markup=markup)
    elif step == 2:
        markup.add("200 процедур", "Ввести іншу кількість", "⬅️ Повернутись в меню")
        bot.send_message(chat_id, "Кількість процедур на місяць:", reply_markup=markup)
    elif step == 3:
        markup.add("3500 грн", "Ввести іншу вартість", "⬅️ Повернутись в меню")
        bot.send_message(chat_id, "Вартість процедури:", reply_markup=markup)
    elif step == 4:
        markup.add("15% від вартості послуги", "Введіть інший %", "⬅️ Повернутись в меню")
        bot.send_message(chat_id, "Заробітня плата фахівця:", reply_markup=markup)
    user_data[chat_id]['step'] = step

# Обработка выбора аппарата
@bot.message_handler(func=lambda m: m.text in config["devices"].keys())
def device_selected(message):
    chat_id = message.chat.id
    user_data[chat_id] = {"device": message.text}
    ask_question_step(chat_id, 1)

# Универсальный обработчик всех сообщений
@bot.message_handler(func=lambda m: True)
def handle_answers(message):
    chat_id = message.chat.id

    # 🔹 Админ-команды
    if message.text.startswith("/"):
        if chat_id != ADMIN_ID:
            bot.send_message(chat_id, "У вас немає прав ❌")
            return
        cmd = message.text.split()
        if cmd[0] == "/set_usd" and len(cmd) == 2:
            try:
                config["USD_UAH"] = float(cmd[1])
                bot.send_message(chat_id, f"✅ Курс змінено: {config['USD_UAH']} грн/$")
            except:
                bot.send_message(chat_id, "❌ Приклад: /set_usd 50")
        elif cmd[0] == "/set_price" and len(cmd) == 3:
            name, price = cmd[1], cmd[2]
            if name in config["devices"]:
                config["devices"][name] = float(price)
                bot.send_message(chat_id, f"✅ Ціна {name} змінена на {price}€")
            else:
                bot.send_message(chat_id, "❌ Немає такого апарату")
        elif cmd[0] == "/add_device" and len(cmd) == 3:
            name, price = cmd[1], float(cmd[2])
            config["devices"][name] = price
            bot.send_message(chat_id, f"✅ Додано апарат {name} ({price}€)")
        elif cmd[0] == "/remove_device" and len(cmd) == 2:
            name = cmd[1]
            if name in config["devices"]:
                del config["devices"][name]
                bot.send_message(chat_id, f"✅ Апарат {name} видалено")
            else:
                bot.send_message(chat_id, "❌ Немає такого апарату")
        else:
            bot.send_message(chat_id, "❌ Невідома команда")
        return

    # Кнопка "Вернуться в меню"
    if message.text == "⬅️ Повернутись в меню":
        bot.send_message(chat_id, "Повертаємось в меню:", reply_markup=main_menu())
        user_data.pop(chat_id, None)
        return

    if chat_id not in user_data:
        return

    step = user_data[chat_id].get('step', 0)

    # Шаги
    if step == 1:
        try:
            val = float(message.text.replace("€", "").replace(" ", ""))
            user_data[chat_id]['cost'] = val
            ask_question_step(chat_id, 2)
        except:
            bot.send_message(chat_id, "Помилка! Введіть число (€):")
    elif step == 2:
        try:
            val = int(message.text.replace("процедур", "").strip())
            user_data[chat_id]['count'] = val
            ask_question_step(chat_id, 3)
        except:
            bot.send_message(chat_id, "Помилка! Введіть число процедур:")
    elif step == 3:
        try:
            val = float(message.text.replace("грн","").replace(" ",""))
            user_data[chat_id]['price'] = val
            ask_question_step(chat_id, 4)
        except:
            bot.send_message(chat_id, "Помилка! Введіть число (грн):")
    elif step == 4:
        try:
            val = float(message.text.replace("%",""))
            user_data[chat_id]['salary_percent'] = val
        except:
            bot.send_message(chat_id, "Помилка! Введіть число %:")
            return

        # 🔹 Расчет окупаемости
        cost_uah = user_data[chat_id]['cost'] * config["USD_UAH"]
        net_profit = (user_data[chat_id]['price'] * user_data[chat_id]['count']) - \
                     (user_data[chat_id]['price'] * user_data[chat_id]['salary_percent']/100 * user_data[chat_id]['count'])
        months = round(cost_uah / net_profit, 1)
        salary_per_procedure = user_data[chat_id]['price'] * user_data[chat_id]['salary_percent']/100

        text = f"""
{user_data[chat_id]['device']}
Вартість апарату: {user_data[chat_id]['cost']}€
Курс: {config['USD_UAH']} грн/$
Кількість процедур: {user_data[chat_id]['count']}
Вартість процедури: {user_data[chat_id]['price']} грн
ЗП фахівця: {salary_per_procedure} грн
Окупність: {months} місяців

Для звʼязку з менеджером: @alex_digital_beauty
"""
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("👨‍💼 Звʼязок з менеджером", "⬅️ Повернутись в меню")
        bot.send_message(chat_id, text, reply_markup=markup)
        user_data.pop(chat_id, None)

# Вебхук для Telegram
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

# Проверка на Render
@app.route("/")
def index():
    return "Бот працює через webhook!", 200

if __name__ == "__main__":
    # Render hostname
    HOSTNAME = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if not HOSTNAME:
        raise Exception("RENDER_EXTERNAL_HOSTNAME не задано")
    bot.remove_webhook()
    bot.set_webhook(url=f"https://{HOSTNAME}/{TOKEN}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

