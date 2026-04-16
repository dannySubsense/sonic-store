.PHONY: install dev-install run test redis-up

install:
	pip install -r requirements.txt

dev-install:
	pip install -r requirements.txt -r requirements-dev.txt

run:
	uvicorn src.api.app:app --reload --port 8000

test:
	pytest tests/ -v

redis-up:
	redis-server --daemonize yes
