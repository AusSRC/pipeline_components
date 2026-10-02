FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y procps

# Install aussrc_tools and requirements
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .
