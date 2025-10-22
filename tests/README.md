# OpenOrtho Test Suite

Professional test suite for the OpenOrtho orthophotos-downloader package.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py                 # Pytest configuration and fixtures
├── test_image_download.py      # Core download functionality tests
├── test_wms_germany.py         # State-specific downloader tests
├── test_auto_downloader.py     # Auto-detection and orchestration tests
└── test_integration.py         # Integration tests with actual downloads
```

## Running Tests

### Install pytest (if not already installed)
```bash
pip install pytest pytest-cov pytest-timeout
```

### Run all tests
```bash
pytest
```

### Run only fast tests (skip slow downloads)
```bash
pytest -m "not slow"
```

### Run only unit tests (no integration)
```bash
pytest -m "not download"
```

### Run with coverage report
```bash
pytest --cov=src/orthophotos_downloader --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_wms_germany.py
```

### Run specific test
```bash
pytest tests/test_wms_germany.py::TestStateDownloaders::test_bavaria_rgb_configuration
```

### Run in verbose mode
```bash
pytest -v
```

### Run in parallel (requires pytest-xdist)
```bash
pytest -n auto
```

## Test Categories

### Unit Tests (Fast)
- **test_image_download.py**: Tests core classes without actual downloads
- **test_wms_germany.py**: Tests state downloader instantiation and configuration
- **test_auto_downloader.py**: Tests auto detection logic

### Integration Tests (Slow)
- **test_integration.py**: Tests with actual WMS downloads
  - Marked with `@pytest.mark.download`
  - Marked with `@pytest.mark.slow`
  - Use small areas (100m x 100m) to minimize download time

## Test Markers

- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.download` - Tests that download actual data from WMS
- `@pytest.mark.integration` - Integration tests

## Continuous Integration

### Run only fast tests in CI
```bash
pytest -m "not slow and not download" --maxfail=5
```

### Run full test suite (including downloads)
```bash
pytest --maxfail=10
```

## Coverage

Generate HTML coverage report:
```bash
pytest --cov=src/orthophotos_downloader --cov-report=html
open htmlcov/index.html
```

## Test Data

Integration tests use:
- Very small areas (100m x 100m) for fast execution
- Bavaria (Bayern) as default test state
- Temporary directories that are auto-cleaned

## Expected Test Results

### Fast Tests (unit + auto)
- ~50-100 tests
- Runtime: < 10 seconds
- No network required

### Full Suite (including integration)
- ~60-110 tests
- Runtime: 1-5 minutes
- Network required
- May have 1-2 failures due to external WMS services

## Troubleshooting

### Import Errors
```bash
# Make sure package is installed
pip install -e .
```

### Slow Tests Taking Too Long
```bash
# Skip slow tests
pytest -m "not slow"
```

### WMS Service Failures
- Some tests may fail if external WMS services are down
- This is expected and not a code issue
- Hamburg WMS is known to have issues

## Adding New Tests

### Add a unit test:
```python
def test_my_feature():
    """Test description."""
    # Your test code
    assert result == expected
```

### Add an integration test:
```python
@pytest.mark.download
@pytest.mark.slow
def test_my_download_feature():
    """Test actual download."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Your download test
        assert downloaded_file.exists()
```

## Best Practices

1. **Fast by default**: Unit tests should run in < 1 second each
2. **Use fixtures**: Share common setup code
3. **Use markers**: Tag slow/integration tests appropriately
4. **Mock when possible**: Don't download unless testing downloads
5. **Clean up**: Use temporary directories, no test artifacts
6. **Parametrize**: Test multiple inputs efficiently
7. **Document**: Clear docstrings for each test

## Example Workflow

```bash
# During development (fast feedback)
pytest -m "not slow" --ff

# Before commit (more thorough)
pytest -m "not download" --cov=src/orthophotos_downloader

# Before push (full suite)
pytest --cov=src/orthophotos_downloader --cov-report=html

# Check coverage
open htmlcov/index.html
```
