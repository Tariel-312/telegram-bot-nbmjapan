import os
import threading
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from keepalive import keep_alive
from google_sheets import GoogleSheetsManager
from datetime import datetime

app = Flask(__name__)

# Токен должен браться из переменных окружения
TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('BOT_TOKEN') or '8102280931:AAFNx7zZOAV4QjRjNnNzB6edsgeXsLBFQss'
bot = telebot.TeleBot(TOKEN)

# Инициализируем Google Sheets Manager
sheets_manager = GoogleSheetsManager()

# Хранение состояний пользователей для регистрации
user_states = {}

# Клавиатура
def create_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False, row_width=2)
    buttons = [
        KeyboardButton("Регистрация клиента"),
        KeyboardButton("Мой профиль"),
        KeyboardButton("Проверить статус"),
        KeyboardButton("Связаться с нами"),
        KeyboardButton("Помощь")
    ]
    markup.add(*buttons)
    return markup

def create_cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Отмена")
    return markup

# Обработчики
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.send_message(
        chat_id=message.chat.id,
        text="🚛 Добро пожаловать в NBM Japan!\n"
             "🌏 Ваша надежная карго компания для доставки из Японии\n\n"
             "📦 Мы доставляем товары быстро и безопасно\n"
             "🎌 Прямые поставки из Японии\n\n"
             "Выберите действие:",
        reply_markup=create_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "Проверить статус")
def handle_status_check(message):
    """Обработчик для проверки статуса заказа"""
    # Проверяем, зарегистрирован ли пользователь
    if not sheets_manager.client_exists(str(message.from_user.id)):
        bot.send_message(message.chat.id, "❌ Вы еще не зарегистрированы.", reply_markup=create_keyboard())
        return
    
    status_info = sheets_manager.get_client_status(str(message.from_user.id))
    
    if not status_info:
        bot.send_message(message.chat.id, "❌ Информация о статусе недоступна.")
        return
    
    status = status_info.get('status', 'неизвестен')
    last_updated = status_info.get('last_updated', 'не указана')
    comment = status_info.get('comment', 'нет комментариев')
    
    # Формируем понятное описание статуса
    status_descriptions = {
        "В обработке": "🔄 Ваш заказ находится в обработке",
        "Отправлен": "🚢 Ваш заказ отправлен из Японии",
        "В пути": "✈️ Ваш заказ в пути",
        "Прибыл": "✅ Ваш заказ прибыл в пункт выдачи",
        "Готов к выдаче": "📦 Заказ готов к выдаче",
        "Выдан": "🎉 Заказ получен"
    }
    
    description = status_descriptions.get(status, f"Статус: {status}")
    
    # Формируем сообщение
    response = (
        f"📦 Статус вашего заказа:\n\n"
        f"{description}\n\n"
        #f"📅 Последнее обновление: {last_updated}\n"
        #f"📝 Комментарий: {comment}\n\n"
        f"Для уточнения деталей нажмите «Связаться с нами»"
    )
    
    bot.send_message(message.chat.id, response, reply_markup=create_keyboard())

@bot.message_handler(func=lambda message: message.text == "Регистрация клиента")
def start_registration(message):
    """Начинает процесс регистрации с проверкой существующего пользователя"""
    user_id = str(message.from_user.id)
    
    # Проверяем, не зарегистрирован ли пользователь уже
    if sheets_manager.client_exists(user_id):
        bot.send_message(
            message.chat.id,
            "ℹ️ Вы уже зарегистрированы в нашей системе. "
            "Если вам нужно обновить информацию, пожалуйста, свяжитесь с нами.",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.from_user.id] = {'step': 'first_name'}
    bot.send_message(
        message.chat.id, 
        "📝 Начинаем регистрацию!\n\nВведите ваше имя:", 
        reply_markup=create_cancel_keyboard()
    )

@bot.message_handler(commands=['setup_sheets'])
def setup_sheets_headers(message):
    """Команда для настройки заголовков в Google Sheets"""
    success, msg = sheets_manager.setup_headers()
    if success:
        bot.send_message(message.chat.id, f"✅ {msg}")
    else:
        bot.send_message(message.chat.id, f"❌ {msg}")

