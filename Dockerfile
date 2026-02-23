FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 5000

# Use gunicorn for unix deployments
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]