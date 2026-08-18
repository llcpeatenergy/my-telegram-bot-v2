# Етап 1: Завантажуємо статично зібраний ffmpeg
FROM alpine:latest AS downloader
RUN apk add --no-cache wget tar
RUN wget -O /ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
    && tar -xf /ffmpeg.tar.xz --strip-components=1 -C / \
    && ls -la /ffmpeg

# Етап 2: Основний образ для бота
FROM python:3.11-slim

# Копіюємо статичний ffmpeg
COPY --from=downloader /ffmpeg/ffmpeg /usr/local/bin/ffmpeg
COPY --from=downloader /ffmpeg/ffprobe /usr/local/bin/ffprobe

# Перевіряємо, що ffmpeg працює
RUN chmod +x /usr/local/bin/ffmpeg && /usr/local/bin/ffmpeg -version

WORKDIR /app

# Встановлюємо залежності Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
