FROM python:3.13-slim

# Установим системные зависимости
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libsm6 libxext6 libxrender-dev \
    ffmpeg \
    && apt-get clean

# Устанавливаем рабочую директорию
WORKDIR /app
COPY . /app

# Устанавливаем зависимости
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Запуск
CMD ["python", "bot.py"]
