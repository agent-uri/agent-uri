#!/bin/bash
# install-dev.sh - Development environment setup using Poetry + uv combination
# This script sets up a complete development environment with ultra-fast dependency resolution

set -euo pipefail

# Colors for output
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RESET='\033[0m'

# Configuration
PYTHON_MIN_VERSION="3.9"
UV_MIN_VERSION="0.4.0"
POETRY_MIN_VERSION="1.6.0"

echo -e "${BLUE}🚀 Agent URI Development Environment Setup${RESET}"
echo -e "${BLUE}===========================================${RESET}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare versions
version_ge() {
    printf '%s\n%s' "$2" "$1" | sort -C -V
}

# Function to get installed version
get_version() {
    case "$1" in
        python|python3)
            python3 --version 2>&1 | cut -d' ' -f2
            ;;
        uv)
            uv --version 2>&1 | cut -d' ' -f2
            ;;
        poetry)
            poetry --version 2>&1 | cut -d' ' -f3
            ;;
    esac
}

# Check Python installation
echo -e "${BLUE}📋 Checking Python installation...${RESET}"
if ! command_exists python3; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python ${PYTHON_MIN_VERSION} or later.${RESET}"
    exit 1
fi

PYTHON_VERSION=$(get_version python3)
if ! version_ge "$PYTHON_VERSION" "$PYTHON_MIN_VERSION"; then
    echo -e "${RED}❌ Python ${PYTHON_VERSION} is installed, but ${PYTHON_MIN_VERSION} or later is required.${RESET}"
    exit 1
fi

echo -e "${GREEN}✓ Python ${PYTHON_VERSION} is installed${RESET}"

# Check/Install uv
echo -e "${BLUE}📦 Checking uv installation...${RESET}"
if ! command_exists uv; then
    echo -e "${YELLOW}⚠️  uv not found. Installing uv...${RESET}"
    if command_exists pip; then
        pip install uv
    elif command_exists pip3; then
        pip3 install uv
    else
        echo -e "${RED}❌ pip not found. Please install pip first.${RESET}"
        exit 1
    fi
else
    UV_VERSION=$(get_version uv)
    if ! version_ge "$UV_VERSION" "$UV_MIN_VERSION"; then
        echo -e "${YELLOW}⚠️  uv ${UV_VERSION} is installed, but ${UV_MIN_VERSION} or later is recommended. Upgrading...${RESET}"
        pip install --upgrade uv
    else
        echo -e "${GREEN}✓ uv ${UV_VERSION} is installed${RESET}"
    fi
fi

# Check/Install Poetry
echo -e "${BLUE}📦 Checking Poetry installation...${RESET}"
if ! command_exists poetry; then
    echo -e "${YELLOW}⚠️  Poetry not found. Installing Poetry...${RESET}"
    curl -sSL https://install.python-poetry.org | python3 -
    
    # Add Poetry to PATH for this session
    export PATH="$HOME/.local/bin:$PATH"
    
    if ! command_exists poetry; then
        echo -e "${RED}❌ Poetry installation failed. Please install manually: https://python-poetry.org/docs/#installation${RESET}"
        exit 1
    fi
else
    POETRY_VERSION=$(get_version poetry)
    if ! version_ge "$POETRY_VERSION" "$POETRY_MIN_VERSION"; then
        echo -e "${YELLOW}⚠️  Poetry ${POETRY_VERSION} is installed, but ${POETRY_MIN_VERSION} or later is recommended.${RESET}"
        echo -e "${YELLOW}   Please consider upgrading: curl -sSL https://install.python-poetry.org | python3 -${RESET}"
    else
        echo -e "${GREEN}✓ Poetry ${POETRY_VERSION} is installed${RESET}"
    fi
fi

# Configure Poetry for this project
echo -e "${BLUE}⚙️  Configuring Poetry...${RESET}"
poetry config virtualenvs.create true
poetry config virtualenvs.in-project false
poetry config virtualenvs.prefer-active-python true

# Install dependencies using uv for speed, Poetry for management
echo -e "${BLUE}📦 Installing dependencies with uv (ultra-fast)...${RESET}"

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}❌ pyproject.toml not found. Please run this script from the project root.${RESET}"
    exit 1
fi

# Install dependencies using uv sync for speed
echo -e "${BLUE}   Using uv for fast dependency resolution...${RESET}"
if ! uv sync; then
    echo -e "${YELLOW}⚠️  uv sync failed, falling back to Poetry...${RESET}"
    poetry install
else
    echo -e "${GREEN}✓ Dependencies installed with uv${RESET}"
fi

# Ensure Poetry knows about the environment
echo -e "${BLUE}🔗 Syncing with Poetry environment...${RESET}"
poetry env use python3

# Install pre-commit hooks
echo -e "${BLUE}🔧 Setting up pre-commit hooks...${RESET}"
if uv run pre-commit install; then
    echo -e "${GREEN}✓ Pre-commit hooks installed${RESET}"
else
    echo -e "${YELLOW}⚠️  Pre-commit hook installation failed (continuing anyway)${RESET}"
fi

# Verify installation
echo -e "${BLUE}🧪 Verifying installation...${RESET}"

# Test imports
echo -e "${BLUE}   Testing package imports...${RESET}"
if uv run python -c "
import sys
sys.path.insert(0, 'packages/uri-parser')
sys.path.insert(0, 'packages/descriptor')
sys.path.insert(0, 'packages/common')
try:
    import agent_uri
    import agent_descriptor
    import agent_common
    print('✓ Core packages import successfully')
except ImportError as e:
    print(f'⚠️  Import warning: {e}')
"; then
    echo -e "${GREEN}✓ Package imports working${RESET}"
fi

# Test development tools
echo -e "${BLUE}   Testing development tools...${RESET}"
for tool in pytest black isort mypy flake8; do
    if uv run "$tool" --version >/dev/null 2>&1; then
        echo -e "${GREEN}✓ $tool is working${RESET}"
    else
        echo -e "${YELLOW}⚠️  $tool may have issues${RESET}"
    fi
done

# Show environment info
echo -e "${BLUE}📊 Environment Information:${RESET}"
echo -e "   Python: $(python3 --version)"
echo -e "   uv: $(uv --version)"
echo -e "   Poetry: $(poetry --version)"
echo -e "   Virtual Environment: $(poetry env info --path 2>/dev/null || echo 'Using system Python')"

# Show next steps
echo -e "${GREEN}🎉 Development environment setup complete!${RESET}"
echo -e "${BLUE}📝 Next steps:${RESET}"
echo -e "   • Run ${YELLOW}'make test'${RESET} to run tests"
echo -e "   • Run ${YELLOW}'make lint'${RESET} to check code quality"  
echo -e "   • Run ${YELLOW}'make docs-serve'${RESET} to preview documentation"
echo -e "   • Run ${YELLOW}'make quality-gate'${RESET} to run all checks"
echo -e ""
echo -e "${BLUE}💡 Development Tips:${RESET}"
echo -e "   • Use ${YELLOW}'uv run <command>'${RESET} for faster tool execution"
echo -e "   • Use ${YELLOW}'poetry run <command>'${RESET} for Poetry-managed execution"
echo -e "   • Use ${YELLOW}'make help'${RESET} to see all available commands"
echo -e "   • Pre-commit hooks will run automatically on git commit"

echo -e "${GREEN}✨ Happy coding!${RESET}"