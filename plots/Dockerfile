FROM python:3.8-slim
WORKDIR /app

# Install requirements
RUN apt-get update && apt-get -y install procps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN python -m pip install -U --pre astroquery

# Copy all files
COPY *.py /app
