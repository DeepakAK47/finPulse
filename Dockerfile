FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Render expects the service to bind to the PORT environment variable (default 10000)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "10000"]