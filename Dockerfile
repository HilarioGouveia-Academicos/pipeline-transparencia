FROM python:3.11.9-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências de sistema necessárias para o psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalação isolada de dependências para reaproveitar a cache de camadas
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Cópia do código-fonte após a instalação das dependências
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]