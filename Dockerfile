# Lista de Compras — pequena app web Flask.
FROM python:3.11-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8003
CMD ["python", "-u", "app.py"]
