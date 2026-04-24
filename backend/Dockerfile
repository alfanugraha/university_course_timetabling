FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Make init script executable
RUN chmod +x scripts/init.sh

CMD ["scripts/init.sh"]
