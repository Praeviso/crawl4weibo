# Crawl4Weibo Development Documentation

[English](DEVELOPMENT.md) | [中文](DEVELOPMENT_zh.md)

## Table of Contents
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Testing Guide](#testing-guide)
- [Code Quality](#code-quality)

## Development Environment Setup

### Requirements
- Python 3.9+
- uv (recommended package manager)

### Quick Start
```bash
# Clone the project
git clone https://github.com/Kritoooo/crawl4weibo.git
cd crawl4weibo

# Install development dependencies
uv sync --dev

# Run tests to ensure the environment is set up correctly
uv run pytest tests/ -v
```

### Development Dependencies
```toml
[dependency-groups]
dev = [
    "pytest>=7.4.4",    # Testing framework
    "pytest-cov>=4.1.0", # Test coverage
    "ruff>=0.14.0",      # Modern fast linter and formatter
]
```

## Project Structure

```
crawl4weibo/
├── crawl4weibo/           # Main package
│   ├── __init__.py
│   ├── core/              # Core functionality
│   │   ├── __init__.py
│   │   └── client.py      # WeiboClient main implementation
│   ├── models/            # Data models
│   │   ├── __init__.py
│   │   ├── user.py        # User model
│   │   └── post.py        # Post model
│   ├── utils/             # Utility modules
│   │   ├── __init__.py
│   │   ├── logger.py      # Logging utilities
│   │   └── parser.py      # Parsing utilities
│   └── exceptions/        # Custom exceptions
│       ├── __init__.py
│       └── base.py        # Base exception classes
├── tests/                 # Test files
│   ├── __init__.py
│   ├── test_models.py     # Model unit tests
│   ├── test_client.py     # Client unit tests
│   └── test_integration.py # Integration tests
├── docs/                  # Documentation
├── examples/              # Example code
├── .github/workflows/     # GitHub Actions configuration
├── pyproject.toml         # Project configuration
├── pytest.ini            # Test configuration
└── README.md
```

## Development Workflow

### Branching Strategy
- `main` - Main branch, stable releases
- `develop` - Development branch
- `feature/*` - Feature branches
- `hotfix/*` - Hotfix branches

### Feature Development Process
```bash
# 1. Create a feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# 2. Run tests continuously during development
uv run pytest tests/ -m unit  # Quick unit tests

# 3. Complete checks before committing
uv run ruff check crawl4weibo --fix  # Check and auto-fix issues
uv run ruff format crawl4weibo       # Format code
uv run pytest tests/                 # Run all tests

# 4. Commit code
git add .
git commit -m "feat: add your feature description"

# 5. Push and create PR
git push origin feature/your-feature-name
# Then create a Pull Request on GitHub
```

### Commit Message Convention
Use conventional commit format:
```
feat: new feature
fix: bug fix
docs: documentation update
style: code style adjustment (no functional changes)
refactor: code refactoring
test: add tests
chore: build or tool-related changes
```

## Testing Guide

### Test Types
The project includes two types of tests:

#### Unit Tests (`@pytest.mark.unit`)
- Test individual functions or classes
- No external API or service dependencies
- Fast execution, suitable for frequent runs during development

```bash
# Run only unit tests
uv run pytest tests/ -m unit -v
```

#### Integration Tests (`@pytest.mark.integration`)
- Test interactions with real Weibo API
- Verify correctness of API response data structures
- Slower execution, suitable for complete validation

```bash
# Run only integration tests
uv run pytest tests/ -m integration -v
```

### Running Tests
```bash
# Run all tests
uv run pytest tests/ -v

# With coverage report
uv run pytest tests/ --cov=crawl4weibo --cov-report=html

# Run specific test file
uv run pytest tests/test_models.py -v

# Run specific test method
uv run pytest tests/test_models.py::TestUser::test_user_creation -v
```

### Writing Tests

#### Unit Test Example
```python
import pytest
from crawl4weibo.models.user import User

@pytest.mark.unit
class TestUser:
    def test_user_creation(self):
        user = User(id="123", screen_name="TestUser")
        assert user.id == "123"
        assert user.screen_name == "TestUser"
```

#### Integration Test Example
```python
import pytest
from crawl4weibo import WeiboClient

@pytest.mark.integration
class TestWeiboClientIntegration:
    def test_get_user_by_uid_returns_data(self):
        client = WeiboClient()
        try:
            user = client.get_user_by_uid("2656274875")
            assert user is not None
            assert hasattr(user, 'screen_name')
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
```

## Code Quality

### Code Style
The project uses **Ruff** as a unified code quality tool, providing extremely fast linting and formatting:

#### Ruff - Unified Code Quality Tool
```bash
# Code checking
uv run ruff check crawl4weibo

# Auto-fix issues
uv run ruff check crawl4weibo --fix

# Code formatting
uv run ruff format crawl4weibo

# Check format (without modifying)
uv run ruff format crawl4weibo --check
```

### Configuration
Ruff configuration in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 88
target-version = "py38"

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "F",     # pyflakes
    "I",     # isort
    "UP",    # pyupgrade
    "B",     # flake8-bugbear
    "C4",    # flake8-comprehensions
    "SIM",   # flake8-simplify
]

[tool.ruff.format]
quote-style = "double"
```

## Development Best Practices

### Pre-commit Checklist
Complete checklist before pushing code:
```bash
# 1. Install dependencies
uv sync --dev

# 2. Code quality check and fix
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo

# 3. Run tests
uv run pytest tests/ -v

# 4. Build package verification (optional)
uv build
```

## Troubleshooting

### Test Failures
```bash
# View detailed error messages
uv run pytest tests/ -v --tb=long

# Run a single failing test
uv run pytest tests/test_file.py::test_function -v
```

### Code Format Issues
```bash
# Auto-fix with ruff
uv run ruff check crawl4weibo --fix
uv run ruff format crawl4weibo
```

### Dependency Issues
```bash
# Reinstall dependencies
rm -rf .venv
uv venv
uv sync --dev
```

## Contributing Guide

1. Fork the project
2. Create a feature branch
3. Write code and tests
4. Ensure all checks pass
5. Create a Pull Request
6. Respond to Code Review feedback

### Code Review Checklist
- Code functionality correctness
- Test coverage
- Code style consistency (verified by ruff)
- Performance impact
- Backward compatibility

Contributions are welcome! Please create an Issue for discussion if you have any questions.
