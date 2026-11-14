FROM python:3.11-slim

WORKDIR /app

# Ensure unbuffered logging in Cloud Run
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source and modules
COPY app_config.py .
COPY app.py .
COPY routes/ routes/
COPY services/ services/
COPY templates/ templates/

EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
