import os
import threading
import json
from datetime import datetime
from typing import Tuple, Optional
from flask import Flask, request
import telebot
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from keepalive import keep_alive
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

class GoogleSheetsManager:
    def __init__(self):
        """Инициализация менеджера Google Sheets."""
        self.service = None
        self._initialize_service()

    def _initialize_service(self) -> None:
        """Инициализирует подключение к Google Sheets API."""
        try:
            service_account_info = self._get_service_account_info()
            spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID')
            
            if not service_account_info or not spreadsheet_id:
                raise ValueError("Не настроены переменные окружения")

            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=creds)
            print("✅ Успешное подключение к Google Sheets")
            
        except Exception as e:
            print(f"❌ Ошибка инициализации: {str(e)}")
            self.service = None

    def get_client_info(self, telegram_id: str) -> Optional[dict]:
        """Возвращает полную информацию о клиенте по Telegram ID"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                range='Клиенты!A:I'
            ).execute()
            
            for row in result.get('values', []):
                if len(row) > 5 and row[5] == str(telegram_id):
                    return {
                        'first_name': row[0] if len(row) > 0 else None,
                        'last_name': row[1] if len(row) > 1 else None,
                        'phone': row[2] if len(row) > 2 else None,
                        'city': row[3] if len(row) > 3 else None,
                        'comments': row[4] if len(row) > 4 else None,
                        'status': row[6] if len(row) > 6 else None,
                        'last_updated': row[7] if len(row) > 7 else None,
                        'status_comment': row[8] if len(row) > 8 else None
                    }
            return None
        except Exception as e:
            print(f"Ошибка при получении информации о клиенте: {e}")
            return None
    
    def _get_service_account_info(self) -> dict:
        """Получает данные сервисного аккаунта из переменных окружения."""
        try:
            return json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
        except json.JSONDecodeError:
            print("⚠️ Неверный формат GOOGLE_SERVICE_ACCOUNT_JSON")
            return {}

    def add_client(self, first_name: str, last_name: str, phone: str, 
                  city: str, comments: str, telegram_id: str) -> Tuple[bool, str]:
        """Добавляет нового клиента в таблицу."""
        if not self.service:
            return False, "Сервис не инициализирован"

        try:
            values = [
                first_name, last_name, phone, city, 
                comments, str(telegram_id),
                "В обработке", "", ""
            ]
            
            body = {'values': [values]}
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                range='Клиенты!A:I',
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True, "Клиент успешно зарегистрирован"
            
        except HttpError as e:
            error_msg = f"Ошибка API: {e.content.decode()}"
            print(f"❌ {error_msg}")
            return False, error_msg
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            return False, f"Ошибка при добавлении: {str(e)}"

    def update_status(self, telegram_id: str, new_status: str, 
                    comment: str = "") -> Tuple[bool, str]:
        """Обновляет статус заказа."""
        if not self.service:
            return False, "Сервис не инициализирован"

        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                range='Клиенты!A:I'
            ).execute()
            
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if len(row) > 5 and row[5] == str(telegram_id):
                    range_name = f'Клиенты!G{i+1}:I{i+1}'
                    update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    body = {
                        'values': [[new_status, update_time, comment]]
                    }
                    
                    self.service.spreadsheets().values().update(
                        spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                        range=range_name,
                        valueInputOption='USER_ENTERED',
                        body=body
                    ).execute()
                    
                    return True, "Статус успешно обновлен"
            
            return False, "Клиент не найден"
            
        except Exception as e:
            print(f"❌ Ошибка обновления статуса: {str(e)}")
            return False, str(e)

    def setup_headers(self) -> Tuple[bool, str]:
        """Устанавливает заголовки таблицы."""
        headers = [
            "Имя", "Фамилия", "Телефон", "Город", 
            "Комментарии", "Telegram ID", 
            "Статус", "Дата обновления", "Комментарий статуса"
        ]
        
        try:
            body = {'values': [headers]}
            self.service.spreadsheets().values().update(
                spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                range='Клиенты!A1:I1',
                valueInputOption='RAW',
                body=body
            ).execute()
            return True, "Заголовки установлены"
        except Exception as e:
            return False, str(e)

    def get_client_status(self, telegram_id: str) -> Optional[dict]:
        """Возвращает текущий статус клиента."""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                range='Клиенты!A:I'
            ).execute()
            
            for row in result.get('values', []):
                if len(row) > 5 and row[5] == str(telegram_id):
                    return {
                        'status': row[6] if len(row) > 6 else None,
                        'last_updated': row[7] if len(row) > 7 else None,
                        'comment': row[8] if len(row) > 8 else None
                    }
            return None
        except Exception:
            return None

    def client_exists(self, telegram_id: str) -> bool:
        """Проверяет, существует ли клиент с заданным Telegram ID."""
        if not self.service:
            return False

        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=os.getenv('GOOGLE_SPREADSHEET_ID'),
                range='Клиенты!A:I'
            ).execute()
            
            for row in result.get('values', []):
                if len(row) > 5 and row[5] == str(telegram_id):
                    return True
            return False
        except Exception:
            return False

# Инициализация бота
TOKEN = os.getenv('TELEGRAM_TOKEN') or os.getenv('BOT_TOKEN') or '8102280931:AAFNx7zZOAV4QjRjNnNzB6edsgeXsLBFQss'
bot = telebot.TeleBot(TOKEN)
sheets_manager = GoogleSheetsManager()
user_states = {}

# Клавиатуры
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

# Обработчики сообщений
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
    status_info = sheets_manager.get_client_status(str(message.from_user.id))
    
    if not status_info:
        bot.send_message(
            message.chat.id,
            "❌ Ваш статус не найден. Возможно, вы еще не зарегистрированы.",
            reply_markup=create_keyboard()
        )
        return
    
    status = status_info.get('status', 'неизвестен')
    last_updated = status_info.get('last_updated', 'не указана')
    comment = status_info.get('comment', 'нет комментариев')
    
    status_descriptions = {
        "В обработке": "🔄 Ваш заказ находится в обработке",
        "Отправлен": "🚢 Ваш заказ отправлен из Японии",
        "В пути": "✈️ Ваш заказ в пути",
        "Прибыл": "✅ Ваш заказ прибыл в пункт выдачи"
    }
    
    description = status_descriptions.get(status, f"Статус: {status}")
    
    response = (
        f"📦 <b>Статус вашего заказа</b>\n\n"
        f"{description}\n\n"
        #f"📅 <b>Последнее обновление:</b> {last_updated}\n"
        #f"📝 <b>Комментарий:</b> {comment}"
    )
    
    bot.send_message(
        message.chat.id,
        response,
        parse_mode='HTML',
        reply_markup=create_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "Регистрация клиента")
def handle_registration_start(message):
    """Начинает процесс регистрации, проверяя, не зарегистрирован ли пользователь уже."""
    telegram_id = str(message.from_user.id)
    
    if sheets_manager.client_exists(telegram_id):
        bot.send_message(
            message.chat.id,
            "ℹ️ Вы уже зарегистрированы в нашей системе. "
            "Если вам нужно обновить информацию, пожалуйста, свяжитесь с нами.",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.chat.id] = {'state': 'awaiting_first_name'}
    bot.send_message(
        chat_id=message.chat.id,
        text="📝 Давайте начнем регистрацию!\n\n"
             "Пожалуйста, введите ваше имя:",
        reply_markup=create_cancel_keyboard()
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'awaiting_first_name')
def handle_first_name(message):
    if message.text.lower() == 'отмена':
        del user_states[message.chat.id]
        bot.send_message(
            message.chat.id,
            "❌ Регистрация отменена",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.chat.id] = {
        'state': 'awaiting_last_name',
        'first_name': message.text
    }
    bot.send_message(
        message.chat.id,
        "Теперь введите вашу фамилию:",
        reply_markup=create_cancel_keyboard()
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'awaiting_last_name')
def handle_last_name(message):
    if message.text.lower() == 'отмена':
        del user_states[message.chat.id]
        bot.send_message(
            message.chat.id,
            "❌ Регистрация отменена",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.chat.id]['state'] = 'awaiting_phone'
    user_states[message.chat.id]['last_name'] = message.text
    bot.send_message(
        message.chat.id,
        "Теперь введите ваш номер телефона:",
        reply_markup=create_cancel_keyboard()
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'awaiting_phone')
def handle_phone(message):
    if message.text.lower() == 'отмена':
        del user_states[message.chat.id]
        bot.send_message(
            message.chat.id,
            "❌ Регистрация отменена",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.chat.id]['state'] = 'awaiting_city'
    user_states[message.chat.id]['phone'] = message.text
    bot.send_message(
        message.chat.id,
        "Введите ваш город:",
        reply_markup=create_cancel_keyboard()
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'awaiting_city')
def handle_city(message):
    if message.text.lower() == 'отмена':
        del user_states[message.chat.id]
        bot.send_message(
            message.chat.id,
            "❌ Регистрация отменена",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.chat.id]['state'] = 'awaiting_comments'
    user_states[message.chat.id]['city'] = message.text
    bot.send_message(
        message.chat.id,
        "Введите дополнительные комментарии (если есть):",
        reply_markup=create_cancel_keyboard()
    )

@bot.message_handler(func=lambda message: user_states.get(message.chat.id, {}).get('state') == 'awaiting_comments')
def handle_comments(message):
    if message.text.lower() == 'отмена':
        del user_states[message.chat.id]
        bot.send_message(
            message.chat.id,
            "❌ Регистрация отменена",
            reply_markup=create_keyboard()
        )
        return
    
    user_states[message.chat.id]['comments'] = message.text
    
    # Завершаем регистрацию
    chat_id = message.chat.id
    user_data = user_states[chat_id]
    
    success, response = sheets_manager.add_client(
        first_name=user_data.get('first_name', ''),
        last_name=user_data.get('last_name', ''),
        phone=user_data.get('phone', ''),
        city=user_data.get('city', ''),
        comments=user_data.get('comments', ''),
        telegram_id=str(message.from_user.id)
    )
    
    if success:
        bot.send_message(
            chat_id,
            "✅ Регистрация успешно завершена!\n\n"
            f"Спасибо, {user_data['first_name']}! Теперь вы можете отслеживать статус вашего заказа.",
            reply_markup=create_keyboard()
        )
    else:
        bot.send_message(
            chat_id,
            f"❌ Произошла ошибка при регистрации: {response}",
            reply_markup=create_keyboard()
        )
    
    del user_states[chat_id]

# Вебхук и запуск бота
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_data = request.get_json()
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])
        return "OK", 200
    return "Bad Request", 400

def run_bot():
    print("🟢 Бот запускается...")
    try:
        bot.remove_webhook()
        print("🤖 Бот запущен в режиме polling!")
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"🔴 Ошибка запуска: {e}")

if __name__ == '__main__':
    keep_alive()
    run_bot()