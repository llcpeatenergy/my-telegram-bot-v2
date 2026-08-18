# Етап 1: Отримуємо ffmpeg з готового образу
FROM jrottenberg/ffmpeg:4.1-alpine AS ffmpeg

# Етап 2: Основний образ для Python
FROM python:3.11-slim

# Копіюємо ffmpeg та ffprobe з першого етапу
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Перевіряємо, що ffmpeg працює
RUN /usr/local/bin/ffmpeg -version

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
