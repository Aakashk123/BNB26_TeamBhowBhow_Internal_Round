SHELL := /bin/bash
PY := $(CURDIR)/.venv/bin/python
BIN := $(CURDIR)/.venv/bin
export PYTHONPATH := $(CURDIR)/backend:$(CURDIR)/sdk/python:$(CURDIR)
.PHONY: bootstrap configure up down demo test test-python test-contracts test-web lint typecheck bench adversarial api-types audit package
bootstrap:
	python3.12 -m venv .venv
	$(BIN)/pip install pip==26.2.1
	$(BIN)/pip install -r backend/requirements.lock
	cd contracts && npm ci
	cd frontend && npm ci
	cd sdk/ts && npm ci
	cd contracts && npm run compile
	$(PY) scripts/export_contract.py
configure:
	$(PY) scripts/configure.py
up:
	docker compose up --build -d --wait --wait-timeout 240
down:
	docker compose down
demo:
	docker compose exec backend python -m app.seed.demo
test: test-python test-contracts test-web
test-python:
	cd backend && $(BIN)/pytest --cov=app/core --cov=app/engine --cov-fail-under=85 --cov-report=term-missing
test-contracts:
	cd contracts && npm test
test-web:
	cd frontend && npm test && npm run e2e
lint:
	cd backend && $(BIN)/ruff check app tests
	cd frontend && npm run lint
typecheck:
	cd backend && $(BIN)/mypy app/core app/engine --strict
	cd frontend && npm run typecheck
	cd contracts && npm run typecheck
	cd sdk/ts && npm run typecheck
bench:
	$(PY) bench/binding_bench.py
	$(PY) bench/origin_bench.py
	$(PY) bench/watermark_bench.py
adversarial:
	cd backend && $(PY) -m app.adversarial.runner
api-types:
	cd backend && ENV=test DATABASE_URL=sqlite:// $(PY) ../scripts/export_openapi.py
	cd frontend && npm run generate
audit:
	$(BIN)/pip-audit
	cd frontend && npm audit
	cd contracts && npm audit
package:
	$(PY) scripts/package.py
