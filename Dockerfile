FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Створюємо простий файл для health check
RUN echo "OK" > /app/health

# Вказуємо команду запуску
CMD ["python", "-u", "bot.py"]
