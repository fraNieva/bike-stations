FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Run migrations first, then start the server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000