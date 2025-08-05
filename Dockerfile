FROM python:3.10.13-slim

# Установим системные зависимости
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libsm6 libxext6 libxrender-dev \
    ffmpeg \
    && apt-get clean

# Установка рабочего каталога
WORKDIR /app
COPY . /app

# Установка зависимостей
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Старт
CMD ["python", "bot.py"]
