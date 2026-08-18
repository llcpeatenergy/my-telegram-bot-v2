FROM python:3.11-slim

WORKDIR /app

# ВСТАНОВЛЮЄМО FFMPEG ЧЕРЕЗ APT-GET (НАЙНАДІЙНІШЕ)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
