FROM jrottenberg/ffmpeg:4.1-ubuntu AS ffmpeg

FROM python:3.11-slim

COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ffprobe

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
