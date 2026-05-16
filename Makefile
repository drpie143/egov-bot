.PHONY: install dev smoke test lint eval docker-build docker-run docker-up

install:
	pip install -r requirements-dev.txt

dev:
	python scripts/run_dev.py

smoke:
	python scripts/smoke_test_api.py

test:
	pytest -q

lint:
	ruff check src tests evaluation scripts

eval:
	python evaluation/run_all.py

docker-build:
	docker build -t egov-bot .

docker-run:
	docker run --env-file .env -p 7860:7860 egov-bot

docker-up:
	docker compose up --build
