# PyOSC Test Suite

This directory contains comprehensive unit tests for the PyOSC library.

## Test Structure

- **test_dispatcher.py**: Tests for the Dispatcher class and message routing
  - Pattern matching (wildcards, character classes, alternatives)
  - Message dispatching to handlers
  - Bundle scheduling and timetag processing
  - Cache management and handler lifecycle
  
- **test_call_handler.py**: Tests for the CallHandler class
  - Request-response pattern implementation
  - Validation with Pydantic models
  - Timeout handling
  - Thread safety and concurrent calls
  
- **test_peer.py**: Tests for the Peer class
  - TCP peer communication
  - UDP peer communication
  - Message sending and receiving
  - Connection lifecycle management
  - Integration with Dispatcher

- **conftest.py**: Shared pytest fixtures and utilities

## Running Tests

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=pyosc --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_dispatcher.py
```

### Run specific test class or function
```bash
pytest tests/test_dispatcher.py::TestDispatcher
pytest tests/test_dispatcher.py::TestDispatcher::test_exact_match
```

### Run tests matching a pattern
```bash
pytest -k "tcp"  # Run all tests with 'tcp' in the name
```

### Run with verbose output
```bash
pytest -v
```

### Run without slow tests
```bash
pytest -m "not slow"
```

## Test Coverage

The test suite aims for comprehensive coverage of:

1. **Core Functionality**
   - Message pattern matching and routing
   - Request-response patterns
   - TCP and UDP communication

2. **Edge Cases**
   - Empty messages and bundles
   - Malformed patterns
   - Connection failures
   - Timeout scenarios

3. **Concurrency**
   - Thread safety
   - Multiple concurrent handlers
   - Race conditions

4. **Integration**
   - Peer-Dispatcher integration
   - CallHandler-Peer integration
   - End-to-end message flow

## Dependencies

The tests require:
- pytest
- pytest-cov (for coverage reports)
- pytest-timeout (for timeout handling)

Install with:
```bash
pip install -e ".[dev]"
```

## Writing New Tests

When adding new tests:

1. Follow the existing naming convention: `test_*.py`
2. Use descriptive test names: `test_<what_is_being_tested>`
3. Add docstrings explaining what each test verifies
4. Use fixtures from conftest.py for common setup
5. Clean up resources in tearDown or fixtures
6. Mark slow tests with `@pytest.mark.slow`

## Continuous Integration

Tests are automatically run in CI pipeline on:
- Pull requests
- Commits to main branch
- Release builds

Coverage reports are generated and tracked over time.
