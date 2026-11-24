.PHONY: up down build test clean

up:
	docker compose up -d --build

down:
	docker compose down

build:
	docker compose build

test:
	pytest backend/tests -v

clean:
	docker compose down -v
