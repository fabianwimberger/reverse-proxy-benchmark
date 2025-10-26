# Reverse Proxy Benchmark

A Docker-based benchmarking suite for comparing popular reverse proxy servers: **Nginx**, **Caddy**, and **Traefik**.

## Overview

This project benchmarks reverse proxy performance across multiple scenarios:
- HTTP
- HTTPS
- HTTPS with HTTP/2
- Resource-constrained environments (2 CPU cores, 2GB memory)

All proxies forward requests to the same backend Nginx server serving a ~20KB JSON file.

## Benchmarked Proxies

- **Nginx** - High-performance web server and reverse proxy
- **Caddy** - Modern web server with automatic HTTPS
- **Traefik** - Cloud-native application proxy

## Requirements

- Docker with Docker Compose
- ~4GB available RAM
- Linux, macOS, or WSL2

## Quick Start

Run the entire benchmark suite:

```bash
./run.sh
```

This script will:
1. Build containers and generate SSL certificates
2. Start all proxy services and backend
3. Run benchmarks using `rewrk` (30s duration, 4 threads, 20 connections)
4. Analyze results and generate charts
5. Display performance comparison tables
6. Optionally stop containers when done

## Benchmark Scenarios

Each proxy is tested in the following scenarios:

| Scenario | Description |
|----------|-------------|
| `http` | Plain HTTP |
| `https` | HTTPS (TLS 1.2/1.3) |
| `https_http2` | HTTPS with HTTP/2 enabled |
| `constrained_*` | Same scenarios with 2 CPU cores and 2GB memory limit |

## Results

Results are stored in the `results/` directory:
- `results/{proxy}/{scenario}.txt` - Raw benchmark output
- `results/charts/summary_*.png` - Visual comparison charts

### Metrics Collected

- **Req/s** - Requests per second (throughput)
- **Lat(ms)** - Average latency in milliseconds
- **Max(ms)** - Maximum latency
- **MB/s** - Megabytes transferred per second
- **Errors** - Number of failed requests
- **Error%** - Percentage of failed requests

### Example Output

```
========================================================
REVERSE PROXY BENCHMARK (~20KB JSON)
========================================================

HTTP
---------------------------------------------------
Proxy           Req/s        Lat(ms)      Max(ms)
nginx           45000        0.44         12.50
caddy           38000        0.52         15.30
traefik         35000        0.57         18.20
```

Charts are automatically generated showing:
- Throughput comparison (requests/sec)
- Transfer rates (MB/sec)
- Latency with standard deviation
- Error rates

## Project Structure

```
.
├── run.sh                 # Main benchmark script
├── docker-compose.yml     # Service definitions
├── Dockerfile            # Test runner container
├── analyze_results.py    # Results analysis and chart generation
├── configs/
│   ├── backend/          # Backend server configuration
│   ├── nginx/            # Nginx proxy configuration
│   ├── caddy/            # Caddy configuration
│   └── traefik/          # Traefik configuration
└── results/              # Benchmark results (generated)
```

## Configuration

### Benchmark Parameters

Edit `run.sh:62` to modify benchmark settings:

```bash
rewrk -t4 -c20 -d30s --pct -h $url
```

- `-t4` - 4 threads
- `-c20` - 20 concurrent connections
- `-d30s` - 30 second duration

### Proxy Configurations

Each proxy has its own configuration in the `configs/` directory:
- `configs/nginx/default.conf` - Nginx reverse proxy settings
- `configs/caddy/Caddyfile` - Caddy server configuration
- `configs/traefik/*.yml` - Traefik static and dynamic config

### Resource Constraints

Constrained scenarios use these limits (see docker-compose.yml:46-52):

```yaml
limits:
  cpus: '2.0'
  memory: 2G
```

## Manual Usage

Start services without running benchmarks:

```bash
docker compose up -d
```

Run a single benchmark manually:

```bash
docker compose exec test-runner bash
rewrk -t4 -c20 -d30s --pct -h http://nginx:80/data.json
```

Stop all services:

```bash
docker compose down -v
```

## Dependencies

The test-runner container includes:
- **rewrk** - Modern HTTP benchmarking tool
- **Python 3** - For result analysis
- **numpy** - Numerical processing
- **matplotlib** - Chart generation

## License

This benchmark suite is provided as-is for performance testing and comparison purposes.
