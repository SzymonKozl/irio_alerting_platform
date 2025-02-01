FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y postgresql && \
    apt-get clean

USER postgres

ENV PATH="/var/lib/postgresql/.local/bin:$PATH"
ENV STATEFUL_SET_INDEX=1

COPY . /home/postgres/repo
WORKDIR /home/postgres/repo

RUN pip install --user -r test/unit/requirements.txt

CMD ["pytest", "-p", "no:cacheprovider"]
