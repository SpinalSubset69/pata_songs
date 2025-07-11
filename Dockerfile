FROM python:3.13.5-slim-bookworm

RUN apt update && apt -y install ffmpeg

COPY requirements.txt /app/

WORKDIR /app

RUN pip install --progress-bar on -r requirements.txt

COPY /src .

CMD ["python3", "pata_song_bot.py"]