if you cannot install `psycopg2` dependency try:
```bash
sudo apt install libpq-dev python<version>-dev
```
where "\<version\>" is python version that you are using.

Environment variables:
- `SMTP_USERNAME`: alerting platform email
- `SMTP_PASSWORD`: alerting platform email password
- `SMTP_SERVER`: mailing service address (`"smtp.gmail.com"` if not provided)
- `SMTP_PORT`: mailing service address (`"587"` if not provided)
