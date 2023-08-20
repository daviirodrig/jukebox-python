FROM python:3.10-slim

ENV PYTHONUNBUFFERED=true

WORKDIR /usr/app

COPY requirements.txt ./

RUN apt-get update -y
RUN apt-get install ffmpeg -y --no-install-recommends

RUN pip install --disable-pip-version-check --no-cache-dir --user -r requirements.txt

COPY . .

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8010", "--reload"]
