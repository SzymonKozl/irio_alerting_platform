FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1
COPY app /app/
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8080
CMD ["python", "app.py"]
