FROM python:3.8-slim

ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /app

# Install system dependencies that might be needed for some python packages
# For example, build-essential for C extensions, or libgomp1 for libraries like scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.5.1/en_core_sci_sm-0.5.1.tar.gz
RUN python -m spacy download en_core_web_sm

# Pre-download NLTK data to avoid conflicts
RUN python -c "import nltk; nltk.download('stopwords', quiet=True); nltk.download('punkt', quiet=True)"

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 5000

# The command is now specified in docker-compose.yml
# CMD ["flask", "run", "--host=0.0.0.0"]