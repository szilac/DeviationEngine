# API Endpoint Tests

This directory contains unit tests for all API endpoints organized by router modules.

## Directory Structure

```
tests/api/
├── conftest.py              # Shared fixtures for API tests
├── test_utils.py            # Helper functions and assertions
├── test_health.py           # Health & info endpoints (2 tests)
├── test_historical.py       # Historical events endpoints
├── test_translation.py      # Translation service endpoints
├── test_settings.py         # Settings & LLM config endpoints
├── test_import_export.py    # Timeline import/export endpoints
├── test_images.py           # Image generation endpoints
├── test_audio.py            # Audio script & generation endpoints
├── test_skeletons.py        # Skeleton workflow endpoints
└── test_timelines.py        # Timeline CRUD & generation endpoints
```

## Running Tests

### Run All API Tests
```bash
cd backend
pytest tests/api/ -v
```

### Run Specific Router Tests
```bash
pytest tests/api/test_health.py -v
pytest tests/api/test_timelines.py -v
```

### Run with Coverage
```bash
pytest tests/api/ --cov=app/api --cov-report=html
```

### Run Tests Matching Pattern
```bash
pytest tests/api/ -k "test_get" -v
```

## Test Fixtures

### Database Fixtures (from `tests/conftest.py`)
- `db_session`: Test database session
- `timeline_db`: Pre-created timeline
- `timeline_with_generation`: Timeline with generation
- `skeleton_db`: Pre-created skeleton
- `skeleton_with_events`: Skeleton with events

### API Fixtures (from `tests/api/conftest.py`)
- `test_client`: FastAPI TestClient
- `async_test_client`: Async HTTP client
- `mock_historian_agent`: Mock Historian agent
- `mock_storyteller_agent`: Mock Storyteller agent
- `mock_skeleton_agent`: Mock Skeleton agent
- `mock_llm_service`: Mock LLM service

## Test Naming Convention

```python
def test_{http_method}_{endpoint_name}_{scenario}():
    """Test description."""
    pass

# Examples:
def test_get_health_returns_200()
def test_post_timeline_creates_record()
def test_delete_timeline_not_found_returns_404()
```

## Writing Tests

### Basic Test Structure

```python
def test_endpoint_success(test_client, db_session):
    """Test successful endpoint call."""
    # Arrange: Set up test data

    # Act: Call endpoint
    response = test_client.get("/api/endpoint")

    # Assert: Verify response
    assert response.status_code == 200
    data = response.json()
    assert "expected_key" in data
```

### Testing with Mocks

```python
def test_endpoint_with_mock(test_client, mock_historian_agent):
    """Test endpoint with mocked agent."""
    # Mock is automatically patched
    response = test_client.post("/api/generate", json={...})

    assert response.status_code == 201
    mock_historian_agent.assert_called_once()
```

### Database Assertions

```python
async def test_endpoint_creates_record(test_client, db_session):
    """Test that endpoint creates database record."""
    # Call endpoint
    response = test_client.post("/api/create", json={...})

    # Verify database state
    result = await db_session.execute(select(Model))
    records = result.scalars().all()
    assert len(records) == 1
```

## Coverage Goals

- **Target**: ≥ 80% coverage for all router modules
- **Focus Areas**:
  - All HTTP methods (GET, POST, PUT, DELETE)
  - Success scenarios (200, 201, 204)
  - Error scenarios (400, 404, 500)
  - Edge cases (empty data, invalid UUIDs, etc.)

## Debugging Failed Tests

### View Detailed Output
```bash
pytest tests/api/test_health.py -vv
```

### Show Print Statements
```bash
pytest tests/api/test_health.py -s
```

### Run Single Test
```bash
pytest tests/api/test_health.py::test_get_health_returns_200 -v
```

### Enable Debug Mode
```bash
pytest tests/api/test_health.py --pdb
```

## Continuous Integration

These tests are designed to run in CI/CD pipelines:
- Fast execution (mocked external services)
- Isolated (in-memory database)
- Deterministic (no flaky tests)
- Independent (no test order dependencies)
