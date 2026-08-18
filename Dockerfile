# Етап 1: Отримуємо ffmpeg з офіційного образу
FROM alpine:latest AS ffmpeg_stage
RUN apk add --no-cache ffmpeg

# Етап 2: Основний образ для бота
FROM python:3.11-slim

# Копіюємо ffmpeg з першого етапу
COPY --from=ffmpeg_stage /usr/bin/ffmpeg /usr/bin/ffmpeg
COPY --from=ffmpeg_stage /usr/bin/ffprobe /usr/bin/ffprobe

# Перевіряємо, що ffmpeg працює
RUN ffmpeg -version

WORKDIR /app

# Встановлюємо залежності Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
