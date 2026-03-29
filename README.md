# Reverse Proxy Benchmark

[![CI](https://github.com/fabianwimberger/reverse-proxy-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/fabianwimberger/reverse-proxy-benchmark/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Docker-based benchmarking suite comparing **Nginx**, **Caddy**, and **Traefik** across HTTP/1.1, HTTPS/1.1, and HTTPS/2.

Powered by [Vegeta](https://github.com/tsenart/vegeta), an industry-standard HTTP load testing tool.

## Why This Project?

Reverse proxies are critical infrastructure components, but performance characteristics vary significantly between solutions and protocol versions. Rather than relying on vendor benchmarks or generic recommendations, this project provides reproducible, data-driven insights for infrastructure decisions.

**Goals:**
- Compare Nginx, Caddy, and Traefik objectively
- Measure impact of TLS and HTTP/2 on throughput and latency
- Establish baseline metrics for containerized deployments
- Provide reproducible methodology for independent verification

<p align="center">
  <img src="assets/demo.gif" width="100%" alt="Benchmark Demo">
  <br><em>Full benchmark run: build, test 9 scenarios, analyze results</em>
</p>

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

**Takeaway:** Nginx wins on raw HTTP/1.1 throughput. Traefik wins on TLS workloads (lowest P99 across both HTTPS scenarios). Caddy shows a notable P99 outlier under HTTPS/1.1 (~38ms vs Traefik's ~1.4ms). All three achieved 0% errors at 5,000 req/s.

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

## Requirements

Docker Engine 24.0+ with Docker Compose, Make, ~4GB RAM. Linux/macOS (Windows via WSL2).

## License

MIT License — see [LICENSE](LICENSE) file.

### Third-Party Licenses

| Component | License | Source |
|-----------|---------|--------|
| Vegeta | [MIT](https://github.com/tsenart/vegeta/blob/master/LICENSE) | https://github.com/tsenart/vegeta |
| Nginx | [BSD-2-Clause](https://nginx.org/LICENSE) | https://nginx.org/ |
| Caddy | [Apache-2.0](https://github.com/caddyserver/caddy/blob/master/LICENSE) | https://github.com/caddyserver/caddy |
| Traefik | [MIT](https://github.com/traefik/traefik/blob/master/LICENSE.md) | https://github.com/traefik/traefik |
