#!/bin/bash
# test-all.sh - Comprehensive testing script for all agent-uri packages
# Runs tests across all packages with proper isolation and reporting

set -euo pipefail

# Colors for output
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RESET='\033[0m'

# Configuration
PARALLEL_JOBS=${PARALLEL_JOBS:-auto}
COVERAGE_THRESHOLD=${COVERAGE_THRESHOLD:-80}
TEST_TIMEOUT=${TEST_TIMEOUT:-300}

echo -e "${BLUE}🧪 Agent URI Test Suite${RESET}"
echo -e "${BLUE}======================${RESET}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run tests for a specific package
run_package_tests() {
    local package_path="$1"
    local package_name="$2"

    echo -e "${BLUE}📦 Testing $package_name...${RESET}"

    if [ ! -d "$package_path/tests" ] && [ ! -d "$package_path/$package_name/tests" ]; then
        echo -e "${YELLOW}⚠️  No tests found for $package_name, skipping...${RESET}"
        return 0
    fi

    # Determine test directory
    local test_dir=""
    if [ -d "$package_path/tests" ]; then
        test_dir="$package_path/tests"
    elif [ -d "$package_path/$package_name/tests" ]; then
        test_dir="$package_path/$package_name/tests"
    fi

    if [ -n "$test_dir" ]; then
        echo -e "${BLUE}   Running tests in $test_dir...${RESET}"
        if ! uv run pytest "$test_dir" -v --tb=short --timeout="$TEST_TIMEOUT"; then
            echo -e "${RED}❌ Tests failed for $package_name${RESET}"
            return 1
        else
            echo -e "${GREEN}✓ Tests passed for $package_name${RESET}"
        fi
    fi

    return 0
}

