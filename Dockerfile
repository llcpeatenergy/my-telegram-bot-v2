# Використовуємо образ із попередньо встановленим ffmpeg
FROM jrottenberg/ffmpeg:4.1-alpine AS ffmpeg_stage

# Основний образ
FROM python:3.11-slim

# Копіюємо ffmpeg та ffprobe з першого етапу
COPY --from=ffmpeg_stage /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg_stage /usr/local/bin/ffprobe /usr/local/bin/ffprobe

# Перевіряємо, що ffmpeg працює
RUN /usr/local/bin/ffmpeg -version

WORKDIR /app

# Копіюємо та встановлюємо залежності Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копіюємо код бота
COPY bot.py .

# Запускаємо бота
CMD ["python", "-u", "bot.py"]
