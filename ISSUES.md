# Technical Debt and Issues to Address

This document tracks known technical debt and issues that need to be addressed in the agent-uri project.

## Recent Updates

### PR #7 - Quick Wins Improvements (Merged 2025-06-20)

#### ✅ Test Coverage & Quality Gate Enhancements
- **Test coverage badge** added to README showing current 66% coverage
- **Coverage requirements enforced** in CI with `--cov-fail-under=66`
- **Coverage increased** to 66.38% with comprehensive exception tests
- **Quality gate strengthened** with blocking coverage requirements

#### ✅ Error Handling System Overhaul
- **HTTP-extended 4-digit error codes** implemented (4xxx client, 5xxx server)
- **Comprehensive exception hierarchy** with rich context details
- **100% test coverage** for exceptions module (28 test cases)
- **Enhanced debugging capability** with structured error details

#### ✅ Professional Project Presentation
- **Comprehensive badge collection** in README (coverage, CI, security, versions)
- **All 234 tests passing** across Python 3.9-3.12
- **Zero breaking changes** maintaining full backward compatibility

### PR #6 - Critical Security & Type Safety (Merged 2025-06-20)

#### ✅ Critical Security Issues Resolved
- **Updated all vulnerable dependencies** to secure versions
- **Zero security vulnerabilities** remaining (verified by safety and pip-audit)
- **CI/CD pipeline hardened** - all security checks now blocking

#### ✅ Type Safety Phase 1 Completed
- **Fixed parser.py** type issues (lines 35, 191, 211, 237)
- **Fixed descriptor module** type annotation gaps
- **mypy now passes** with 0 errors across 27 source files
- **Type checking enforced** in CI/CD pipeline

#### ✅ CI/CD Improvements Completed
- **Removed all `|| echo` fallbacks** - security checks truly blocking
- **pip-audit failures** now block CI pipeline
- **mypy type errors** now block releases
- **All pre-commit hooks** passing

#### ✅ Code Quality Improvements
- **Fixed all flake8 issues** in core code and examples
- **Maintained 66% test coverage** with 206/207 tests passing
- **Quality gate** fully enforced

## Type Checking Issues (High Priority)

