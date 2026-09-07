FROM python:3.12-slim

WORKDIR /app

# System deps + Node.js (para claude CLI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Source
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
