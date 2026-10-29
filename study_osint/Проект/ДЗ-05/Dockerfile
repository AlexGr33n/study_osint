FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY collector ./collector
COPY targets.toml .
ENTRYPOINT ["python", "-m", "collector"]
CMD ["run"]
