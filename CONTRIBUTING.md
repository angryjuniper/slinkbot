# Contributing to SlinkBot

Thank you for your interest in contributing to SlinkBot! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- Discord Bot development knowledge
- Basic understanding of SQLite and API integration

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/angryjuniper/slinkbot.git
   cd slinkbot/python
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment**
   ```bash
   cp config/examples.env .env
   # Configure your development environment variables
   ```

5. **Initialize Database**
   ```bash
   python -c "from database.models import init_database; init_database()"
   ```

## 🎯 How to Contribute

### Reporting Issues

When reporting issues, please include:

- **Clear Description**: What you expected vs. what happened
- **Steps to Reproduce**: Detailed reproduction steps
- **Environment Info**: Python version, OS, Discord.py version
- **Logs**: Relevant error messages or logs
- **Screenshots**: If applicable

Use the GitHub issue template and label appropriately:
- `bug`: Something isn't working
- `enhancement`: New feature or improvement
- `documentation`: Documentation improvements
- `question`: Questions about usage

### Feature Requests

We welcome feature requests! Please:

1. Check existing issues to avoid duplicates
2. Provide clear use cases and rationale
3. Consider implementation complexity
4. Be open to discussion and iteration

### Pull Requests

#### Before You Start

1. **Check Issues**: Look for existing issues or create one
2. **Discuss Approach**: For large changes, discuss your approach first
3. **Branch Strategy**: Create a feature branch from `main`

#### Development Workflow

1. **Create Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow code style guidelines
   - Add tests for new functionality
   - Update documentation as needed

3. **Test Your Changes**
   ```bash
   # Run existing tests
   pytest
   
   # Test your specific changes
   python -m pytest tests/test_your_feature.py
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

5. **Push and Create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## 📋 Code Guidelines

### Code Style

- **PEP 8**: Follow Python style guidelines
- **Type Hints**: Use type annotations for all functions
- **Docstrings**: Document all classes and functions
- **Import Organization**: Group imports logically
- **Line Length**: Maximum 100 characters

Example:
```python
from typing import Optional, Dict, Any

async def process_request(
    request_id: int, 
    user_id: int, 
    options: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Process a media request.
    
    Args:
        request_id: Unique request identifier
        user_id: Discord user ID
        options: Optional processing parameters
        
    Returns:
        True if processing succeeded, False otherwise
        
    Raises:
        MediaRequestError: If processing fails
    """
    # Implementation here
    pass
```

### Architecture Patterns

#### Error Handling
Use the centralized error handling system:

```python
from utils.error_handling import handle_service_errors_async, MediaRequestError

@handle_service_errors_async("media request processing")
async def process_media_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    # Your implementation
    pass
```

#### Database Operations
Use the centralized database session management:

```python
from utils.database_session import database_session

async def update_request_status(request_id: int, status: int) -> bool:
    with database_session() as session:
        request = session.query(TrackedRequest).filter_by(id=request_id).first()
        if request:
            request.last_status = status
            session.commit()
            return True
        return False
```

#### Configuration
Use the centralized configuration system:

```python
from config.settings import load_config

config = load_config()
jellyseerr_url = config.api.jellyseerr_url
```

### Testing Guidelines

#### Test Structure
```python
import pytest
from unittest.mock import Mock, patch
from your_module import YourClass

class TestYourClass:
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.instance = YourClass()
    
    def test_valid_input(self):
        """Test with valid input."""
        result = self.instance.your_method("valid_input")
        assert result == expected_result
    
    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async methods."""
        result = await self.instance.async_method()
        assert result is not None
    
    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ExpectedError):
            self.instance.method_that_should_fail("bad_input")
```

#### Test Coverage
- Write tests for all new functionality
- Aim for high test coverage on critical paths
- Include edge cases and error conditions
- Mock external dependencies (APIs, databases)

## 🏗️ Project Structure

Understanding the codebase structure:

```
slinkbot/
├── commands/          # Discord slash commands
│   ├── __init__.py
│   ├── advanced_commands.py    # Complex command implementations
│   ├── quick_sync.py          # Command synchronization
│   └── request_commands.py    # Basic request commands
├── config/           # Configuration management
│   ├── settings.py           # Main configuration classes
│   └── examples.env         # Environment template
├── database/         # Database layer
│   └── models.py            # SQLAlchemy models
├── managers/         # Business logic
│   ├── health_manager.py    # Service health monitoring
│   └── request_manager.py   # Request processing logic
├── notifications/    # Discord notifications
│   └── enhanced_notifier.py # Notification system
├── services/         # External API integrations
│   ├── base.py              # Base service class
│   └── jellyseerr.py       # Jellyseerr API client
├── utils/           # Utility functions
│   ├── database_session.py  # DB session management
│   ├── error_handling.py   # Error handling utilities
│   ├── logging_config.py   # Logging configuration
│   └── status_manager.py   # Request status management
└── slinkbot.py      # Main application entry point
```

### Adding New Features

#### New Commands
1. Add command logic to appropriate file in `commands/`
2. Register command in `slinkbot.py`
3. Add tests in `tests/`
4. Update documentation

#### New Services
1. Create service class inheriting from `BaseService`
2. Implement required methods
3. Add configuration options
4. Add health checks
5. Write comprehensive tests

#### New Utilities
1. Add to appropriate file in `utils/`
2. Follow existing patterns
3. Include comprehensive docstrings
4. Add unit tests

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_specific_feature.py

# Run tests matching pattern
pytest -k "test_request"
```

### Test Categories

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test component interactions
- **API Tests**: Test external service integrations
- **End-to-End Tests**: Test complete workflows

## 📚 Documentation

### Code Documentation
- Use clear, descriptive docstrings
- Include parameter types and return values
- Document exceptions that may be raised
- Provide usage examples for complex functions

### README Updates
When adding features, update:
- Feature list
- Configuration options
- Usage examples
- Installation instructions (if changed)

## 🔄 Release Process

### Version Numbering
We follow semantic versioning (SemVer):
- `MAJOR.MINOR.PATCH` (e.g., 1.2.3)
- Alpha/Beta releases: `Alpha v0.1.0`, `Beta v1.0.0`

### Changelog
Update `CHANGELOG.md` with:
- New features
- Bug fixes
- Breaking changes
- Migration notes

## 🤝 Community Guidelines

### Communication
- Be respectful and constructive
- Use clear, descriptive language
- Provide context for technical discussions
- Help others learn and grow

### Code Review
- Review code thoroughly but kindly
- Suggest improvements with explanations
- Test changes locally when possible
- Focus on code quality and maintainability

### Recognition
Contributors will be recognized in:
- Release notes for significant contributions
- Contributors section (if added)
- Special mentions for outstanding help

## ❓ Questions and Support

### Getting Help
- **GitHub Issues**: For bugs and feature requests
- **Discussions**: For general questions and ideas
- **Documentation**: Check existing docs first
- **Code Comments**: Look for inline explanations

### Maintainer Response Time
- Issues: Usually within 48 hours
- Pull Requests: Within 1 week for initial review
- Critical bugs: Within 24 hours

## 📋 Checklist for Contributors

Before submitting your contribution:

- [ ] Code follows style guidelines
- [ ] Tests are included and passing
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No sensitive information in code
- [ ] Feature is backward compatible (or migration provided)
- [ ] Error handling is comprehensive
- [ ] Logging is appropriate

Thank you for contributing to SlinkBot! Your efforts help make this project better for everyone. 🎉