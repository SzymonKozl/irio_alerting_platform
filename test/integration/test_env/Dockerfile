FROM python:3.11-slim

# non interactive postgres installation
ENV DEBIAN_FRONTEND=noninteractive

# Install PostgreSQL client and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    postgresql \
    postgresql-client \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# clone project repo
ARG REPO_URL="https://github.com/SzymonKozl/irio_alerting_platform"
RUN git clone $REPO_URL repo
WORKDIR repo
RUN git checkout origin/test/integration

#move to tests dir
WORKDIR test/integration/test_env
RUN pip install -r requirements.txt

# postgres setup
# Set environment variable for PostgreSQL data directory
ENV PGDATA=/var/lib/postgresql/data

# Initialize the database and change the default password for postgres user
RUN service postgresql start \
    && su - postgres -c "psql -c \"ALTER USER postgres PASSWORD 'postgres';\"" \
    && su - postgres -c "psql -c \"CREATE DATABASE irio_test\""
ENV POSTGRES_USER="postgres"
ENV POSTGRES_PASSWORD="postgres"
ENV POSTGRES_DB="irio_test"
ENV POSTGRES_HOST="localhost"
ENV POSTGRES_PORT="5432"

# SMTP credentials
ARG SMTP_USERNAME=""
ARG SMTP_PASSWORD=""
ARG SMTP_SERVER=""

ENV SMTP_USERNAME=$SMTP_USERNAME
ENV SMTP_PASSWORD=$SMTP_PASSWORD
ENV SMTP_SERVER=$SMTP_SERVER

# install alerting platform dependencties
RUN pip install -r ../../../server/requirements.txt
CMD ["python", "../tests.py"]