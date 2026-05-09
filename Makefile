.PHONY: all bench clean run lint format wait-ready run-benchmarks

RATE ?= 5000
DURATION ?= 20s
CONNECTIONS ?= 64
WARMUP_DURATION ?= 5s

COMPOSE_PROJECT := $(shell docker compose config 2>/dev/null | awk '/^name:/{print $$2}')
SSL_VOLUME := $(COMPOSE_PROJECT)_ssl_certs

all: bench

bench:
	@echo "Building..."
	@docker compose build -q
	@echo "Generating SSL certificates..."
	@docker run --rm -v $(SSL_VOLUME):/ssl --entrypoint sh alpine/openssl:3.5.0 -c '\
		if [ ! -s /ssl/cert.pem ] || [ ! -s /ssl/key.pem ]; then \
			openssl req -x509 -nodes -newkey rsa:4096 \
				-keyout /ssl/key.pem -out /ssl/cert.pem -days 365 \
				-subj "/CN=localhost" >/dev/null 2>&1; \
		fi'
	@docker run --rm -v $(SSL_VOLUME):/ssl alpine:3.21 sh -c '\
		if [ ! -s /ssl/haproxy.pem ] || [ /ssl/cert.pem -nt /ssl/haproxy.pem ] || [ /ssl/key.pem -nt /ssl/haproxy.pem ]; then \
			cat /ssl/cert.pem /ssl/key.pem > /ssl/haproxy.pem; \
		fi' >/dev/null 2>&1
	@echo "==> Unrestricted benchmarks"
	@docker compose up -d >/dev/null 2>&1
	@mkdir -p results
	@$(MAKE) --no-print-directory wait-ready
	@$(MAKE) --no-print-directory run-warmup
	@$(MAKE) --no-print-directory run-benchmarks SUFFIX=""
	@docker compose down >/dev/null 2>&1
	@echo "==> Restricted benchmarks (2 cores, 4GB)"
	@docker compose -f docker-compose.yml -f docker-compose.restricted.yml up -d >/dev/null 2>&1
	@$(MAKE) --no-print-directory wait-ready
	@$(MAKE) --no-print-directory run-warmup
	@$(MAKE) --no-print-directory run-benchmarks SUFFIX="_restricted"
	@echo "==> Analyzing"
	@docker compose exec -T test-runner python3 /app/analyze_results.py
	@echo "Done. Results in results/charts/"

wait-ready:
	@docker compose exec -T test-runner bash -c ' \
		printf "  waiting for proxies"; \
		for proxy in nginx caddy traefik haproxy; do \
			ok=0; \
			for i in $$(seq 1 60); do \
				if curl -fsSk -o /dev/null --max-time 1 "http://$$proxy/data.json" >/dev/null 2>&1; then ok=1; break; fi; \
				printf "."; sleep 1; \
			done; \
			if [ "$$ok" -ne 1 ]; then echo " FAIL ($$proxy HTTP)"; exit 1; fi; \
			ok=0; \
			for i in $$(seq 1 60); do \
				if curl -fsSk -o /dev/null --max-time 1 "https://$$proxy/data.json" >/dev/null 2>&1; then ok=1; break; fi; \
				printf "."; sleep 1; \
			done; \
			if [ "$$ok" -ne 1 ]; then echo " FAIL ($$proxy HTTPS)"; exit 1; fi; \
		done; \
		echo " ready"; \
	'

run-warmup:
	@docker compose exec -T test-runner bash -c ' \
		rate="$(RATE)"; dur="$(WARMUP_DURATION)"; conn="$(CONNECTIONS)"; \
		printf "  Warming up..."; \
		for proxy in nginx caddy traefik haproxy; do \
			echo "GET http://$$proxy:80/data.json" | vegeta attack -rate=$$rate -duration=$$dur -connections=$$conn >/dev/null 2>&1; \
			echo "GET https://$$proxy:443/data.json" | vegeta attack -rate=$$rate -duration=$$dur -connections=$$conn -insecure -http2 >/dev/null 2>&1; \
		done; \
		echo " done"; \
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
		scenarios=$$(printf "%s\n" \
			"nginx|http://nginx:80/data.json||http" \
			"nginx|https://nginx:443/data.json|-insecure|https" \
			"nginx|https://nginx:443/data.json|-insecure -http2|https_http2" \
			"caddy|http://caddy:80/data.json||http" \
			"caddy|https://caddy:443/data.json|-insecure|https" \
			"caddy|https://caddy:443/data.json|-insecure -http2|https_http2" \
			"traefik|http://traefik:80/data.json||http" \
			"traefik|https://traefik:443/data.json|-insecure|https" \
			"traefik|https://traefik:443/data.json|-insecure -http2|https_http2" \
			"haproxy|http://haproxy:80/data.json||http" \
			"haproxy|https://haproxy:443/data.json|-insecure|https" \
			"haproxy|https://haproxy:443/data.json|-insecure -http2|https_http2" \
			| shuf); \
		while IFS="|" read -r proxy url opts scenario; do \
			bench "$$proxy" "$$url" "$$opts" "$$scenario"; \
		done <<< "$$scenarios"; \
	'

clean:
	@docker compose down -v >/dev/null 2>&1 || true
	@docker volume rm -f $(SSL_VOLUME) >/dev/null 2>&1 || true
	@echo "Cleaning results..."
	@docker run --rm -v $(PWD)/results:/results alpine sh -c 'rm -rf /results/*' >/dev/null 2>&1 || true

run: clean all

lint:
	@echo "Running linters..."
	@ruff check analyze_results.py

format:
	@echo "Formatting code..."
	@ruff format analyze_results.py
