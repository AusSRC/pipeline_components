FROM python:3.8-slim
WORKDIR /app

# Install requirements
RUN apt-get update && apt-get -y install procps
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all files
COPY *.py /app