.PHONY: all bench clean

RATE ?= 5000
DURATION ?= 20s
CONNECTIONS ?= 5
all: bench

bench:
	@echo "Building..."
	@docker compose build -q
	@echo "Generating SSL certificates..."
	@docker run --rm -v reverse-proxy-benchmark_ssl_certs:/ssl alpine/openssl \
		req -x509 -nodes -newkey rsa:4096 \
		-keyout /ssl/key.pem -out /ssl/cert.pem -days 365 \
		-subj "/CN=localhost" 2>/dev/null
	@echo "Starting services..."
	@docker compose up -d
	@sleep 8
	@echo "Running benchmarks..."
	@mkdir -p results
	@$(MAKE) run-benchmarks
	@echo "Analyzing..."
	@docker compose exec -T test-runner python3 /app/analyze_results.py
	@echo "Done. Results in results/charts/"

run-benchmarks:
	@docker compose exec -T test-runner bash -c ' \
		rate="$(RATE)"; dur="$(DURATION)"; conn="$(CONNECTIONS)"; \
		bench() { \
			mkdir -p "/app/results/$$1"; \
			echo "GET $$2" | vegeta attack -rate=$$rate -duration=$$dur -connections=$$conn $$3 | vegeta report -type=json > "/app/results/$$1/$$4.json"; \
		}; \
		bench nginx http://nginx:80/data.json "" http; \
		bench nginx https://nginx:443/data.json "-insecure" https; \
		bench nginx https://nginx:443/data.json "-insecure -http2" https_http2; \
		bench caddy http://caddy:80/data.json "" http; \
		bench caddy https://caddy:443/data.json "-insecure" https; \
		bench caddy https://caddy:443/data.json "-insecure -http2" https_http2; \
		bench traefik http://traefik:80/data.json "" http; \
		bench traefik https://traefik:443/data.json "-insecure" https; \
		bench traefik https://traefik:443/data.json "-insecure -http2" https_http2; \
	'

clean:
	@docker compose down -v 2>/dev/null || true
	@docker volume rm -f reverse-proxy-benchmark_ssl_certs 2>/dev/null || true
	@echo "Cleaning results..."
	@docker run --rm -v $(PWD)/results:/results alpine sh -c 'rm -rf /results/*' 2>/dev/null || true

run: clean all
