FROM python:3.10-slim

# Установим системные зависимости
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libsm6 libxext6 libxrender-dev \
    ffmpeg \
    && apt-get clean

# Установка рабочей директории
WORKDIR /app

# Копируем все файлы проекта
COPY . /app

# Установка зависимостей
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Устанавливаем переменные среды (если нужно)
ENV PYTHONUNBUFFERED=1

# Запуск бота
CMD ["python", "bot.py"]
