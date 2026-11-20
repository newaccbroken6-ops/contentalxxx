FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5986
EXPOSE 5986

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5986"]
