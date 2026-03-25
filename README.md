# Reverse Proxy Benchmark

[![CI](https://github.com/fabianwimberger/reverse-proxy-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/fabianwimberger/reverse-proxy-benchmark/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Docker-based benchmarking suite comparing **Nginx**, **Caddy**, and **Traefik** across HTTP/1.1, HTTPS/1.1, and HTTPS/2.

Powered by [Vegeta](https://github.com/tsenart/vegeta), an industry-standard HTTP load testing tool.

> **Why this exists:** Built while evaluating reverse proxy options for production IoT workloads — specifically to inform infrastructure decisions for high-throughput telemetry pipelines.

## Why This Project?

Reverse proxies are critical infrastructure components, but performance characteristics vary significantly between solutions and protocol versions. Rather than relying on vendor benchmarks or generic recommendations, this project provides reproducible, data-driven insights for infrastructure decisions.

**Goals:**
- Compare Nginx, Caddy, and Traefik objectively
- Measure impact of TLS and HTTP/2 on throughput and latency
- Establish baseline metrics for containerized deployments
- Provide reproducible methodology for independent verification

## Features

- **Three proxies** — Nginx, Caddy, Traefik
- **Three protocols** — HTTP/1.1, HTTPS/1.1, HTTPS/2
- **Realistic load testing** — Vegeta with configurable rate and duration
- **Visual results** — matplotlib charts comparing all scenarios
- **Containerized** — fully Docker-based for reproducibility

## Quick Start

```bash
# Clone the repository
git clone https://github.com/fabianwimberger/reverse-proxy-benchmark.git
cd reverse-proxy-benchmark

# Run full benchmark (~2 minutes)
make

# Or with custom parameters
make RATE=10000 DURATION=10s CONNECTIONS=100

# Clean up
make clean
```

Results are saved to `results/charts/` with timestamped PNG files.

## How It Works

```
Vegeta → [Nginx|Caddy|Traefik] → Backend
```

**Proxies:** Nginx 1.29.7 · Caddy 2.11.2 · Traefik 3.6.11

**Load Generator:** Vegeta v12.13.0

**Methodology:**
- Attack Rate: Configurable (default 5,000 req/s)
- Duration: Configurable (default 20s)
- Connections: Configurable pool size (default 5)
- Payload: ~20KB JSON file
- Metrics: Throughput, latency percentiles (P50, P90, P95, P99), success rate

## Key Findings

Based on benchmarks with ~20KB JSON payload at **5,000 req/s** (default parameters), 0% errors across all scenarios:

| Scenario | Best Mean Latency | Best P99 Latency | Notes |
|----------|-------------------|------------------|-------|
| HTTP/1.1 | **Nginx** (~0.27ms) | **Nginx** (~0.80ms) | All three within ~30% of each other |
| HTTPS/1.1 | **Traefik** (~0.45ms) | **Traefik** (~1.41ms) | Caddy shows severe tail latency (P99 ~38ms) |
| HTTPS/2 | **Traefik** (~0.44ms) | **Traefik** (~1.33ms) | Nginx higher latency under HTTP/2 (P99 ~9ms) |

**What the Data Actually Shows:**

**Nginx** leads on raw plaintext (HTTP/1.1) performance — marginally the fastest with the tightest P99. However, it does not carry that advantage into TLS scenarios: under HTTPS/1.1 and HTTPS/2, Nginx's P99 climbs to ~9ms while Traefik stays under 1.5ms.

**Traefik** is the clear winner for TLS workloads. It posts the lowest mean and P99 latency on both HTTPS/1.1 and HTTPS/2, and its performance is highly consistent (low max values). Its slight edge in plaintext makes it competitive across all three scenarios.

**Caddy** performs well on HTTP/1.1 and HTTPS/2 (mean latency comparable to the others), but exhibits severe tail latency under HTTPS/1.1 — P99 of 38ms and a max of 217ms, roughly 27x higher P99 than Traefik in the same scenario. This warrants further investigation into TLS session handling or connection pool behavior.

**Honest Observations:**
- All three proxies achieved 0% errors at 5,000 req/s on this hardware — a clean result
- Nginx wins on HTTP/1.1 raw throughput, but Traefik wins on TLS scenarios
- Traefik offers the best ergonomics for containerized environments *and* the best TLS latency
- Caddy's HTTPS/1.1 tail latency is a notable outlier — worth investigating before using in latency-sensitive TLS workloads
- HTTP/2 does not automatically lower latency vs HTTPS/1.1 — Nginx actually performs comparably on both

*The "best" proxy depends on your constraints: plaintext throughput (Nginx), TLS performance + operational simplicity (Traefik), or auto-provisioned certificates (Caddy).*

## Benchmark Results

<p align="center">
  <img src="assets/local-results/benchmark.png" width="100%" alt="Benchmark Results">
  <br><em>5,000 req/s · 20s duration · ~20KB JSON payload · 0% errors across all scenarios</em>
</p>

## Configuration

| Component | Location |
|-----------|----------|
| Proxy configs | `configs/{nginx,caddy,traefik}/` |
| Benchmark parameters | `Makefile` (RATE, DURATION, CONNECTIONS) |
| Analysis script | `analyze_results.py` |

## Manual Testing

```bash
docker compose up -d

# HTTP/1.1 test
docker compose exec -T test-runner sh -c \
  'echo "GET http://nginx:80/data.json" | vegeta attack -rate=1000 -duration=5s | vegeta report'

# HTTPS/2 test
docker compose exec -T test-runner sh -c \
  'echo "GET https://traefik:443/data.json" | vegeta attack -rate=1000 -duration=5s -insecure -http2 | vegeta report'

docker compose down -v
```

## Requirements

- Docker Engine 24.0+ with Docker Compose
- Make
- ~4GB RAM available to Docker
- Linux/macOS (Windows via WSL2)

## License

MIT License — see [LICENSE](LICENSE) file.
