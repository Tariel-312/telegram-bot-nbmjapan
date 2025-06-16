
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
        
        if not self.service_account_info or not self.spreadsheet_id:
            print("⚠️ Google Sheets не настроен. Добавьте GOOGLE_SERVICE_ACCOUNT_JSON и GOOGLE_SPREADSHEET_ID в Secrets")
            self.service = None
            return
            
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
    
    def add_client(self, first_name, last_name, phone, telegram_id):
        """Добавляет клиента в Google Sheets"""
        if not self.service:
            return False, "Google Sheets не настроен"
        
        try:
            # Подготавливаем данные для добавления
            values = [[first_name, last_name, phone, telegram_id]]
            
            body = {
                'values': values
            }
            
            # Добавляем данные в таблицу
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A:D',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return True, f"Клиент добавлен в строку {result.get('updates', {}).get('updatedRows', 0)}"
            
        except Exception as e:
            return False, f"Ошибка при добавлении в таблицу: {str(e)}"
    
    def setup_headers(self):
        """Устанавливает заголовки в таблице"""
        if not self.service:
            return False, "Google Sheets не настроен"
        
        try:
            headers = [['Имя', 'Фамилия', 'Телефон', 'Telegram ID']]
            
            body = {
                'values': headers
            }
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f'{self.sheet_name}!A1:D1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            return True, "Заголовки установлены"
            
        except Exception as e:
            return False, f"Ошибка при установке заголовков: {str(e)}"
