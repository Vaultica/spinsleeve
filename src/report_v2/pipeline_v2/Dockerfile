FROM python:3.11-slim

WORKDIR /app

# Ensure unbuffered logging in Cloud Run
ENV PYTHONUNBUFFERED=1

# Install Python requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy pipeline scripts
COPY *.py ./

CMD ["python", "sync.py"]