### MyPy Configuration Issues
- **Status**: ✅ FIXED - Now blocking in CI (PR #6)
- **Impact**: Type safety enforced, runtime errors prevented
- **Completed**: mypy checks now block releases and CI

### Type Annotation Gaps

#### Core Parser Module (`agent_uri/parser.py`)
- **Status**: ✅ FIXED (PR #6)
- Line 35: Fixed query dict type assignment
- Line 191: Added proper type annotations
- Line 211: Fixed string/list type mismatch
- Line 237: Resolved Dict variance issues

#### Descriptor Module (`agent_uri/descriptor/`)
- **Status**: ✅ PARTIALLY FIXED (PR #6)
- `parser.py:62`: Added explicit type annotation for result dict
- `validator.py:30`: Still needs attention
- `compatibility.py:81+`: Multiple type incompatibility issues remain
- `generator.py:157+`: Dict/string type issues remain

#### Transport Layer (`agent_uri/transport/`)
- `base.py:51,81`: Missing function type annotations
- `registry.py:26`: Missing return type annotations
- `transports/local.py`: Multiple missing type annotations and return type issues
- `transports/https.py`: Missing type annotations throughout
- `transports/websocket.py`: Extensive type annotation gaps, None attribute access

#### Capability System (`agent_uri/capability.py`)
- Lines 101-149: Multiple type assignment incompatibilities
- Line 162: Missing function type annotations
- Line 196: Missing type annotation for sessions
- Lines 307-344: Optional dict handling issues
- Line 403: Missing function type annotation

#### Handler Module (`agent_uri/handler.py`)
- Multiple missing return type annotations
- Missing function parameter type annotations
- AsyncGenerator vs Coroutine return type conflicts

### Test Files Type Issues
- Most test functions missing return type annotations (`-> None`)
- Affects files: `test_validator.py`, `test_error_transport.py`, etc.

## Security Issues (Addressed but Documented)

### False Positives (Fixed with nosec comments)
- **B107**: "Bearer" token type flagged as hardcoded password (legitimate OAuth standard)
- **B310**: URL opening with scheme validation (properly validated)
- **B110**: Try/except pass in resource cleanup (acceptable pattern)

### Dependency Vulnerabilities (CRITICAL - ✅ FIXED in PR #6)
Found by safety check - all vulnerabilities resolved:

1. **anyio** → ✅ Updated to ^4.9.0 (was 3.7.1, fixed race condition)
2. **black** → ✅ Updated to ^25.1.0 (was 24.10.0, fixed ReDoS vulnerability)
3. **cryptography** → ✅ Maintained at ^45.0.4 (secure version)
4. **starlette** → ✅ Constrained to >=0.40.0,<0.47.0 (fixed DoS vulnerabilities)

**Completed Actions**:
- ✅ Updated all vulnerable dependencies in pyproject.toml
- ✅ Dependabot already enabled for automated security updates
- ✅ pip audit added to CI pipeline and made blocking
- ✅ All security checks now blocking in CI (removed all `|| echo` fallbacks)

## Code Quality Issues

### Import Management
- **Status**: Fixed with proper noqa comments
- Public API imports in `__init__.py` properly documented

### Line Length Consistency
- **Status**: Fixed
- All tools now use 88-character line length consistently

### Code Formatting
- **Status**: Fixed
- Black, isort, flake8 all properly configured and passing

## Configuration Issues

### Build System Modernization
- **Status**: Completed
- Poetry + uv combination working
- All package management modernized

### CI/CD Pipeline
- **Status**: ✅ FULLY FIXED (PR #6)
- Bandit exclude patterns corrected ✅
- Tool parameter synchronization completed ✅
- Security scans properly scoped ✅
- Version sync check already implemented ✅
- Security gate in release pipeline already exists ✅
- All `|| echo` fallbacks removed - checks now blocking ✅

## Future Improvements

### Type Safety Roadmap (Updated after PR #6)
1. **Phase 1**: ✅ COMPLETED - Core parser and descriptor type issues fixed
   - Fixed: `parser.py` query dict, type annotations, string/list issues
   - Fixed: `descriptor/parser.py` explicit type annotations
   - mypy now passes with 0 errors

2. **Phase 2 (Week 2)**: Complete transport layer type annotations (PR #5 Required)
   - Priority: `websocket.py`, `https.py`, `local.py`
   - Fix None attribute access issues
   - Add transport-specific type tests

3. **Phase 3 (Week 3)**: Add comprehensive capability system types
   - Fix type assignment incompatibilities in `capability.py`
   - Add proper session type annotations
   - Complete handler module types

4. **Phase 4 (Week 4)**: Re-enable strict mypy configuration
   - ✅ COMPLETED: Removed all `|| echo` fallbacks from CI
   - Still needed: Enable strict mypy configuration
   - ✅ COMPLETED: mypy is now blocking in CI

5. **Phase 5**: Add type checking to pre-commit hooks

### Testing Improvements (High Priority)
1. **Increase test coverage to 80% minimum**
   - Current: 66.38% overall (✅ coverage requirements enforced in CI)
   - Critical gaps: transport layer (local.py 18%, websocket.py 20%, https.py 58%)
   - ✅ Coverage requirements added to CI (`--cov-fail-under=66`)
   - ✅ Test coverage badges added to README

2. **Add comprehensive integration tests**
   - End-to-end transport protocol tests
   - Multi-protocol communication tests
   - Failure injection scenarios
   - Performance benchmarks

3. Add property-based testing for parser edge cases
4. Mock external dependencies in tests

### Documentation
1. Add comprehensive API documentation
2. Create developer setup guide
3. Document transport protocol specifications
4. Add troubleshooting guides

### Performance Optimization
1. Profile transport layer performance
2. Optimize parser for large URIs
3. Add caching for descriptor validation
4. Benchmark capability invocation overhead

## Maintenance Tasks

### Dependency Management
- Regular security updates for all dependencies
- Monitor for new vulnerability disclosures
- Update dev dependencies (black, mypy, etc.)

### Code Review Guidelines
- Require type annotations for all new code
- Mandate test coverage for new features
- Security review for transport protocol changes

### Release Process
- Automate changelog generation
- Add semantic versioning checks
- Create release candidate testing process

## PR #3 Review Recommendations

### High Priority Actions

#### 1. Type Safety Enforcement
- **Issue**: 100+ mypy errors currently ignored
- **Action**: Remove `|| echo` fallbacks for mypy in CI
- **Timeline**: Before next release
- **Details**:
  ```python
  # Example fix needed in parser.py line 35
  query: Optional[Dict[str, Union[str, list]]] = None  # Fix type annotation
  ```

#### 2. Transport Layer Test Coverage
- **Current**: local.py (18%), websocket.py (20%), https.py (58%)
- **Target**: 80%+ for all transport modules
- **Action**: Add comprehensive unit and integration tests
- **Focus Areas**:
  - Error handling paths
  - Connection lifecycle
  - Protocol-specific features

#### 3. Migration Documentation
- **Issue**: No guide for v0.1.x → v0.2.x migration
- **Action**: Create MIGRATION.md with:
  - Package structure changes (multiple → unified)
  - Import path updates
  - Breaking changes list
  - Example migrations

### Medium Priority Actions

#### 4. Enhanced Error Messages
- **Status**: ✅ COMPLETED (PR #7)
- **Action**: Add helpful context to exceptions
- **Implemented**: HTTP-extended 4-digit error codes with rich context details
- **Result**: All exceptions now include structured details and enhanced context

#### 5. Security Hardening
- **Status**: ✅ COMPLETED (PR #6)
- **Action**: Make security checks blocking in CI
- **Completed**: `pip audit` and `safety` checks now blocking in CI
- **Implemented**: Security gate in release pipeline with TestPyPI publishing

#### 6. Integration Testing Suite
- **Missing**: End-to-end transport tests
- **Action**: Create integration test framework
- **Include**:
  - Multi-protocol communication tests
  - Failure injection scenarios
  - Performance benchmarks

### Developer Experience Improvements

#### 7. Progressive Examples
- **Issue**: Complex decorators may intimidate beginners
- **Action**: Add simple → complex example progression
- **Structure**:
  ```python
  # Level 1: Minimal
  @capability(name="hello")
  async def hello(): return {"message": "Hello"}

  # Level 2: With parameters
  @capability(name="echo", description="...")
  async def echo(message: str): return {"response": message}

  # Level 3: Full configuration
  @capability(name="advanced", version="1.0.0", schemas={...})
  ```

#### 8. Debugging & Troubleshooting Guide
- **Add**: Troubleshooting section to docs
- **Include**:
  - Common error scenarios and solutions
  - Debug logging configuration
  - Network debugging for agents
  - Environment variables (e.g., `AGENT_URI_DEBUG=1`)

#### 9. API Documentation Generation
- **Tool**: Sphinx or MkDocs with autodoc
- **Coverage**: All public APIs with examples
- **Format**: Hosted on Read the Docs

### CI/CD Enhancements

#### 10. Test Environment Improvements
- **Add**: Dedicated integration test environment
- **Implement**: Canary deployment strategy
- **Create**: Smoke test suite for post-deployment

#### 11. Automated Rollback
- **Issue**: No automatic rollback on failure
- **Action**: Implement rollback triggers
- **Criteria**: Failed smoke tests, error rate thresholds

#### 12. Performance Testing
- **Add**: Baseline performance metrics
- **Monitor**: Regression in key operations
- **Benchmark**: Transport protocol efficiency

### Long-term Architecture

#### 13. Caching Strategy
- **Add**: Poetry cache in GitHub Actions
- **Implement**: Descriptor validation cache
- **Consider**: CDN for agent descriptors

#### 14. Monitoring & Observability
- **Add**: Structured logging
- **Implement**: Metrics collection
- **Create**: Health check endpoints

#### 15. Plugin Architecture
- **Design**: Plugin system for custom transports
- **Document**: Extension points
- **Example**: Custom authentication plugins

## Post-PR #3 Action Priority Summary

### Critical (48 Hours)
1. **PR #4**: Update vulnerable dependencies (anyio, black, cryptography, starlette)
2. Enable Dependabot and security scanning

### High Priority (Week 1)
1. **PR #5**: Critical type fixes for transport layer
2. Begin Phase 1 of Type Safety Roadmap (parser types)
3. Implement security gate in release pipeline
4. Add test coverage requirements (80% minimum)

### Medium Priority (Week 2-4)
1. Complete remaining phases of Type Safety Roadmap
2. Add version sync CI check
3. Document rollback procedures
4. Implement SBOM generation

---

**Note**: This file tracks technical debt from PR reviews and ongoing development. It serves as our action item tracker for maintaining code quality and security.
