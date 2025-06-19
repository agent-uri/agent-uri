#!/bin/bash
# build-packages.sh - Build and publish script for agent-uri packages
# Handles building, testing, and publishing with proper dependency management

set -euo pipefail

# Colors for output
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
RESET='\033[0m'

# Configuration
PUBLISH_MODE=${PUBLISH_MODE:-false}
TEST_PYPI=${TEST_PYPI:-false}
SKIP_TESTS=${SKIP_TESTS:-false}
BUILD_WHEELS_ONLY=${BUILD_WHEELS_ONLY:-false}
PARALLEL_BUILD=${PARALLEL_BUILD:-true}

echo -e "${BLUE}📦 Agent URI Package Builder${RESET}"
echo -e "${BLUE}============================${RESET}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check dependencies
check_dependencies() {
    echo -e "${BLUE}🔍 Checking build dependencies...${RESET}"

    local missing_deps=()

    if ! command_exists uv; then
        missing_deps+=("uv")
    fi

    if ! command_exists poetry; then
        missing_deps+=("poetry")
    fi

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing dependencies: ${missing_deps[*]}${RESET}"
        echo -e "${BLUE}💡 Run 'make install-dev' to install all dependencies${RESET}"
        exit 1
    fi

    echo -e "${GREEN}✓ All build dependencies available${RESET}"
}

# Function to clean previous builds
clean_builds() {
    echo -e "${BLUE}🧹 Cleaning previous builds...${RESET}"

    # Clean root build artifacts
    rm -rf build/ dist/ *.egg-info/

    # Clean package build artifacts
    find packages/ -name "build" -type d -exec rm -rf {} + 2>/dev/null || true
    find packages/ -name "dist" -type d -exec rm -rf {} + 2>/dev/null || true
    find packages/ -name "*.egg-info" -type d -exec rm -rf {} + 2>/dev/null || true

    echo -e "${GREEN}✓ Build artifacts cleaned${RESET}"
}

# Function to validate package structure
validate_package() {
    local package_path="$1"
    local package_name="$2"

    echo -e "${BLUE}   Validating $package_name structure...${RESET}"

    # Check for essential files
    if [ ! -f "$package_path/setup.py" ] && [ ! -f "$package_path/pyproject.toml" ]; then
        echo -e "${RED}     ❌ Missing setup.py or pyproject.toml${RESET}"
        return 1
    fi

    # Check for package source code
    local src_found=false
    for src_dir in "$package_path/$package_name" "$package_path/src/$package_name"; do
        if [ -d "$src_dir" ] && [ -f "$src_dir/__init__.py" ]; then
            src_found=true
            break
        fi
    done

    if [ "$src_found" = "false" ]; then
        echo -e "${RED}     ❌ Package source code not found${RESET}"
        return 1
    fi

    echo -e "${GREEN}     ✓ Package structure valid${RESET}"
    return 0
}

# Function to run tests for a package
test_package() {
    local package_path="$1"
    local package_name="$2"

    if [ "$SKIP_TESTS" = "true" ]; then
        echo -e "${YELLOW}⚠️  Skipping tests for $package_name${RESET}"
        return 0
    fi

    echo -e "${BLUE}🧪 Testing $package_name...${RESET}"

    # Check if tests exist
    local test_dir=""
    if [ -d "$package_path/tests" ]; then
        test_dir="$package_path/tests"
    elif [ -d "$package_path/$package_name/tests" ]; then
        test_dir="$package_path/$package_name/tests"
    else
        echo -e "${YELLOW}⚠️  No tests found for $package_name, skipping...${RESET}"
        return 0
    fi

    # Run tests
    if ! (cd "$package_path" && uv run pytest "$test_dir" -v --tb=short); then
        echo -e "${RED}❌ Tests failed for $package_name${RESET}"
        return 1
    fi

    echo -e "${GREEN}✓ Tests passed for $package_name${RESET}"
    return 0
}

# Function to build a single package
build_package() {
    local package_path="$1"
    local package_name="$2"

    echo -e "${BLUE}🔨 Building $package_name...${RESET}"

    # Validate package first
    if ! validate_package "$package_path" "$package_name"; then
        return 1
    fi

    # Test package if not skipped
    if ! test_package "$package_path" "$package_name"; then
        return 1
    fi

    # Build package
    (
        cd "$package_path"

        if [ -f "pyproject.toml" ]; then
            echo -e "${BLUE}     Building with Poetry...${RESET}"
            if [ "$BUILD_WHEELS_ONLY" = "true" ]; then
                poetry build --format wheel
            else
                poetry build
            fi
        elif [ -f "setup.py" ]; then
            echo -e "${BLUE}     Building with setuptools...${RESET}"
            uv run python setup.py sdist bdist_wheel
        else
            echo -e "${RED}     ❌ No build configuration found${RESET}"
            return 1
        fi
    )

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully built $package_name${RESET}"
        return 0
    else
        echo -e "${RED}❌ Failed to build $package_name${RESET}"
        return 1
    fi
}

