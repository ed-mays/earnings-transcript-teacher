FROM python:3.12-slim

WORKDIR /repo

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Copy the full repo so root-level modules (db/, core/, prompts/) are importable
COPY . .

# Match the PYTHONPATH that dev.sh sets so `from db.repositories import ...` works
ENV PYTHONPATH=/repo

WORKDIR /repo/api

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
