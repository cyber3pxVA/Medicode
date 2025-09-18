FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System dependencies for scientific / NLP stack
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc g++ make \
    libgomp1 \
    libffi-dev libxml2-dev libxslt1-dev \
    libjpeg-dev zlib1g-dev \
    libssl-dev \
    libblas-dev liblapack-dev gfortran \
    curl git \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./

# Install Python dependencies & language models in one layer to reduce image size
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz \
    && python -m spacy download en_core_web_sm \
    && python - <<'EOF'
import nltk
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
EOF

# Copy the rest of the application code
COPY . .

EXPOSE 8080

# Default command for Cloud Run (can be overridden by docker-compose)
CMD ["python", "run.py"]