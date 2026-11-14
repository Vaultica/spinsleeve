FROM python:3.11-slim

WORKDIR /app

# Ensure unbuffered logging in Cloud Run
ENV PYTHONUNBUFFERED=1

# Install requirements
COPY src/pipeline_v2/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

RUN chmod +x entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
