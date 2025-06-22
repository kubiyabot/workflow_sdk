# Kubiya Workflow SDK Makefile
.PHONY: help install dev test lint format docs server docker clean

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
PIP := $(PYTHON) -m pip
PYTEST := $(PYTHON) -m pytest
BLACK := $(PYTHON) -m black
RUFF := $(PYTHON) -m ruff
DOCKER_IMAGE := kubiya-sdk-server
DOCKER_TAG := latest

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Kubiya Workflow SDK - Development Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Install the SDK with basic dependencies
	$(PIP) install -e .
	@echo "$(GREEN)✓ SDK installed successfully$(NC)"

install-all: ## Install the SDK with all features (ADK, server, etc.)
	$(PIP) install -e ".[all]"
	@echo "$(GREEN)✓ SDK installed with all features$(NC)"

install-dev: ## Install development dependencies
	$(PIP) install -e ".[dev]"
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

dev: install-dev ## Set up complete development environment
	pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(NC)"

test: ## Run all tests
	$(PYTEST) tests/ -v --cov=kubiya_workflow_sdk --cov-report=term-missing

test-unit: ## Run unit tests only
	$(PYTEST) tests/unit -v

test-integration: ## Run integration tests
	$(PYTEST) tests/integration -v

test-e2e: ## Run end-to-end tests
	$(PYTEST) test_server_e2e.py -v

lint: ## Run linting checks
	$(RUFF) check kubiya_workflow_sdk tests
	$(BLACK) --check kubiya_workflow_sdk tests

format: ## Format code with black
	$(BLACK) kubiya_workflow_sdk tests
	$(RUFF) check --fix kubiya_workflow_sdk tests
	@echo "$(GREEN)✓ Code formatted$(NC)"

type-check: ## Run type checking with mypy
	mypy kubiya_workflow_sdk --ignore-missing-imports

server: ## Start the SDK server locally
	@echo "$(BLUE)Starting Kubiya SDK Server...$(NC)"
	python -m kubiya_workflow_sdk.server --reload

server-prod: ## Start server in production mode
	python -m kubiya_workflow_sdk.server --host 0.0.0.0 --port 8000

docker-build: ## Build Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .
	@echo "$(GREEN)✓ Docker image built: $(DOCKER_IMAGE):$(DOCKER_TAG)$(NC)"

docker-run: ## Run Docker container
	docker run -p 8000:8000 \
		-e KUBIYA_API_KEY=$$KUBIYA_API_KEY \
		-e TOGETHER_API_KEY=$$TOGETHER_API_KEY \
		$(DOCKER_IMAGE):$(DOCKER_TAG)

docker-compose-up: ## Start services with docker-compose
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "$(BLUE)Server: http://localhost:8000$(NC)"
	@echo "$(BLUE)Health: http://localhost:8000/health$(NC)"

docker-compose-down: ## Stop docker-compose services
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-compose-logs: ## Show docker-compose logs
	docker-compose logs -f

docs-serve: ## Serve documentation locally
	@echo "$(BLUE)Starting documentation server...$(NC)"
	cd docs/kubiya && mintlify dev

docs-build: ## Build documentation
	cd docs/kubiya && mintlify build

notebook: ## Start Jupyter notebook server
	jupyter notebook examples/notebooks/

example-basic: ## Run basic workflow example
	python examples/basic_workflow.py

example-ai: ## Run AI workflow generation example
	python examples/ai_workflow_generation.py

clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	@echo "$(GREEN)✓ Cleaned up generated files$(NC)"

env-check: ## Check environment variables
	@echo "$(BLUE)Environment Check:$(NC)"
	@[ -n "$$KUBIYA_API_KEY" ] && echo "$(GREEN)✓ KUBIYA_API_KEY is set$(NC)" || echo "$(RED)✗ KUBIYA_API_KEY is not set$(NC)"
	@[ -n "$$TOGETHER_API_KEY" ] && echo "$(GREEN)✓ TOGETHER_API_KEY is set$(NC)" || echo "$(YELLOW)⚠ TOGETHER_API_KEY is not set (optional)$(NC)"
	@[ -n "$$GOOGLE_API_KEY" ] && echo "$(GREEN)✓ GOOGLE_API_KEY is set$(NC)" || echo "$(YELLOW)⚠ GOOGLE_API_KEY is not set (optional)$(NC)"

setup-env: ## Copy env.example to .env
	@if [ ! -f .env ]; then \
		cp env.example .env; \
		echo "$(GREEN)✓ Created .env file from env.example$(NC)"; \
		echo "$(YELLOW)⚠ Please edit .env and add your API keys$(NC)"; \
	else \
		echo "$(YELLOW)⚠ .env already exists$(NC)"; \
	fi

release: ## Create a new release
	@echo "$(BLUE)Creating new release...$(NC)"
	@read -p "Version (e.g., 2.0.1): " version; \
	git tag -a v$$version -m "Release v$$version"; \
	git push origin v$$version; \
	echo "$(GREEN)✓ Released v$$version$(NC)"

version: ## Show current version
	@python -c "from kubiya_workflow_sdk import __version__; print(__version__)"

.PHONY: help install install-all install-dev dev test test-unit test-integration test-e2e
.PHONY: lint format type-check server server-prod docker-build docker-run
.PHONY: docker-compose-up docker-compose-down docker-compose-logs
.PHONY: docs-serve docs-build notebook example-basic example-ai
.PHONY: clean env-check setup-env release version 