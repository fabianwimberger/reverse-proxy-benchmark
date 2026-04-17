.PHONY: all bench clean run lint format wait-ready run-benchmarks

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
		-subj "/CN=localhost" >/dev/null 2>&1
	@docker run --rm -v reverse-proxy-benchmark_ssl_certs:/ssl alpine sh -c "cat /ssl/cert.pem /ssl/key.pem > /ssl/haproxy.pem" >/dev/null 2>&1
	@echo "==> Unrestricted benchmarks"
	@docker compose up -d >/dev/null 2>&1
	@mkdir -p results
	@$(MAKE) --no-print-directory wait-ready
	@$(MAKE) --no-print-directory run-benchmarks SUFFIX=""
	@docker compose down >/dev/null 2>&1
	@echo "==> Restricted benchmarks (2 cores, 4GB)"
	@docker compose -f docker-compose.yml -f docker-compose.restricted.yml up -d >/dev/null 2>&1
	@$(MAKE) --no-print-directory wait-ready
	@$(MAKE) --no-print-directory run-benchmarks SUFFIX="_restricted"
	@echo "==> Analyzing"
	@docker compose exec -T test-runner python3 /app/analyze_results.py
	@echo "Done. Results in results/charts/"

wait-ready:
	@docker compose exec -T test-runner bash -c ' \
		printf "  waiting for proxies"; \
		for proxy in nginx caddy traefik haproxy; do \
			ok=0; \
			for i in $$(seq 1 30); do \
				if curl -fsSk -o /dev/null --max-time 1 "http://$$proxy/data.json" >/dev/null 2>&1; then ok=1; break; fi; \
				printf "."; sleep 1; \
			done; \
			if [ "$$ok" -ne 1 ]; then echo " FAIL ($$proxy)"; exit 1; fi; \
		done; \
		echo " ready"; \
	'

run-benchmarks:
	@docker compose exec -T test-runner bash -c ' \
		rate="$(RATE)"; dur="$(DURATION)"; conn="$(CONNECTIONS)"; i=0; total=12; \
		bench() { \
			i=$$((i + 1)); \
			printf "  [%2d/%d] %-8s %-11s " "$$i" "$$total" "$$1" "$$4"; \
			mkdir -p "/app/results/$$1$(SUFFIX)"; \
			tmp=$$(mktemp); \
			echo "GET $$2" | vegeta attack -rate=$$rate -duration=$$dur -connections=$$conn $$3 > "$$tmp"; \
			vegeta report -type=json "$$tmp" > "/app/results/$$1$(SUFFIX)/$$4.json"; \
			python3 /app/summarize.py "/app/results/$$1$(SUFFIX)/$$4.json"; \
			rm -f "$$tmp"; \
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
		bench haproxy http://haproxy:80/data.json "" http; \
		bench haproxy https://haproxy:443/data.json "-insecure" https; \
		bench haproxy https://haproxy:443/data.json "-insecure -http2" https_http2; \
	'

clean:
	@docker compose down -v >/dev/null 2>&1 || true
	@docker volume rm -f reverse-proxy-benchmark_ssl_certs >/dev/null 2>&1 || true
	@echo "Cleaning results..."
	@docker run --rm -v $(PWD)/results:/results alpine sh -c 'rm -rf /results/*' >/dev/null 2>&1 || true

run: clean all

lint:
	@echo "Running linters..."
	@ruff check analyze_results.py

format:
	@echo "Formatting code..."
	@ruff format analyze_results.py
