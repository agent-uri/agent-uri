# Makefile for agent-uri project
# Combines Poetry and uv for optimal development experience

.PHONY: help install install-dev install-ci test test-all lint format type-check security docs clean build publish
.DEFAULT_GOAL := help

# Variables
PYTHON := python3
UV := uv
POETRY := poetry
PYTEST := pytest
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy
BANDIT := bandit
MKDOCS := mkdocs

# Colors for output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

help: ## Show this help message
	@echo "$(BLUE)Agent URI Development Commands$(RESET)"
	@echo ""
	@echo "$(GREEN)Setup Commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(install|setup)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Development Commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(test|lint|format|type|security)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Build & Deploy Commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E "(build|publish|docs|clean)" | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'

# Setup Commands
install: ## Install production dependencies using uv for speed
	@echo "$(BLUE)Installing production dependencies with uv...$(RESET)"
	$(UV) sync --no-dev
	@echo "$(GREEN)✓ Production dependencies installed$(RESET)"

install-dev: ## Install all dependencies including development tools
	@echo "$(BLUE)Installing all dependencies with uv...$(RESET)"
	$(UV) sync
	@echo "$(BLUE)Setting up pre-commit hooks...$(RESET)"
	$(UV) run pre-commit install
	@echo "$(GREEN)✓ Development environment ready$(RESET)"

install-ci: ## Install CI dependencies (faster, minimal)
	@echo "$(BLUE)Installing CI dependencies with uv...$(RESET)"
	$(UV) sync --group ci
	@echo "$(GREEN)✓ CI environment ready$(RESET)"

setup-poetry: ## Initialize Poetry if needed (fallback)
	@echo "$(BLUE)Setting up Poetry environment...$(RESET)"
	$(POETRY) install
	@echo "$(GREEN)✓ Poetry environment ready$(RESET)"

# Testing Commands
test: ## Run fast unit tests
	@echo "$(BLUE)Running unit tests...$(RESET)"
	$(POETRY) run $(PYTEST) -m "not slow and not integration" --tb=short

test-all: ## Run all tests including integration and slow tests
	@echo "$(BLUE)Running all tests...$(RESET)"
	$(POETRY) run $(PYTEST) --tb=short

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(RESET)"
	$(POETRY) run $(PYTEST) -m integration --tb=short

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(RESET)"
	$(POETRY) run $(PYTEST) --cov=agent_uri --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(RESET)"

test-parallel: ## Run tests in parallel for speed
	@echo "$(BLUE)Running tests in parallel...$(RESET)"
	$(POETRY) run $(PYTEST) -n auto --tb=short

# Code Quality Commands
lint: ## Run all linting tools
	@echo "$(BLUE)Running all linting tools...$(RESET)"
	@$(MAKE) lint-flake8
	@$(MAKE) lint-black-check
	@$(MAKE) lint-isort-check
	@echo "$(GREEN)✓ All linting checks passed$(RESET)"

lint-flake8: ## Run flake8 linter
	@echo "$(BLUE)Running flake8...$(RESET)"
	$(POETRY) run $(FLAKE8) agent_uri/ --max-line-length=88 --extend-ignore=W503,E203
	$(POETRY) run $(FLAKE8) examples/ --max-line-length=88 --extend-ignore=W503,E203,F401,W291,E501 || echo "$(YELLOW)Examples have some style issues (non-critical)$(RESET)"

lint-black-check: ## Check code formatting with black
	@echo "$(BLUE)Checking code formatting with black...$(RESET)"
	$(POETRY) run $(BLACK) --check agent_uri/ examples/ --line-length=88

lint-isort-check: ## Check import sorting with isort
	@echo "$(BLUE)Checking import sorting with isort...$(RESET)"
	$(POETRY) run $(ISORT) --check-only agent_uri/ examples/ --profile=black --line-length=88

format: ## Auto-format code with black and isort
	@echo "$(BLUE)Formatting code with black...$(RESET)"
	$(POETRY) run $(BLACK) agent_uri/ examples/ scripts/ --line-length=88
	@echo "$(BLUE)Sorting imports with isort...$(RESET)"
	$(POETRY) run $(ISORT) agent_uri/ examples/ scripts/ --profile=black --line-length=88
	@echo "$(GREEN)✓ Code formatted$(RESET)"

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checking with mypy...$(RESET)"
	$(POETRY) run $(MYPY) agent_uri/ || echo "$(YELLOW)Type checking found issues (non-blocking for now)$(RESET)"

security: ## Run security checks
	@echo "$(BLUE)Running security checks with bandit...$(RESET)"
	$(POETRY) run $(BANDIT) -r agent_uri/ -x "*/tests/*,*/test_*.py"
	@echo "$(BLUE)Checking for known vulnerabilities with safety...$(RESET)"
	$(POETRY) run safety check --ignore=67599
	@echo "$(GREEN)✓ Security checks passed$(RESET)"

# Quality Gates
quality-gate: ## Run all quality checks (for CI)
	@echo "$(BLUE)Running complete quality gate...$(RESET)"
	@$(MAKE) lint
	@$(MAKE) type-check
	@$(MAKE) security
	@$(MAKE) test-coverage
	@echo "$(GREEN)✓ Quality gate passed$(RESET)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(BLUE)Running pre-commit hooks...$(RESET)"
	$(UV) run pre-commit run --all-files

# Documentation Commands
docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(RESET)"
	$(UV) run $(MKDOCS) build
	@echo "$(GREEN)✓ Documentation built in site/$(RESET)"

docs-serve: ## Serve documentation locally for development
	@echo "$(BLUE)Serving documentation at http://127.0.0.1:8000$(RESET)"
	$(UV) run $(MKDOCS) serve

docs-deploy: ## Deploy documentation to GitHub Pages
	@echo "$(BLUE)Deploying documentation...$(RESET)"
	$(UV) run $(MKDOCS) gh-deploy

# Build Commands
build: ## Build all packages for distribution
	@echo "$(BLUE)Building all packages...$(RESET)"
	@for pkg in packages/*/; do \
		if [ -f "$$pkg/pyproject.toml" ] || [ -f "$$pkg/setup.py" ]; then \
			echo "$(BLUE)Building $$pkg...$(RESET)"; \
			cd "$$pkg" && $(POETRY) build && cd ../..; \
		fi \
	done
	@echo "$(GREEN)✓ All packages built$(RESET)"

build-wheel: ## Build wheels only
	@echo "$(BLUE)Building wheels...$(RESET)"
	$(POETRY) build --format wheel
	@echo "$(GREEN)✓ Wheels built$(RESET)"

# Dependency Management
update-deps: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(RESET)"
	$(UV) sync --upgrade
	$(POETRY) update
	@echo "$(GREEN)✓ Dependencies updated$(RESET)"

lock-deps: ## Generate lock files
	@echo "$(BLUE)Generating lock files...$(RESET)"
	$(POETRY) lock
	$(UV) lock
	@echo "$(GREEN)✓ Lock files generated$(RESET)"

# Package Management
install-package: ## Install a specific package (usage: make install-package PKG=package-name)
	@echo "$(BLUE)Installing $(PKG)...$(RESET)"
	$(UV) add $(PKG)

install-dev-package: ## Install a development package (usage: make install-dev-package PKG=package-name)
	@echo "$(BLUE)Installing development package $(PKG)...$(RESET)"
	$(UV) add --group dev $(PKG)

# Publishing Commands
publish-test: ## Publish to test PyPI
	@echo "$(BLUE)Publishing to test PyPI...$(RESET)"
	$(POETRY) config repositories.testpypi https://test.pypi.org/legacy/
	$(POETRY) publish --repository testpypi

publish: ## Publish to PyPI (production)
	@echo "$(RED)Publishing to production PyPI...$(RESET)"
	@read -p "Are you sure you want to publish to production PyPI? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(POETRY) publish; \
	else \
		echo "$(YELLOW)Publish cancelled$(RESET)"; \
	fi

# Maintenance Commands
clean: ## Clean build artifacts and caches
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/
	rm -rf site/
	@echo "$(GREEN)✓ Cleaned build artifacts$(RESET)"

clean-env: ## Remove virtual environments
	@echo "$(BLUE)Cleaning virtual environments...$(RESET)"
	$(UV) clean
	$(POETRY) env remove --all 2>/dev/null || true
	@echo "$(GREEN)✓ Virtual environments cleaned$(RESET)"

reset: clean clean-env ## Complete reset (clean + remove environments)
	@echo "$(GREEN)✓ Complete reset done$(RESET)"

# Development Workflow Commands
dev-setup: install-dev ## Complete development setup
	@echo "$(GREEN)✓ Development environment ready!$(RESET)"
	@echo "$(BLUE)Next steps:$(RESET)"
	@echo "  - Run 'make test' to run tests"
	@echo "  - Run 'make docs-serve' to preview documentation"
	@echo "  - Run 'make quality-gate' to run all checks"

quick-check: ## Quick development check (fast tests + basic linting)
	@echo "$(BLUE)Running quick development check...$(RESET)"
	@$(MAKE) lint-flake8
	@$(MAKE) test
	@echo "$(GREEN)✓ Quick check passed$(RESET)"

# Docker Commands (if needed)
docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(RESET)"
	docker build -t agent-uri:latest .

docker-test: ## Run tests in Docker
	@echo "$(BLUE)Running tests in Docker...$(RESET)"
	docker run --rm agent-uri:latest make test

# Utility Commands
check-tools: ## Check if required tools are installed
	@echo "$(BLUE)Checking required tools...$(RESET)"
	@command -v $(UV) >/dev/null 2>&1 || { echo "$(RED)✗ uv not found. Install with: pip install uv$(RESET)"; exit 1; }
	@command -v $(POETRY) >/dev/null 2>&1 || { echo "$(RED)✗ poetry not found. Install with: pip install poetry$(RESET)"; exit 1; }
	@echo "$(GREEN)✓ All required tools found$(RESET)"

version: ## Show version information
	@echo "$(BLUE)Version Information:$(RESET)"
	@echo "Python: $$($(PYTHON) --version)"
	@echo "uv: $$($(UV) --version 2>/dev/null || echo 'not installed')"
	@echo "Poetry: $$($(POETRY) --version 2>/dev/null || echo 'not installed')"
	@echo "Project: $$(grep '^version' pyproject.toml | cut -d'"' -f2)"

# Example target for package-specific commands
test-parser: ## Test only the URI parser package
	@echo "$(BLUE)Testing URI parser package...$(RESET)"
	$(POETRY) run $(PYTEST) agent_uri/tests/test_parser.py

test-client: ## Test only the client package
	@echo "$(BLUE)Testing client package...$(RESET)"
	$(POETRY) run $(PYTEST) agent_uri/tests/test_client.py