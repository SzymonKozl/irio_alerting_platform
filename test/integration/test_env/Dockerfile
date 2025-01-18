FROM postgres:15-bullseye

# install python
RUN apt-get update
RUN apt-get install -y python3.11

# clone project repo
ARG REPO_URL="https://github.com/SzymonKozl/irio_alerting_platform"
RUN git clone $REPO_URL repo

#move to tests dir
WORKDIR repo/testing/integration/test_env
RUN pip install -r requirements.txt

# postgres setup
RUN sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
RUN sudo -u postgres createdb irio_test
ENV POSTGRES_USER="postgres"
ENV POSTGRES_PASSWORD="postgres"
ENV POSTGRES_DB="irio_test"
ENV POSTGRES_HOST="localhost"
ENV POSTGRES_PORT="5432"

# SMTP credentials
ARG SMTP_USERNAME=""
ARG SMTP_PASSWORD=""

ENV SMTP_USERNAME=$SMTP_USERNAME
ENV SMTP_PASSWORD=$SMTP_PASSWORD

# install alerting platform dependencties
RUN pip install -r ../../../server/requirements.txt
CMD ["python", "../tests.py"]