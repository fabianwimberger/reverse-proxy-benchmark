.PHONY: all bench clean

THREADS ?= 4
CONNECTIONS ?= 20
DURATION ?= 3s

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
	@docker compose exec -T test-runner python /app/analyze_results.py
	@echo "Done. Results in results/charts/"

run-benchmarks:
	@docker compose exec -T test-runner bash -c ' \
		threads=$(THREADS); conn=$(CONNECTIONS); dur=$(DURATION); \
		bench() { \
			mkdir -p "/app/results/$$1"; \
			cmd="rewrk -t$$threads -c$$conn -d$$dur --pct -h $$2"; \
			[ -n "$$3" ] && cmd="$$cmd --http2"; \
			$$cmd > "/app/results/$$1/$$4.txt" 2>&1 || true; \
		}; \
		bench nginx http://nginx:80/data.json "" http; \
		bench nginx https://nginx:443/data.json "" https; \
		bench nginx https://nginx:443/data.json 1 https_http2; \
		bench caddy http://caddy:80/data.json "" http; \
		bench caddy https://caddy:443/data.json "" https; \
		bench caddy https://caddy:443/data.json 1 https_http2; \
		bench traefik http://traefik:80/data.json "" http; \
		bench traefik https://traefik:443/data.json "" https; \
		bench traefik https://traefik:443/data.json 1 https_http2; \
		bench nginx_constrained http://nginx_constrained:80/data.json "" http; \
		bench nginx_constrained https://nginx_constrained:443/data.json "" https; \
		bench nginx_constrained https://nginx_constrained:443/data.json 1 https_http2; \
		bench caddy_constrained http://caddy_constrained:80/data.json "" http; \
		bench caddy_constrained https://caddy_constrained:443/data.json "" https; \
		bench caddy_constrained https://caddy_constrained:443/data.json 1 https_http2; \
		bench traefik_constrained http://traefik_constrained:80/data.json "" http; \
		bench traefik_constrained https://traefik_constrained:443/data.json "" https; \
		bench traefik_constrained https://traefik_constrained:443/data.json 1 https_http2; \
	'

clean:
	@docker compose down -v 2>/dev/null || true
	@docker volume rm -f reverse-proxy-benchmark_ssl_certs 2>/dev/null || true
	@echo "Cleaning results..."
	@docker run --rm -v $(PWD)/results:/results alpine sh -c 'rm -rf /results/*' 2>/dev/null || true

run: clean all
