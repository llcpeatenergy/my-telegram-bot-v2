FROM python:3.11-slim

WORKDIR /app

# Встановлюємо тільки необхідне для завантаження та розпакування
RUN apt-get update && apt-get install -y wget xz-utils && \
    wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xJf ffmpeg-release-amd64-static.tar.xz && \
    cp ffmpeg-*-amd64-static/ffmpeg /usr/local/bin/ && \
    cp ffmpeg-*-amd64-static/ffprobe /usr/local/bin/ && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf ffmpeg-* && \
    apt-get remove -y wget xz-utils && apt-get autoremove -y && apt-get clean

# Перевіряємо, що ffmpeg працює
RUN /usr/local/bin/ffmpeg -version

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
