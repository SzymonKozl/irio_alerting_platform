FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y postgresql libpq-dev python3.11-dev build-essential && \
    apt-get clean

USER postgres

ENV PATH="/var/lib/postgresql/.local/bin:$PATH"

COPY . /home/postgres/repo
WORKDIR /home/postgres/repo/unit_tests

RUN pip install --user -r requirements.txt

CMD ["pytest", "-p", "no:cacheprovider"]
