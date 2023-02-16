FROM python:3.8-slim
WORKDIR /app

# Install curl for download
RUN apt-get update && \
    apt-get install -y curl procps

# Install requirements
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all files
COPY . /app
