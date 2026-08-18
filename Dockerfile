FROM python:3.11-slim

WORKDIR /app

# Встановлюємо необхідні пакети
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файли
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

# Запускаємо бота
CMD ["python", "-u", "bot.py"]