@bot.message_handler(commands=['check_sheets'])
def check_sheets_config(message):
    """Команда для проверки настроек Google Sheets"""
    config_status = []
    
    # Проверяем переменные окружения
    if os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'):
        config_status.append("✅ GOOGLE_SERVICE_ACCOUNT_JSON настроен")
    else:
        config_status.append("❌ GOOGLE_SERVICE_ACCOUNT_JSON не найден")
    
    if os.getenv('GOOGLE_SPREADSHEET_ID'):
        config_status.append(f"✅ GOOGLE_SPREADSHEET_ID: {os.getenv('GOOGLE_SPREADSHEET_ID')}")
    else:
        config_status.append("❌ GOOGLE_SPREADSHEET_ID не найден")
    
    # Проверяем подключение
    if sheets_manager.service:
        config_status.append("✅ Google Sheets API подключен")
    else:
        config_status.append("❌ Google Sheets API не подключен")
    
    response = "🔍 Проверка настроек Google Sheets:\n\n" + "\n".join(config_status)
    bot.send_message(message.chat.id, response)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text
    
    # Проверяем, находится ли пользователь в процессе регистрации
    if user_id in user_states:
        if text == "Отмена":
            del user_states[user_id]
            bot.send_message(message.chat.id, "❌ Регистрация отменена", reply_markup=create_keyboard())
            return
        
        state = user_states[user_id]
        
        if state['step'] == 'first_name':
            state['first_name'] = text
            state['step'] = 'last_name'
            bot.send_message(message.chat.id, "Введите вашу фамилию:", reply_markup=create_cancel_keyboard())
            
        elif state['step'] == 'last_name':
            state['last_name'] = text
            state['step'] = 'phone'
            bot.send_message(
                message.chat.id, 
                "Введите ваш номер телефона (например: +996 000 000 000):", 
                reply_markup=create_cancel_keyboard()
            )
            
        elif state['step'] == 'phone':
            state['phone'] = text
            state['step'] = 'city'
            bot.send_message(message.chat.id, "Введите ваш город:", reply_markup=create_cancel_keyboard())
            
        elif state['step'] == 'city':
            state['city'] = text
            state['step'] = 'comments'
            bot.send_message(
                message.chat.id, 
                "Введите комментарии (пожелания, особые требования к доставке):", 
                reply_markup=create_cancel_keyboard()
            )
            
        elif state['step'] == 'comments':
            state['comments'] = text
            
            # Завершаем регистрацию и добавляем в Google Sheets
            success, msg = sheets_manager.add_client(
                state['first_name'],
                state['last_name'], 
                state['phone'],
                state['city'],
                state['comments'],
                str(user_id)
            )
            
            if success:
                bot.send_message(
                    message.chat.id, 
                    f"✅ Регистрация в NBM Japan завершена!\n\n"
                    f"📋 Ваши данные:\n"
                    f"Имя: {state['first_name']}\n"
                    f"Фамилия: {state['last_name']}\n"
                    f"Телефон: {state['phone']}\n"
                    f"Город: {state['city']}\n"
                    f"Комментарии: {state['comments']}\n\n"
                    f"🗃️ {msg}\n\n"
                    f"📞 Для оформления заказа свяжитесь с нами через кнопку 'Связаться с нами'",
                    reply_markup=create_keyboard())
            else:
                bot.send_message(
                    message.chat.id, 
                    f"✅ Регистрация завершена!\n\n"
                    f"📋 Ваши данные:\n"
                    f"Имя: {state['first_name']}\n"
                    f"Фамилия: {state['last_name']}\n"
                    f"Телефон: {state['phone']}\n"
                    f"Город: {state['city']}\n"
                    f"Комментарии: {state['comments']}\n\n"
                    f"⚠️ Ошибка записи в таблицу: {msg}\n\n"
                    f"📞 Для оформления заказа свяжитесь с нами через кнопку 'Связаться с нами'",
                    reply_markup=create_keyboard())
            
            # Удаляем состояние пользователя
            del user_states[user_id]
        return
    
    # Обычные команды
    if text == "Мой профиль":
        user = message.from_user
        response = (
            f"👤 Ваш профиль в NBM Japan:\n"
            f"ID: {user.id}\n"
            f"Имя: {user.first_name}\n"
            f"Фамилия: {user.last_name or 'не указана'}\n"
            f"Юзернейм: @{user.username or 'не указан'}\n\n"
        )
        
        # Добавляем информацию из Google Sheets, если пользователь зарегистрирован
        if sheets_manager.client_exists(str(user.id)):
            client_info = sheets_manager.get_client_status(str(user.id))
            response += (
                f"📋 Статус вашего заказа:\n"
                #f"Телефон: {client_info.get('phone', 'не указан')}\n"
                #f"Город: {client_info.get('city', 'не указан')}\n"
                f"📦: {client_info.get('status', 'неизвестен')}"
            )
        else:
            response += "ℹ️ Вы еще не зарегистрированы в системе."
            
        bot.send_message(message.chat.id, response, reply_markup=create_keyboard())
        
    elif text == "Связаться с нами":
        bot.send_message(
            message.chat.id, 
            "📞 Контакты NBM Japan:\n\n"
            "📱 WhatsApp: +81 90-9542-7552\n"
            "📱 WhatsApp: +996 778 56 27 36\n"
            "📱 Telegram: @aitakma\n"
            "📧 Email: info@nbmjapan.com\n\n"
            "🕐 Время работы: 9:00 - 18:00 (ПН-ПТ)\n\n"
            "💬 Напишите нам для:\n"
            "• Оформления заказа\n"
            "• Отслеживания посылки\n"
            "• Консультации по товарам",
            reply_markup=create_keyboard()
        )
        
    elif text == "Помощь":
        bot.send_message(
            message.chat.id, 
            "ℹ️ NBM Japan - карго доставка из Японии\n\n"
            "🔹 Регистрация клиента - зарегистрироваться в системе\n"
            "🔹 Мой профиль - информация о вашем аккаунте\n"
            "🔹 Проверить статус - узнать статус вашего заказа\n"
            "🔹 Связаться с нами - контакты для заказов\n\n"
            "📦 Услуги:\n"
            "• Покупка товаров в японских интернет-магазинах\n"
            "• Консолидация посылок\n"
            "• Быстрая доставка в Кыргызстан\n"
            "• Страхование грузов",
            reply_markup=create_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id, 
            "🤖 Используйте кнопки меню для навигации", 
            reply_markup=create_keyboard()
        )

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
        # Для разработки используем polling вместо webhook
        print("🤖 Бот запущен в режиме polling!")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"🔴 Ошибка запуска: {e}")

if __name__ == '__main__':
    # Запускаем keep-alive сервер в отдельном потоке
    keep_alive()
    # Запускаем бота
    run_bot()