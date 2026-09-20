FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY authors_seed.csv .
COPY sql/ sql/
COPY src/ src/

CMD ["python", "src/run_pipeline.py"]
