#!/bin/bash
set -e

# Benchmark configuration
# These values control the load generation parameters for all tests
# -t: number of threads (4)
# -c: number of concurrent connections (20)  
# -d: duration of the test (3s)
# Chosen to provide quick but statistically meaningful results
# Increase values for more intensive testing
BENCHMARK_THREADS="${BENCHMARK_THREADS:-4}"
BENCHMARK_CONNECTIONS="${BENCHMARK_CONNECTIONS:-20}"
BENCHMARK_DURATION="${BENCHMARK_DURATION:-3s}"

COMPOSE_FILE="$(dirname "$(readlink -f "$0")")/docker-compose.yml"

echo "Building and generating SSL certificates..."
docker compose -f "${COMPOSE_FILE}" build -q
docker run --rm -v reverse-proxy-benchmark_ssl_certs:/ssl alpine/openssl req -x509 -nodes -newkey rsa:4096 \
  -keyout /ssl/key.pem -out /ssl/cert.pem -days 365 \
  -subj "/C=US/O=Benchmark/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null

echo "Starting services..."
docker compose -f "${COMPOSE_FILE}" up -d
sleep 5

if ! docker compose -f "${COMPOSE_FILE}" ps | grep -q "Up"; then
  echo "✗ Startup failed"
  docker compose -f "${COMPOSE_FILE}" logs --tail=20
  exit 1
fi

echo "Running benchmarks..."
mkdir -p results
docker compose -f "${COMPOSE_FILE}" exec -T test-runner bash -c "rm -rf /app/results/*" 2>/dev/null || true

docker compose -f "${COMPOSE_FILE}" exec -T \
  -e BENCHMARK_THREADS="${BENCHMARK_THREADS}" \
  -e BENCHMARK_CONNECTIONS="${BENCHMARK_CONNECTIONS}" \
  -e BENCHMARK_DURATION="${BENCHMARK_DURATION}" \
  test-runner bash <<'EOF'

declare -A tests=(
  [nginx_http]="http://nginx:80/data.json false"
  [nginx_https]="https://nginx:443/data.json true false"
  [nginx_https_http2]="https://nginx:443/data.json true true"
  [caddy_http]="http://caddy:80/data.json false"
  [caddy_https]="https://caddy:443/data.json true false"
  [caddy_https_http2]="https://caddy:443/data.json true true"
  [traefik_http]="http://traefik:80/data.json false"
  [traefik_https]="https://traefik:443/data.json true false"
  [traefik_https_http2]="https://traefik:443/data.json true true"
  [nginx_constrained_http]="http://nginx_constrained:80/data.json false"
  [nginx_constrained_https]="https://nginx_constrained:443/data.json true false"
  [nginx_constrained_https_http2]="https://nginx_constrained:443/data.json true true"
  [caddy_constrained_http]="http://caddy_constrained:80/data.json false"
  [caddy_constrained_https]="https://caddy_constrained:443/data.json true false"
  [caddy_constrained_https_http2]="https://caddy_constrained:443/data.json true true"
  [traefik_constrained_http]="http://traefik_constrained:80/data.json false"
  [traefik_constrained_https]="https://traefik_constrained:443/data.json true false"
  [traefik_constrained_https_http2]="https://traefik_constrained:443/data.json true true"
)

sleep 10
for name in "${!tests[@]}"; do
  test_info=${tests[$name]}
  url=$(echo "$test_info" | cut -d' ' -f1)
  use_ssl=$(echo "$test_info" | cut -d' ' -f2)
  use_http2=$(echo "$test_info" | cut -d' ' -f3)

  proxy=$(echo "$name" | cut -d_ -f1)
  scenario=$(echo "$name" | cut -d_ -f2-)

  mkdir -p "/app/results/${proxy}"
  cmd="rewrk -t${BENCHMARK_THREADS} -c${BENCHMARK_CONNECTIONS} -d${BENCHMARK_DURATION} --pct -h $url"
  if [ "$use_http2" = "true" ]; then
    cmd="$cmd --http2"
  fi
  
  if ! eval "$cmd" > "/app/results/${proxy}/${scenario}.txt" 2>&1; then
    echo "⚠ Warning: Benchmark failed for ${name} (${url})" >&2
    echo "   Check /app/results/${proxy}/${scenario}.txt for details"
  fi
done
EOF

echo "Analyzing results..."
docker compose -f "${COMPOSE_FILE}" exec -T test-runner python /app/analyze_results.py

echo ""
read -p "Stop containers? (y/N): " -n 1 -r < /dev/tty 2>/dev/null || REPLY="n"
echo
[[ $REPLY =~ ^[Yy]$ ]] && docker compose -f "${COMPOSE_FILE}" down -v

echo "Done."
