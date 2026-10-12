FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py setup.py ./
COPY static ./static
COPY data/seed.json data/reference.json ./data/
ENV PYTHONUNBUFFERED=1 PORT=8000 REQUIRE_AUTH=0 DASHBOARD_DB_PATH=/var/data/dashboard.sqlite
EXPOSE 8000
CMD ["sh", "-c", "python setup.py && exec python app.py"]
