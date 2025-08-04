FROM python:3.10-slim

# Установка зависимостей
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Копирование кода
WORKDIR /app
COPY . /app

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Запуск бота
CMD ["python", "bot.py"]
