# Етап 1: Завантажуємо статичний ffmpeg
FROM alpine:latest AS downloader

# Встановлюємо необхідні інструменти
RUN apk add --no-cache wget tar xz

# Завантажуємо та розпаковуємо статичний ffmpeg
RUN wget -O /ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xJf /ffmpeg.tar.xz \
    && ls -la

# Етап 2: Основний образ для бота
FROM python:3.11-slim

# Копіюємо статичний ffmpeg
COPY --from=downloader /ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ffmpeg
COPY --from=downloader /ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ffprobe

# Перевіряємо, що ffmpeg працює
RUN chmod +x /usr/local/bin/ffmpeg && /usr/local/bin/ffmpeg -version

WORKDIR /app

# Встановлюємо залежності Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
