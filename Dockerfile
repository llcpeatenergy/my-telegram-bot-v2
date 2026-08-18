FROM python:3.11-slim

WORKDIR /app

# Завантажуємо статичний ffmpeg
RUN apt-get update && apt-get install -y wget && \
    wget -O ffmpeg.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xf ffmpeg.tar.xz && \
    cp ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    cp ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf ffmpeg.tar.xz ffmpeg-*-amd64-static && \
    apt-get remove -y wget && apt-get autoremove -y && apt-get clean

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