# Function to discover and test all packages
test_all_packages() {
    local failed_packages=()
    local tested_packages=()

    echo -e "${BLUE}🔍 Discovering packages...${RESET}"

    # Define packages to test
    local packages=(
        "packages/uri-parser:agent_uri"
        "packages/descriptor:agent_descriptor"
        "packages/resolver:agent_resolver"
        "packages/transport:agent_transport"
        "packages/client:agent_client"
        "packages/server:agent_server"
        "packages/common:agent_common"
    )

    for package_info in "${packages[@]}"; do
        IFS=':' read -r package_path package_name <<< "$package_info"

        if [ -d "$package_path" ]; then
            tested_packages+=("$package_name")
            if ! run_package_tests "$package_path" "$package_name"; then
                failed_packages+=("$package_name")
            fi
        else
            echo -e "${YELLOW}⚠️  Package directory $package_path not found, skipping...${RESET}"
        fi
    done

    # Test examples
    if [ -d "examples" ]; then
        echo -e "${BLUE}📚 Testing examples...${RESET}"
        for example_dir in examples/*/; do
            if [ -d "$example_dir" ] && [ -f "$example_dir/tests.py" ]; then
                example_name=$(basename "$example_dir")
                echo -e "${BLUE}   Testing example: $example_name...${RESET}"
                tested_packages+=("example:$example_name")
                if ! (cd "$example_dir" && uv run python tests.py); then
                    failed_packages+=("example:$example_name")
                    echo -e "${RED}❌ Example tests failed for $example_name${RESET}"
                else
                    echo -e "${GREEN}✓ Example tests passed for $example_name${RESET}"
                fi
            fi
        done
    fi

    # Report results
    echo -e "${BLUE}📊 Test Results Summary${RESET}"
    echo -e "   Packages tested: ${#tested_packages[@]}"
    echo -e "   Packages failed: ${#failed_packages[@]}"

    if [ ${#failed_packages[@]} -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed!${RESET}"
        return 0
    else
        echo -e "${RED}❌ Failed packages:${RESET}"
        for package in "${failed_packages[@]}"; do
            echo -e "${RED}   • $package${RESET}"
        done
        return 1
    fi
}

# Function to run integration tests
run_integration_tests() {
    echo -e "${BLUE}🔗 Running integration tests...${RESET}"

    if [ -d "tests/integration" ]; then
        if ! uv run pytest tests/integration/ -v --tb=short -m integration; then
            echo -e "${RED}❌ Integration tests failed${RESET}"
            return 1
        else
            echo -e "${GREEN}✓ Integration tests passed${RESET}"
        fi
    else
        echo -e "${YELLOW}⚠️  No integration tests found${RESET}"
    fi

    return 0
}

# Function to run end-to-end tests
run_e2e_tests() {
    echo -e "${BLUE}🌐 Running end-to-end tests...${RESET}"

    if [ -d "tests/e2e" ]; then
        if ! uv run pytest tests/e2e/ -v --tb=short -m e2e; then
            echo -e "${RED}❌ End-to-end tests failed${RESET}"
            return 1
        else
            echo -e "${GREEN}✓ End-to-end tests passed${RESET}"
        fi
    else
        echo -e "${YELLOW}⚠️  No end-to-end tests found${RESET}"
    fi

    return 0
}

# Function to generate coverage report
generate_coverage() {
    echo -e "${BLUE}📈 Generating coverage report...${RESET}"

    if ! uv run pytest --cov=packages --cov-report=html --cov-report=term --cov-report=xml; then
        echo -e "${RED}❌ Coverage generation failed${RESET}"
        return 1
    fi

    # Check coverage threshold
    local coverage_percent
    coverage_percent=$(uv run coverage report --format=total 2>/dev/null || echo "0")

    if [ "$coverage_percent" -ge "$COVERAGE_THRESHOLD" ]; then
        echo -e "${GREEN}✓ Coverage: ${coverage_percent}% (meets threshold of ${COVERAGE_THRESHOLD}%)${RESET}"
    else
        echo -e "${YELLOW}⚠️  Coverage: ${coverage_percent}% (below threshold of ${COVERAGE_THRESHOLD}%)${RESET}"
    fi

    echo -e "${BLUE}📄 Coverage report: htmlcov/index.html${RESET}"
    return 0
}

# Function to run performance tests
run_performance_tests() {
    echo -e "${BLUE}⚡ Running performance tests...${RESET}"

    if [ -d "tests/performance" ]; then
        if ! uv run pytest tests/performance/ -v --tb=short -m performance; then
            echo -e "${RED}❌ Performance tests failed${RESET}"
            return 1
        else
            echo -e "${GREEN}✓ Performance tests passed${RESET}"
        fi
    else
        echo -e "${YELLOW}⚠️  No performance tests found${RESET}"
    fi

    return 0
}

# Main function
main() {
    local test_type="${1:-all}"
    local exit_code=0

    # Check dependencies
    if ! command_exists uv; then
        echo -e "${RED}❌ uv not found. Please install uv first.${RESET}"
        exit 1
    fi

    if ! command_exists pytest; then
        echo -e "${YELLOW}⚠️  pytest not found, trying with uv run...${RESET}"
        if ! uv run pytest --version >/dev/null 2>&1; then
            echo -e "${RED}❌ pytest not available. Please run 'make install-dev' first.${RESET}"
            exit 1
        fi
    fi

    # Create test results directory
    mkdir -p test-results

    echo -e "${BLUE}🎯 Test type: $test_type${RESET}"
    echo -e "${BLUE}🔧 Parallel jobs: $PARALLEL_JOBS${RESET}"
    echo -e "${BLUE}⏱️  Timeout: ${TEST_TIMEOUT}s${RESET}"
    echo ""

    case "$test_type" in
        "unit")
            echo -e "${BLUE}Running unit tests only...${RESET}"
            if ! test_all_packages; then
                exit_code=1
            fi
            ;;
        "integration")
            echo -e "${BLUE}Running integration tests only...${RESET}"
            if ! run_integration_tests; then
                exit_code=1
            fi
            ;;
        "e2e")
            echo -e "${BLUE}Running end-to-end tests only...${RESET}"
            if ! run_e2e_tests; then
                exit_code=1
            fi
            ;;
        "performance")
            echo -e "${BLUE}Running performance tests only...${RESET}"
            if ! run_performance_tests; then
                exit_code=1
            fi
            ;;
        "coverage")
            echo -e "${BLUE}Running tests with coverage...${RESET}"
            if ! generate_coverage; then
                exit_code=1
            fi
            ;;
        "all"|*)
            echo -e "${BLUE}Running comprehensive test suite...${RESET}"

            # Run unit tests
            if ! test_all_packages; then
                exit_code=1
            fi

            # Run integration tests
            if ! run_integration_tests; then
                exit_code=1
            fi

            # Run e2e tests
            if ! run_e2e_tests; then
                exit_code=1
            fi

            # Generate coverage
            if ! generate_coverage; then
                exit_code=1
            fi

            # Run performance tests (non-failing)
            run_performance_tests || echo -e "${YELLOW}⚠️  Performance tests had issues but continuing...${RESET}"
            ;;
    esac

    echo ""
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}🎉 All requested tests completed successfully!${RESET}"
    else
        echo -e "${RED}❌ Some tests failed. Please check the output above.${RESET}"
    fi

    exit $exit_code
}

# Handle script arguments
if [ $# -eq 0 ]; then
    main "all"
else
    main "$1"
fi
