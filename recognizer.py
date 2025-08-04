import pytesseract
from PIL import Image
import datetime

def check_kaspi_receipt(image_path, kaspi_name="Абдильманов Темирлан Серыкович", min_amount=400):
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image, lang="rus+eng")

        # Поиск имени
        if kaspi_name.lower() not in text.lower():
            return False, "Имя не найдено в чеке"

        # Поиск суммы
        for line in text.splitlines():
            if "₸" in line or "KZT" in line:
                try:
                    amount = int(''.join(filter(str.isdigit, line)))
                    if amount < min_amount:
                        return False, f"Сумма {amount}₸ меньше необходимой"
                except:
                    continue

        # Поиск даты
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        if today not in text:
            return False, f"Дата {today} не найдена в чеке"

        return True, "Чек подтверждён"
    except Exception as e:
        return False, f"Ошибка при проверке: {str(e)}"
