# Use a lightweight Python base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install dependencies first (helps with Docker caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port Flask runs on
EXPOSE 5000

# Run the app using Gunicorn production server
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
