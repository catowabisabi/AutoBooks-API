# ===================================
# AutoBooks-API Makefile
# Docker Container Management Commands
# ===================================

.PHONY: help build up down restart logs shell test migrate clean deploy

# Default target
help:
	@echo "AutoBooks-API Docker Commands"
	@echo "=============================="
	@echo ""
	@echo "Development:"
	@echo "  make dev          - Start development environment"
	@echo "  make dev-build    - Build and start development environment"
	@echo "  make dev-down     - Stop development environment"
	@echo ""
	@echo "Production:"
	@echo "  make prod         - Start production environment"
	@echo "  make prod-build   - Build and start production environment"
	@echo "  make prod-down    - Stop production environment"
	@echo ""
	@echo "General:"
	@echo "  make build        - Build Docker images"
	@echo "  make up           - Start containers (default: dev)"
	@echo "  make down         - Stop all containers"
	@echo "  make restart      - Restart all containers"
	@echo "  make logs         - View container logs"
	@echo "  make logs-api     - View API container logs"
	@echo "  make shell        - Open shell in API container"
	@echo ""
	@echo "Database:"
	@echo "  make migrate      - Run Django migrations"
	@echo "  make makemigrations - Create new migrations"
	@echo "  make clean_migrate - Clean and re-run migrations"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove containers and volumes"
	@echo "  make prune        - Remove unused Docker resources"
	@echo ""
	@echo "AWS ECR (Legacy):"
	@echo "  make deploy       - Deploy to AWS ECR"

# ===================================
# Development Commands
# ===================================
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

dev-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

dev-logs:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# ===================================
# Production Commands
# ===================================
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-build:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# ===================================
# General Docker Commands
# ===================================
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose restart

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

shell:
	docker compose exec api /bin/bash

# ===================================
# Database Commands
# ===================================
migrate:
	docker compose exec api python manage.py migrate

makemigrations:
	docker compose exec api python manage.py makemigrations

createsuperuser:
	docker compose exec api python manage.py createsuperuser

collectstatic:
	docker compose exec api python manage.py collectstatic --noinput

# Legacy migration commands (without Docker)
clear_migrate:
	cd api && rm -f db.sqlite3
	cd api && find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	cd api && find . -path "*/migrations/*.pyc" -delete

migrate_local:
	cd api && python manage.py makemigrations
	cd api && python manage.py migrate

clean_migrate:
	make clear_migrate
	make migrate_local

# ===================================
# Testing Commands
# ===================================
test:
	docker compose exec api pytest -v

test-cov:
	docker compose exec api pytest --cov=. --cov-report=html -v

lint:
	docker compose exec api black . --check
	docker compose exec api flake8 .
	docker compose exec api isort . --check-only

format:
	docker compose exec api black .
	docker compose exec api isort .

# ===================================
# Cleanup Commands
# ===================================
clean:
	docker compose down -v --remove-orphans
	docker compose rm -f

prune:
	docker system prune -f
	docker volume prune -f

# ===================================
# AWS ECR Deploy (Legacy)
# ===================================
deploy:
	aws ecr get-login-password --region us-east-2 --profile wise | docker login --username AWS --password-stdin 935364008466.dkr.ecr.us-east-2.amazonaws.com/wisematic/erp-core
	AWS_PROFILE=wise skaffold run

# ===================================
# Health Check
# ===================================
health:
	curl -f http://localhost:8000/api/v1/health/ || echo "Health check failed"

# ===================================
# Docker Hub Commands
# ===================================
docker-login:
	docker login

docker-push:
	docker compose build api
	docker tag autobooks-api:latest $(DOCKER_USERNAME)/autobooks-api:latest
	docker push $(DOCKER_USERNAME)/autobooks-api:latest

docker-pull:
	docker pull $(DOCKER_USERNAME)/autobooks-api:latest
