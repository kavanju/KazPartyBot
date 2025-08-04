FROM python:3.10-slim

# Установим системные зависимости
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libsm6 libxext6 libxrender-dev \
    && apt-get clean

# Копируем файлы проекта
WORKDIR /app
COPY . /app

# Устанавливаем Python-зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Запуск бота
CMD ["python", "bot.py"]
