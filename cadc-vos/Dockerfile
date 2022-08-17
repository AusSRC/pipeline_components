FROM python:3.8-slim
WORKDIR /app

# Install module
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy script
COPY copy.sh .

# Entrypoint
ENTRYPOINT [ "/app/copy.sh" ]