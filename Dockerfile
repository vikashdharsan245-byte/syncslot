FROM python:3.11-slim

WORKDIR /app

# Copy and install tracking dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the remaining portal files
COPY . .

# Render free tier web services listen on port 10000 by default
EXPOSE 10000

# Fire up Gunicorn on port 10000
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]