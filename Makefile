.PHONY: help build up down logs clean test migrate-up migrate-down backend-shell frontend-shell db-shell

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-backend: ## View backend logs
	docker-compose logs -f backend

logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

logs-metric: ## View metric service logs
	docker-compose logs -f metric-service

clean: ## Stop and remove all containers, volumes, and images
	docker-compose down -v
	docker system prune -f

restart: ## Restart all services
	docker-compose restart

restart-backend: ## Restart backend service
	docker-compose restart backend

restart-frontend: ## Restart frontend service
	docker-compose restart frontend

restart-metric: ## Restart metric service
	docker-compose restart metric-service

# Database operations
migrate-up: ## Run database migrations
	docker-compose exec backend alembic upgrade head

migrate-down: ## Rollback last migration
	docker-compose exec backend alembic downgrade -1

migrate-create: ## Create a new migration (usage: make migrate-create MESSAGE="your message")
	docker-compose exec backend alembic revision --autogenerate -m "$(MESSAGE)"

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgres psql -U wanllmdb -d wanllmdb

# Shell access
backend-shell: ## Open shell in backend container
	docker-compose exec backend /bin/bash

frontend-shell: ## Open shell in frontend container
	docker-compose exec frontend /bin/sh

metric-shell: ## Open shell in metric service container
	docker-compose exec metric-service /bin/sh

# Testing
test-backend: ## Run backend tests
	docker-compose exec backend pytest

test-frontend: ## Run frontend tests
	docker-compose exec frontend npm test

test: test-backend test-frontend ## Run all tests

# Code quality
lint-backend: ## Lint backend code
	docker-compose exec backend ruff check app

lint-frontend: ## Lint frontend code
	docker-compose exec frontend npm run lint

format-backend: ## Format backend code
	docker-compose exec backend black app

format-frontend: ## Format frontend code
	docker-compose exec frontend npm run format

# Development
dev: up logs ## Start development environment and show logs

status: ## Show status of all services
	docker-compose ps

# Initial setup
setup: build up migrate-up ## Initial setup: build, start, and migrate
	@echo "Setup complete! Services are running."
	@echo "Frontend: http://localhost:3000"
	@echo "Backend API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Metric Service: http://localhost:8001"
	@echo "MinIO Console: http://localhost:9001"
