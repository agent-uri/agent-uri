# Agent URI Development Scripts

This directory contains automation scripts for the Agent URI project that implement the modern build system using Poetry + uv combination for ultra-fast dependency management and build automation.

## Scripts Overview

### 🚀 install-dev.sh
**Purpose**: Complete development environment setup with Poetry + uv combination

**Features**:
- Automatically installs uv and Poetry if not present
- Ultra-fast dependency resolution using uv
- Sets up pre-commit hooks
- Validates package imports
- Provides environment information

**Usage**:
```bash
./scripts/install-dev.sh
```

**Benefits**:
- 10-100x faster dependency resolution with uv
- Consistent dependency versions across packages with Poetry
- Automated development environment setup

### 🧪 test-all.sh
**Purpose**: Comprehensive testing across all agent-uri packages

**Features**:
- Discovers and tests all packages automatically
- Supports unit, integration, e2e, and performance tests
- Generates coverage reports
- Configurable test timeouts and parallel execution
- Tests examples and standalone scripts

**Usage**:
```bash
# Run all tests
./scripts/test-all.sh

# Run specific test types
./scripts/test-all.sh unit
./scripts/test-all.sh integration
./scripts/test-all.sh coverage
```

**Environment Variables**:
- `PARALLEL_JOBS`: Number of parallel test jobs (default: auto)
- `COVERAGE_THRESHOLD`: Minimum coverage percentage (default: 80)
- `TEST_TIMEOUT`: Test timeout in seconds (default: 300)

### 🔍 lint-all.sh
**Purpose**: Comprehensive code quality and linting checks

**Features**:
- Black code formatting (with auto-fix support)
- isort import sorting (with auto-fix support)
- flake8 PEP8 compliance checking
- mypy type checking
- bandit security scanning
- safety dependency vulnerability checking
- Package structure validation
- Pre-commit hooks execution

**Usage**:
```bash
# Check mode (default)
./scripts/lint-all.sh

# Fix mode (auto-format code)
./scripts/lint-all.sh fix

# Strict mode (additional checks)
./scripts/lint-all.sh strict
```

**Environment Variables**:
- `FIX_MODE`: Enable auto-fixing (default: false)
- `STRICT_MODE`: Enable additional strict checks (default: false)

### 📦 build-packages.sh
**Purpose**: Build and publish all agent-uri packages

**Features**:
- Validates package structure before building
- Runs tests before building (configurable)
- Builds with Poetry or setuptools
- Verifies built packages
- Supports publishing to PyPI or Test PyPI
- Generates build reports

**Usage**:
```bash
# Build only
./scripts/build-packages.sh

# Build and publish to Test PyPI
./scripts/build-packages.sh --publish --test-pypi

# Build wheels only (faster)
./scripts/build-packages.sh --wheels-only

# Skip tests for faster builds
./scripts/build-packages.sh --skip-tests
```

**Options**:
- `--publish`: Publish packages after building
- `--test-pypi`: Use Test PyPI instead of production
- `--skip-tests`: Skip running tests before building
- `--wheels-only`: Build only wheel distributions

## Integration with Makefile

All scripts are integrated with the project Makefile for convenient access:

```bash
# Development setup
make install-dev    # Runs install-dev.sh
make dev-setup      # Complete setup with pre-commit hooks

# Testing
make test          # Quick tests
make test-all      # Runs test-all.sh
make test-coverage # Tests with coverage

# Code quality
make lint          # Runs lint-all.sh
make format        # Auto-format code
make quality-gate  # Complete quality checks

# Building
make build         # Runs build-packages.sh
make publish       # Build and publish
```

## Tool Combination Strategy

The scripts implement the following strategy for optimal performance:

- **uv**: Ultra-fast dependency resolution and virtual environment creation (10-100x faster)
- **Poetry**: Project/dependency management, packaging, and publishing (best-in-class)
- **Workflow**: Use `uv` for speed during development, `poetry` for packaging and publishing

## Dependencies

### Required Tools
- Python 3.9+
- uv 0.4.0+
- Poetry 1.6.0+

### Development Tools (installed automatically)
- pytest (testing)
- black (code formatting)
- isort (import sorting)
- flake8 (linting)
- mypy (type checking)
- bandit (security scanning)
- safety (dependency scanning)
- pre-commit (git hooks)

## Project Structure

The scripts work with the following package structure:

```
agent-uri/
├── pyproject.toml          # Unified Poetry configuration
├── Makefile               # Development commands
├── scripts/               # This directory
│   ├── install-dev.sh     # Development setup
│   ├── test-all.sh        # Testing automation
│   ├── lint-all.sh        # Code quality checks
│   └── build-packages.sh  # Build and publish
└── packages/              # Package modules
    ├── uri-parser/        # Agent URI parser
    ├── descriptor/        # Agent descriptor handling
    ├── resolver/          # URI resolution
    ├── transport/         # Transport layer
    ├── client/            # Client implementation
    ├── server/            # Server implementation
    └── common/            # Common utilities
```

## Benefits

### Performance
- **Ultra-fast dependency resolution**: 10-100x faster with uv
- **Parallel testing**: Automatic parallel test execution
- **Efficient builds**: Optimized build processes with caching

### Developer Experience
- **One-command setup**: Complete environment setup with single script
- **Comprehensive automation**: All development tasks automated
- **Clear feedback**: Colored output and progress indicators
- **Error handling**: Robust error handling and recovery

### Quality Assurance
- **Automated quality checks**: Comprehensive linting and testing
- **Security scanning**: Automated vulnerability detection
- **Package validation**: Structure and dependency validation
- **Coverage reporting**: Detailed test coverage analysis

## Troubleshooting

### Common Issues

1. **uv not found**: Install with `pip install uv`
2. **Poetry not found**: Install from https://python-poetry.org/docs/#installation
3. **Permission errors**: Ensure scripts are executable (`chmod +x scripts/*.sh`)
4. **Import errors**: Run `make install-dev` to set up dependencies

### Getting Help

```bash
# Show available commands
make help

# Script-specific help
./scripts/build-packages.sh --help
```

## Next Steps

After setting up the development environment:

1. Run `make dev-setup` for complete setup
2. Run `make test` to verify everything works
3. Run `make lint` to check code quality
4. Run `make docs-serve` to preview documentation
5. Run `make quality-gate` before committing changes

This modern build system provides the foundation for scaling the agent-uri project while maintaining high code quality and developer productivity.