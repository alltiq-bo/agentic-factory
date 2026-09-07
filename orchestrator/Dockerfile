FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY orchestrator/   ./orchestrator/
COPY agents/         ./agents/
COPY knowledge_base/ ./knowledge_base/
COPY teams/          ./teams/
COPY workflows/      ./workflows/
COPY profiles/       ./profiles/
COPY guidelines/     ./guidelines/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "orchestrator.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
