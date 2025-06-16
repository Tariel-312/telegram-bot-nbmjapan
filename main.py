
import os
import threading
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup
from keepalive import keep_alive

app = Flask(__name__)

# Токен должен браться из переменных окружения
TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('BOT_TOKEN') or '8102280931:AAFNx7zZOAV4QjRjNnNzB6edsgeXsLBFQss'
bot = telebot.TeleBot(TOKEN)

# Клавиатура
def create_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Мой профиль", "Помощь")
    return markup

# Обработчики
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🔹 Привет! Я бот на Replit!\n\n"
                 "Доступные команды:\n"
                 "/start - начать работу\n"
                 "/help - помощь", reply_markup=create_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if message.text == "Мой профиль":
        user = message.from_user
        response = (f"📌 Ваш профиль:\n"
                   f"ID: `{user.id}`\n"
                   f"Имя: {user.first_name}\n"
                   f"Фамилия: {user.last_name or 'не указана'}\n"
                   f"Юзернейм: @{user.username or 'не указан'}")
        bot.send_message(message.chat.id, response, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, f"🔹 Вы написали: `{message.text}`", parse_mode='Markdown')

# Вебхук
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    return "Bad Request", 400

# Запуск бота
def run_bot():
    print("🟢 Бот запускается...")
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co/webhook")
        print("🤖 Бот успешно запущен!")
    except Exception as e:
        print(f"🔴 Ошибка запуска: {e}")

# Потоки
threading.Thread(target=run_bot, daemon=True).start()
keep_alive()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
