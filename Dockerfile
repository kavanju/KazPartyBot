FROM python:3.10-slim

# Установим зависимости
RUN apt-get update && apt-get install -y \
    libsm6 libxext6 libxrender-dev \
    tesseract-ocr \
    ffmpeg \
    && apt-get clean

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
