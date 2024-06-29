FROM python:3.10-slim

ENV PYTHONUNBUFFERED=true

WORKDIR /usr/app

RUN mkdir /usr/app/cache

COPY requirements.txt ./

RUN apt-get update -y
RUN apt-get install ffmpeg -y --no-install-recommends

RUN pip install --disable-pip-version-check --no-cache-dir --upgrade -r requirements.txt

COPY . .

CMD ["fastapi", "run", "--port", "8010"]
