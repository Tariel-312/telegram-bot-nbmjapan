
import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

class GoogleSheetsManager:
    def __init__(self):
        # Получаем данные сервисного аккаунта из переменных окружения
        self.service_account_info = json.loads(os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
        self.spreadsheet_id = os.getenv('GOOGLE_SPREADSHEET_ID', '')
        self.sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Клиенты')
        
        if not self.service_account_info:
            print("⚠️ GOOGLE_SERVICE_ACCOUNT_JSON не найден в переменных окружения")
            self.service = None
            return
        
        if not self.spreadsheet_id:
            print("⚠️ GOOGLE_SPREADSHEET_ID не найден в переменных окружения")
            self.service = None
            return
        
        print(f"📊 Подключаемся к таблице: {self.spreadsheet_id}")
        print(f"📄 Лист: {self.sheet_name}")
            
        try:
            credentials = Credentials.from_service_account_info(
                self.service_account_info,
                scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            self.service = build('sheets', 'v4', credentials=credentials)
            print("✅ Google Sheets подключен успешно")
        except Exception as e:
            print(f"❌ Ошибка подключения к Google Sheets: {e}")
            self.service = None
    
    def add_client(self, first_name, last_name, phone, city, comments, telegram_id):
        """Добавляет клиента в Google Sheets"""
        if not self.service:
            return False, "Google Sheets не настроен"
        
        try:
            print(f"📝 Добавляем клиента: {first_name} {last_name}, {phone}, {city}")
            
            # Подготавливаем данные для добавления
            values = [[first_name, last_name, phone, city, comments, telegram_id]]
            
            body = {
                'values': values
            }
            
            # Добавляем данные в таблицу
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:F',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            updated_rows = result.get('updates', {}).get('updatedRows', 0)
            print(f"✅ Клиент успешно добавлен. Обновлено строк: {updated_rows}")
            return True, "Добро пожаловать в команду NBM Japan! Мы рады видеть вас среди наших клиентов! 🎉"
            
        except Exception as e:
            print(f"❌ Ошибка при добавлении в Google Sheets: {str(e)}")
            return False, f"Ошибка при добавлении в таблицу: {str(e)}"
    
    def setup_headers(self):
        """Устанавливает заголовки в таблице"""
        if not self.service:
            return False, "Google Sheets не настроен"
        
        try:
            headers = [['Имя', 'Фамилия', 'Телефон', 'Город/Село', 'Комментарии', 'Telegram ID']]
            
            body = {
                'values': headers
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1:F1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True, "Заголовки установлены"
            
        except Exception as e:
            return False, f"Ошибка при установке заголовков: {str(e)}"
