FROM python:3.12-slim
WORKDIR /app

# Ignore python packages in the home directory when it is mounted into the container
ENV PYTHONNOUSERSITE=1

RUN apt-get update && apt-get install -y procps

# Install aussrc_tools and requirements
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip install .
