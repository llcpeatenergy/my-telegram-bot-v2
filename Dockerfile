FROM linuxserver/ffmpeg:latest AS ffmpeg

FROM python:3.11-slim

# Копіюємо ffmpeg та ffprobe
COPY --from=ffmpeg /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg /usr/local/bin/ffprobe /usr/local/bin/ff
