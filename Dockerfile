FROM python:3.13.5-slim-bookworm

RUN apt update && apt -y install ffmpeg

COPY requirements.txt /app/

WORKDIR /app

RUN pip install --progress-bar on -r requirements.txt

COPY /src .

# Install Nodejs since PytubeFIX required it to auto generete PO Token for youtube search within a banned IP
RUN ["chmod", "+x", "/app/scripts/init_bot.sh"]

ENTRYPOINT /app/scripts/init_bot.sh