# Function to build all packages
build_all_packages() {
    echo -e "${BLUE}🏗️  Building all packages...${RESET}"

    # Define packages to build
    local packages=(
        "packages/uri-parser:agent_uri"
        "packages/descriptor:agent_descriptor"
        "packages/resolver:agent_resolver"
        "packages/transport:agent_transport"
        "packages/client:agent_client"
        "packages/server:agent_server"
        "packages/common:agent_common"
    )

    local failed_builds=()
    local successful_builds=()

    for package_info in "${packages[@]}"; do
        IFS=':' read -r package_path package_name <<< "$package_info"

        if [ -d "$package_path" ]; then
            echo ""
            if build_package "$package_path" "$package_name"; then
                successful_builds+=("$package_name")
            else
                failed_builds+=("$package_name")
            fi
        else
            echo -e "${YELLOW}⚠️  Package directory $package_path not found, skipping...${RESET}"
        fi
    done

    # Report results
    echo ""
    echo -e "${BLUE}📊 Build Results${RESET}"
    echo -e "   Successful builds: ${#successful_builds[@]}"
    echo -e "   Failed builds: ${#failed_builds[@]}"

    if [ ${#failed_builds[@]} -eq 0 ]; then
        echo -e "${GREEN}🎉 All packages built successfully!${RESET}"
        return 0
    else
        echo -e "${RED}❌ Failed to build packages:${RESET}"
        for package in "${failed_builds[@]}"; do
            echo -e "${RED}   • $package${RESET}"
        done
        return 1
    fi
}

# Function to check built packages
verify_builds() {
    echo -e "${BLUE}🔍 Verifying built packages...${RESET}"

    local verification_failures=0

    # Check if distribution files exist
    for package_dir in packages/*/; do
        if [ -d "$package_dir/dist" ]; then
            local package_name=$(basename "$package_dir")
            echo -e "${BLUE}   Checking $package_name distributions...${RESET}"

            local wheel_count=$(find "$package_dir/dist" -name "*.whl" | wc -l)
            local sdist_count=$(find "$package_dir/dist" -name "*.tar.gz" | wc -l)

            if [ "$BUILD_WHEELS_ONLY" = "true" ]; then
                if [ $wheel_count -eq 0 ]; then
                    echo -e "${RED}     ❌ No wheel found${RESET}"
                    ((verification_failures++))
                else
                    echo -e "${GREEN}     ✓ Wheel found${RESET}"
                fi
            else
                if [ $wheel_count -eq 0 ] || [ $sdist_count -eq 0 ]; then
                    echo -e "${RED}     ❌ Missing distributions (wheels: $wheel_count, sdist: $sdist_count)${RESET}"
                    ((verification_failures++))
                else
                    echo -e "${GREEN}     ✓ Both wheel and source distribution found${RESET}"
                fi
            fi

            # Verify wheel can be installed
            local wheel_file=$(find "$package_dir/dist" -name "*.whl" | head -1)
            if [ -n "$wheel_file" ]; then
                echo -e "${BLUE}     Testing wheel installation...${RESET}"
                if uv run pip install --dry-run "$wheel_file" >/dev/null 2>&1; then
                    echo -e "${GREEN}     ✓ Wheel is installable${RESET}"
                else
                    echo -e "${RED}     ❌ Wheel installation test failed${RESET}"
                    ((verification_failures++))
                fi
            fi
        fi
    done

    if [ $verification_failures -eq 0 ]; then
        echo -e "${GREEN}✓ All package verifications passed${RESET}"
        return 0
    else
        echo -e "${RED}❌ $verification_failures verification failure(s)${RESET}"
        return 1
    fi
}

# Function to publish packages
publish_packages() {
    if [ "$PUBLISH_MODE" = "false" ]; then
        echo -e "${BLUE}ℹ️  Publish mode disabled${RESET}"
        return 0
    fi

    echo -e "${BLUE}📤 Publishing packages...${RESET}"

    # Determine repository
    local repository=""
    local repository_flag=""
    if [ "$TEST_PYPI" = "true" ]; then
        repository="testpypi"
        repository_flag="--repository testpypi"
        echo -e "${YELLOW}⚠️  Publishing to TEST PyPI${RESET}"
    else
        repository="pypi"
        echo -e "${RED}🚨 Publishing to PRODUCTION PyPI${RESET}"
        read -p "Are you sure you want to publish to production PyPI? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}❌ Publish cancelled${RESET}"
            return 1
        fi
    fi

    # Configure repository if needed
    if [ "$TEST_PYPI" = "true" ]; then
        poetry config repositories.testpypi https://test.pypi.org/legacy/
    fi

    # Publish each package
    local publish_failures=0

    for package_dir in packages/*/; do
        if [ -d "$package_dir/dist" ]; then
            local package_name=$(basename "$package_dir")
            echo -e "${BLUE}   Publishing $package_name...${RESET}"

            (
                cd "$package_dir"
                if ! poetry publish $repository_flag; then
                    echo -e "${RED}     ❌ Failed to publish $package_name${RESET}"
                    exit 1
                else
                    echo -e "${GREEN}     ✓ Successfully published $package_name${RESET}"
                fi
            )

            if [ $? -ne 0 ]; then
                ((publish_failures++))
            fi
        fi
    done

    if [ $publish_failures -eq 0 ]; then
        echo -e "${GREEN}🎉 All packages published successfully!${RESET}"
        return 0
    else
        echo -e "${RED}❌ $publish_failures package(s) failed to publish${RESET}"
        return 1
    fi
}

# Function to generate build report
generate_build_report() {
    echo -e "${BLUE}📊 Generating build report...${RESET}"

    local report_file="build-report.txt"

    {
        echo "Agent URI Build Report"
        echo "Generated: $(date)"
        echo "======================"
        echo ""
        echo "Build Configuration:"
        echo "- Publish mode: $PUBLISH_MODE"
        echo "- Test PyPI: $TEST_PYPI"
        echo "- Skip tests: $SKIP_TESTS"
        echo "- Wheels only: $BUILD_WHEELS_ONLY"
        echo ""
        echo "Package Distributions:"

        for package_dir in packages/*/; do
            if [ -d "$package_dir/dist" ]; then
                local package_name=$(basename "$package_dir")
                echo "- $package_name:"
                find "$package_dir/dist" -type f -name "*.whl" -o -name "*.tar.gz" | while read -r file; do
                    local size=$(du -h "$file" | cut -f1)
                    echo "  - $(basename "$file") ($size)"
                done
            fi
        done

    } > "$report_file"

    echo -e "${GREEN}✓ Build report generated: $report_file${RESET}"
}

# Main function
main() {
    local action="${1:-build}"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --publish)
                PUBLISH_MODE=true
                shift
                ;;
            --test-pypi)
                TEST_PYPI=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --wheels-only)
                BUILD_WHEELS_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --publish      Publish packages after building"
                echo "  --test-pypi    Use test PyPI instead of production"
                echo "  --skip-tests   Skip running tests before building"
                echo "  --wheels-only  Build only wheel distributions"
                echo "  --help         Show this help message"
                exit 0
                ;;
            *)
                action="$1"
                shift
                ;;
        esac
    done

    echo -e "${BLUE}🎯 Action: $action${RESET}"
    echo -e "${BLUE}📦 Publish: $PUBLISH_MODE${RESET}"
    echo -e "${BLUE}🧪 Test PyPI: $TEST_PYPI${RESET}"
    echo -e "${BLUE}⏭️  Skip tests: $SKIP_TESTS${RESET}"
    echo -e "${BLUE}🎡 Wheels only: $BUILD_WHEELS_ONLY${RESET}"
    echo ""

    # Run build process
    check_dependencies || exit 1

    clean_builds || exit 1

    if ! build_all_packages; then
        echo -e "${RED}❌ Build process failed${RESET}"
        exit 1
    fi

    if ! verify_builds; then
        echo -e "${RED}❌ Build verification failed${RESET}"
        exit 1
    fi

    if ! publish_packages; then
        echo -e "${RED}❌ Publish process failed${RESET}"
        exit 1
    fi

    generate_build_report

    echo ""
    echo -e "${GREEN}🎉 Build process completed successfully!${RESET}"

    if [ "$PUBLISH_MODE" = "true" ]; then
        if [ "$TEST_PYPI" = "true" ]; then
            echo -e "${BLUE}💡 Packages published to Test PyPI${RESET}"
        else
            echo -e "${BLUE}💡 Packages published to Production PyPI${RESET}"
        fi
    else
        echo -e "${BLUE}💡 Packages built but not published${RESET}"
        echo -e "${BLUE}💡 Use --publish flag to publish packages${RESET}"
    fi
}

# Handle script execution
main "$@"
