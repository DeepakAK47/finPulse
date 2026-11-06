FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r requirements.txt
# Use shell form so $PORT is expanded. Render provides this variable.
CMD uvicorn api.main:app --host 0.0.0.0 --port $PORT