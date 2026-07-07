FROM python:3.11-slim

# Create a secure non-root user required by Hugging Face
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements and install them securely
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the remaining portal files
COPY --chown=user . .

# Hugging Face spaces use port 7860 by default
EXPOSE 7860

# Run using Gunicorn on port 7860
CMD ["gunicorn", "--bind", "0.0.0.0:7860", "app:app"]