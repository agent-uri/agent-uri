# Technical Debt and Issues to Address

This document tracks known technical debt and issues that need to be addressed in the agent-uri project.

## Type Checking Issues (High Priority)

### MyPy Configuration Issues
- **Status**: Currently non-blocking in CI
- **Impact**: Type safety compromised, potential runtime errors
- **Action Required**: Gradually re-enable strict type checking

### Type Annotation Gaps

#### Core Parser Module (`agent_uri/parser.py`)
- Line 35: Incompatible assignment to query dict
- Line 191: Missing type annotation for `query_params`
- Line 211: String assigned to list type
- Line 237: Dict type variance issues with `AgentUri`

#### Descriptor Module (`agent_uri/descriptor/`)
- `validator.py:30`: None assigned to ValidationError list
- `parser.py:69`: List assigned to dict type
- `compatibility.py:81+`: Multiple type incompatibility issues in agent card conversion
- `generator.py:157+`: Dict assigned to string types

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

### Dependency Vulnerabilities (Medium Priority)
Found by safety check - require dependency updates:

1. **anyio 3.7.1** → Need 4.4.0+ (Race condition fix)
2. **black 23.12.1** → Need 24.3.0+ (ReDoS vulnerability)
3. **cryptography 43.0.3** → Need 44.0.1+ (OpenSSL security update)
4. **starlette 0.27.0** → Multiple issues:
   - Need >0.36.1 (multipart regex DoS)
   - Need 0.40.0+ (DoS via request restrictions)

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
- **Status**: Fixed
- Bandit exclude patterns corrected
- Tool parameter synchronization completed
- Security scans properly scoped

## Future Improvements

### Type Safety Roadmap
1. **Phase 1**: Fix core parser and descriptor type issues
2. **Phase 2**: Complete transport layer type annotations
3. **Phase 3**: Add comprehensive capability system types
4. **Phase 4**: Re-enable strict mypy configuration
5. **Phase 5**: Add type checking to pre-commit hooks

### Testing Improvements
1. Increase test coverage beyond current 66%
2. Add integration tests for transport protocols
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

---

**Note**: This file tracks technical debt and should not be committed to avoid cluttering the repository. Issues should be converted to GitHub issues for tracking and assignment.