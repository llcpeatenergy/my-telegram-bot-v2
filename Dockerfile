FROM python:3.11-slim

WORKDIR /app

# Встановлюємо залежності Python, включаючи ffmpeg-python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "-u", "bot.py"]
