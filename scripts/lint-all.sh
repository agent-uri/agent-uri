#!/bin/bash
# lint-all.sh - Comprehensive code quality and linting script
# Runs all linting tools with proper configuration and reporting

set -euo pipefail

# Colors for output
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RESET='\033[0m'

# Configuration
FIX_MODE=${FIX_MODE:-false}
STRICT_MODE=${STRICT_MODE:-false}
PARALLEL=${PARALLEL:-true}

echo -e "${BLUE}🔍 Agent URI Code Quality Suite${RESET}"
echo -e "${BLUE}===============================${RESET}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run a linting tool with proper error handling
run_linter() {
    local tool_name="$1"
    local command="$2"
    local description="$3"
    local fix_available="${4:-false}"

    echo -e "${BLUE}🔧 Running $description...${RESET}"

    if [ "$FIX_MODE" = "true" ] && [ "$fix_available" = "true" ]; then
        echo -e "${YELLOW}   (Fix mode enabled)${RESET}"
    fi

    if eval "$command"; then
        echo -e "${GREEN}✓ $tool_name passed${RESET}"
        return 0
    else
        echo -e "${RED}❌ $tool_name failed${RESET}"
        return 1
    fi
}

# Function to check code formatting with Black
check_black() {
    local fix_flag=""
    if [ "$FIX_MODE" = "true" ]; then
        fix_flag=""
    else
        fix_flag="--check --diff"
    fi

    run_linter "Black" \
        "uv run black $fix_flag agent_uri/ examples/ scripts/" \
        "Black code formatting" \
        "true"
}

# Function to check import sorting with isort
check_isort() {
    local fix_flag=""
    if [ "$FIX_MODE" = "true" ]; then
        fix_flag=""
    else
        fix_flag="--check-only --diff"
    fi

    run_linter "isort" \
        "uv run isort $fix_flag agent_uri/ examples/ scripts/" \
        "Import sorting with isort" \
        "true"
}

# Function to run flake8 linting
check_flake8() {
    run_linter "flake8" \
        "uv run flake8 agent_uri/ examples/ scripts/" \
        "PEP8 compliance with flake8" \
        "false"
}

# Function to run mypy type checking
check_mypy() {
    local strict_flag=""
    if [ "$STRICT_MODE" = "true" ]; then
        strict_flag="--strict"
    fi

    run_linter "mypy" \
        "uv run mypy $strict_flag agent_uri/" \
        "Type checking with mypy" \
        "false"
}

# Function to run bandit security checks
check_bandit() {
    run_linter "bandit" \
        "uv run bandit -r agent_uri/ -f json -o bandit-report.json || uv run bandit -r agent_uri/" \
        "Security scanning with bandit" \
        "false"
}

# Function to run safety dependency checks
check_safety() {
    run_linter "safety" \
        "uv run safety check --json --output safety-report.json || uv run safety check" \
        "Dependency vulnerability scanning with safety" \
        "false"
}

# Function to check docstring quality
check_docstrings() {
    if command_exists pydocstyle || uv run pydocstyle --version >/dev/null 2>&1; then
        run_linter "pydocstyle" \
            "uv run pydocstyle agent_uri/" \
            "Docstring quality with pydocstyle" \
            "false"
    else
        echo -e "${YELLOW}⚠️  pydocstyle not available, skipping docstring checks${RESET}"
    fi
}

# Function to check complexity
check_complexity() {
    if command_exists mccabe || uv run python -c "import mccabe" 2>/dev/null; then
        run_linter "mccabe" \
            "uv run python -m mccabe --min 10 agent_uri/" \
            "Cyclomatic complexity with mccabe" \
            "false"
    else
        echo -e "${YELLOW}⚠️  mccabe not available, skipping complexity checks${RESET}"
    fi
}

# Function to check for dead code
check_vulture() {
    if command_exists vulture || uv run vulture --version >/dev/null 2>&1; then
        run_linter "vulture" \
            "uv run vulture agent_uri/ --min-confidence 80" \
            "Dead code detection with vulture" \
            "false"
    else
        echo -e "${YELLOW}⚠️  vulture not available, skipping dead code checks${RESET}"
    fi
}

# Function to run pre-commit hooks
check_precommit() {
    if [ -f ".pre-commit-config.yaml" ]; then
        run_linter "pre-commit" \
            "uv run pre-commit run --all-files" \
            "Pre-commit hooks" \
            "true"
    else
        echo -e "${YELLOW}⚠️  No .pre-commit-config.yaml found, skipping pre-commit checks${RESET}"
    fi
}

