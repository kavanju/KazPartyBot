FROM python:3.13-slim

# Установка системных библиотек
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libsm6 libxext6 libxrender-dev \
    ffmpeg \
    && apt-get clean

# Установка рабочей директории
WORKDIR /app

# Копирование файлов
COPY . /app

# Установка зависимостей Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Старт бота
CMD ["python", "bot.py"]
