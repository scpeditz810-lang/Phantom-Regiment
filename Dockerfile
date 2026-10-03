FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fix permissions so the database is writable on Render
RUN mkdir -p data && chmod -R 777 /app

EXPOSE 10000

CMD ["python", "bot.py"]