# Function to check package structure
check_package_structure() {
    echo -e "${BLUE}🏗️  Checking package structure...${RESET}"

    # Package structure now uses single unified agent_uri package
    local packages=(
        "agent_uri"
    )

    local structure_issues=0

    for package in "${packages[@]}"; do
        if [ -d "$package" ]; then
            echo -e "${BLUE}   Checking $package...${RESET}"

            # Check for __init__.py
            if [ ! -f "$package/__init__.py" ]; then
                echo -e "${YELLOW}     ⚠️  Missing __init__.py${RESET}"
                ((structure_issues++))
            fi

            # Check for tests
            if [ ! -d "$package/tests" ]; then
                echo -e "${YELLOW}     ⚠️  Missing tests directory${RESET}"
                ((structure_issues++))
            fi

            # Check for pyproject.toml (root level for unified package)
            if [ ! -f "pyproject.toml" ]; then
                echo -e "${YELLOW}     ⚠️  Missing pyproject.toml${RESET}"
                ((structure_issues++))
            fi

        else
            echo -e "${RED}     ❌ Package directory $package not found${RESET}"
            ((structure_issues++))
        fi
    done

    if [ $structure_issues -eq 0 ]; then
        echo -e "${GREEN}✓ Package structure looks good${RESET}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Found $structure_issues package structure issues${RESET}"
        return 1
    fi
}

# Function to generate lint report
generate_report() {
    echo -e "${BLUE}📊 Generating lint report...${RESET}"

    local report_file="lint-report.txt"
    local json_report="lint-report.json"

    {
        echo "Agent URI Code Quality Report"
        echo "Generated: $(date)"
        echo "=============================="
        echo ""

        if [ -f "bandit-report.json" ]; then
            echo "Security Issues (Bandit):"
            jq -r '.results[] | "- \(.test_name): \(.issue_text)"' bandit-report.json 2>/dev/null || echo "Error parsing bandit report"
            echo ""
        fi

        if [ -f "safety-report.json" ]; then
            echo "Dependency Vulnerabilities (Safety):"
            jq -r '.[] | "- \(.package): \(.vulnerability)"' safety-report.json 2>/dev/null || echo "Error parsing safety report"
            echo ""
        fi

    } > "$report_file"

    echo -e "${GREEN}✓ Report generated: $report_file${RESET}"
}

# Function to clean up temporary files
cleanup() {
    rm -f bandit-report.json safety-report.json 2>/dev/null || true
}

# Main function
main() {
    local mode="${1:-check}"
    local failed_checks=0
    local total_checks=0

    # Parse arguments
    case "$mode" in
        "fix")
            FIX_MODE=true
            echo -e "${YELLOW}🔧 Running in fix mode${RESET}"
            ;;
        "strict")
            STRICT_MODE=true
            echo -e "${YELLOW}🔒 Running in strict mode${RESET}"
            ;;
        "check"|*)
            echo -e "${BLUE}🔍 Running in check mode${RESET}"
            ;;
    esac

    # Check dependencies
    if ! command_exists uv; then
        echo -e "${RED}❌ uv not found. Please install uv first.${RESET}"
        exit 1
    fi

    echo -e "${BLUE}🎯 Mode: $mode${RESET}"
    echo -e "${BLUE}🔧 Fix mode: $FIX_MODE${RESET}"
    echo -e "${BLUE}🔒 Strict mode: $STRICT_MODE${RESET}"
    echo ""

    # Run all checks
    local checks=(
        "check_black"
        "check_isort"
        "check_flake8"
        "check_mypy"
        "check_bandit"
        "check_safety"
        "check_package_structure"
        "check_precommit"
    )

    # Optional checks
    if [ "$STRICT_MODE" = "true" ]; then
        checks+=("check_docstrings" "check_complexity" "check_vulture")
    fi

    for check in "${checks[@]}"; do
        ((total_checks++))
        echo ""
        if ! $check; then
            ((failed_checks++))
        fi
    done

    # Generate report
    echo ""
    generate_report

    # Cleanup
    cleanup

    # Summary
    echo ""
    echo -e "${BLUE}📈 Summary${RESET}"
    echo -e "   Total checks: $total_checks"
    echo -e "   Failed checks: $failed_checks"
    echo -e "   Success rate: $((100 * (total_checks - failed_checks) / total_checks))%"

    if [ $failed_checks -eq 0 ]; then
        echo -e "${GREEN}🎉 All linting checks passed!${RESET}"
        if [ "$FIX_MODE" = "true" ]; then
            echo -e "${BLUE}💡 Code has been automatically formatted where possible${RESET}"
        fi
        exit 0
    else
        echo -e "${RED}❌ $failed_checks linting check(s) failed${RESET}"
        if [ "$FIX_MODE" = "false" ]; then
            echo -e "${BLUE}💡 Try running with 'fix' mode: ./scripts/lint-all.sh fix${RESET}"
        fi
        exit 1
    fi
}

# Handle script arguments
main "$@"
