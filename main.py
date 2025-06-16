
import os
import telebot
from flask import Flask, request
import threading
import time
import requests
from telebot import types

# Получаем токен из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    print("Ошибка: BOT_TOKEN не найден в переменных окружения!")
    exit(1)

# Инициализация бота и Flask приложения
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# URL для вебхука (будет получен автоматически)
REPL_URL = f"https://{os.getenv('REPL_SLUG', 'telegram-bot')}.{os.getenv('REPL_OWNER', 'user')}.repl.co"

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Создаем клавиатуру с кнопкой "Мой профиль"
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    profile_button = types.KeyboardButton("Мой профиль")
    markup.add(profile_button)
    
    welcome_text = f"Привет, {message.from_user.first_name}! 👋\n\n" \
                   "Я эхо-бот. Отправь мне любое сообщение, и я повторю его.\n" \
                   "Также ты можешь нажать кнопку 'Мой профиль' для получения информации о себе."
    
    bot.reply_to(message, welcome_text, reply_markup=markup)

# Обработчик кнопки "Мой профиль"
@bot.message_handler(func=lambda message: message.text == "Мой профиль")
def show_profile(message):
    user = message.from_user
    profile_info = f"👤 Информация о профиле:\n\n" \
                   f"🆔 ID: {user.id}\n" \
                   f"👤 Имя: {user.first_name or 'Не указано'}\n" \
                   f"👥 Фамилия: {user.last_name or 'Не указана'}\n" \
                   f"📝 Username: @{user.username or 'Не указан'}\n" \
                   f"🌐 Язык: {user.language_code or 'Не указан'}\n" \
                   f"🤖 Бот: {'Да' if user.is_bot else 'Нет'}"
    
    bot.reply_to(message, profile_info)

# Обработчик всех остальных текстовых сообщений (эхо)
@bot.message_handler(func=lambda message: True, content_types=['text'])
def echo_message(message):
    echo_text = f"Эхо: {message.text}"
    bot.reply_to(message, echo_text)

# Flask маршрут для обработки вебхуков
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        print(f"Ошибка обработки вебхука: {e}")
        return '', 500

# Keep-alive маршрут
@app.route('/')
def index():
    return "✅ Telegram Bot @nbmjapan_bot is running! 🤖"

@app.route('/health')
def health():
    return {'status': 'ok', 'bot': 'nbmjapan_bot'}, 200

# Функция для установки вебхука
def set_webhook():
    try:
        # Удаляем старый вебхук
        bot.remove_webhook()
        time.sleep(2)
        
        # Устанавливаем новый вебхук
        webhook_url = f"{REPL_URL}/{BOT_TOKEN}"
        success = bot.set_webhook(url=webhook_url)
        
        if success:
            print(f"✅ Вебхук успешно установлен: {webhook_url}")
            # Проверяем информацию о вебхуке
            webhook_info = bot.get_webhook_info()
            print(f"📡 URL вебхука: {webhook_info.url}")
            print(f"🔄 Ожидающих обновлений: {webhook_info.pending_update_count}")
        else:
            print("❌ Ошибка при установке вебхука")
        
        return success
    except Exception as e:
        print(f"❌ Ошибка при установке вебхука: {e}")
        return False

# Функция keep-alive для поддержания работы сервера
def keep_alive():
    def run_server():
        app.run(host='0.0.0.0', port=5000, debug=False)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Ожидаем запуска сервера
    time.sleep(5)
    
    # Устанавливаем вебхук
    webhook_set = set_webhook()
    
    if not webhook_set:
        print("⚠️ Повторная попытка установки вебхука через 10 секунд...")
        time.sleep(10)
        set_webhook()

# Основная функция
def main():
    print("🚀 Запуск Telegram бота @nbmjapan_bot...")
    print(f"🔗 Repl URL: {REPL_URL}")
    
    # Запускаем keep-alive сервер
    keep_alive()
    
    print("✅ Бот запущен и готов к работе!")
    print("📱 Попробуйте отправить команду /start боту")
    
    # Бесконечный цикл для поддержания работы
    try:
        while True:
            time.sleep(30)
            # Пинг для поддержания активности
            try:
                response = requests.get(f"{REPL_URL}/health", timeout=10)
                if response.status_code == 200:
                    print("💚 Keep-alive ping успешен")
            except Exception as e:
                print(f"⚠️ Keep-alive ping failed: {e}")
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
        bot.remove_webhook()

if __name__ == "__main__":
    main()
