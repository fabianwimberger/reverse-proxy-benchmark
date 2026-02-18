FROM python:3.13-trixie AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
    curl wget ca-certificates build-essential git > /dev/null && \
    rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain stable
ENV PATH="/root/.cargo/bin:${PATH}"

RUN git clone https://github.com/ChillFish8/rewrk.git /tmp/rewrk && \
    cd /tmp/rewrk && \
    cargo build --release && \
    cp target/release/rewrk /usr/local/bin/rewrk && \
    chmod +x /usr/local/bin/rewrk

FROM python:3.13-trixie

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update -qq && \
    apt-get install -y -qq --no-install-recommends \
    curl wget apache2-utils ca-certificates > /dev/null && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/rewrk /usr/local/bin/rewrk

COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

WORKDIR /app

COPY analyze_results.py /app/analyze_results.py

