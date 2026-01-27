# Quick Test Reference

## Installation
```bash
pip install -e ".[dev]"
```

## Run All Tests
```bash
pytest
```

## Run with Coverage
```bash
pytest --cov=pyosc --cov-report=term-missing --cov-report=html
```

## Run Specific Tests
```bash
# Run one file
pytest tests/test_dispatcher.py

# Run one class
pytest tests/test_dispatcher.py::TestDispatcher

# Run one test
pytest tests/test_dispatcher.py::TestDispatcher::test_exact_match

# Run by keyword
pytest -k "tcp"
pytest -k "timeout"
```

## Run with Different Verbosity
```bash
pytest -v          # Verbose
pytest -vv         # More verbose
pytest -q          # Quiet
```

## Run and Stop on First Failure
```bash
pytest -x
```

## Run with Print Statements
```bash
pytest -s
```

## Using the Test Runner Script
```bash
# Make executable (first time only)
chmod +x run_tests.sh

# Run all tests
./run_tests.sh

# Run with coverage
./run_tests.sh --coverage

# Run specific test
./run_tests.sh --test tests/test_peer.py

# Verbose output
./run_tests.sh --verbose
```

## Common Test Scenarios

### Before Committing
```bash
pytest --cov=pyosc --cov-report=term-missing
```

### Debugging a Failure
```bash
pytest -vv -s tests/test_name.py::test_function
```

### Quick Smoke Test
```bash
pytest -x -q
```

### Generate HTML Coverage Report
```bash
pytest --cov=pyosc --cov-report=html
# Then open htmlcov/index.html in browser
```

## Test Organization
- `test_dispatcher.py` - Message routing tests
- `test_call_handler.py` - Request/response tests  
- `test_peer.py` - Network communication tests
- `test_integration.py` - End-to-end workflows

## Exit Codes
- 0: All tests passed
- 1: Tests failed
- 2: Test execution interrupted
- 3: Internal error
- 4: pytest command line usage error
- 5: No tests collected
