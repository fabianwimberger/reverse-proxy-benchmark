FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
    ca-certificates curl python3 python3-pip > /dev/null && \
    rm -rf /var/lib/apt/lists/*

# Install vegeta (static binary)
ARG VEGETA_VERSION=12.13.0
RUN curl -L -o /tmp/vegeta.tar.gz \
    https://github.com/tsenart/vegeta/releases/download/v${VEGETA_VERSION}/vegeta_${VEGETA_VERSION}_linux_amd64.tar.gz && \
    tar -xzf /tmp/vegeta.tar.gz -C /usr/local/bin vegeta && \
    rm /tmp/vegeta.tar.gz && \
    chmod +x /usr/local/bin/vegeta

WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --break-system-packages -r /app/requirements.txt || pip3 install -r /app/requirements.txt

COPY analyze_results.py /app/analyze_results.py

CMD ["sleep", "infinity"]
