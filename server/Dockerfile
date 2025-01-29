FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y postgresql libpq-dev python3.11-dev build-essential && \
    apt-get clean

COPY . /repo
WORKDIR /repo/server

RUN pip install --user -r requirements.txt

CMD ["python", "main.py"]

