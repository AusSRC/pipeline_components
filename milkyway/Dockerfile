FROM python:3.8-slim
WORKDIR /app

# Install requirements
COPY requirements.txt .
RUN apt-get update && apt-get install -y gcc
RUN pip install -r requirements.txt

# Copy all files
COPY *.py /app
ENTRYPOINT ["python", "milkyway_validation.py"]
