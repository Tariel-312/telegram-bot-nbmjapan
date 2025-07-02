from google_sheets import GoogleSheetsManager

sheets = GoogleSheetsManager()
success, message = sheets.add_client(
    "Тест", "Тестов", "+79991112233", "Москва", "Коммент", "123456"
)
print(f"Успешно: {success}, Сообщение: {message}")