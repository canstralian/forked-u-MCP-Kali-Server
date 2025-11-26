# Contributing to MCP Kali Server

Thank you for considering contributing to the MCP Kali Server project! This document provides guidelines for contributing to the project.

## Code of Conduct

### Our Pledge

This project is intended for **educational and ethical security testing only**. By contributing, you agree to:
- Use the software responsibly and legally
- Follow ethical hacking principles
- Respect the security and privacy of others
- Not promote or enable malicious activities

## How to Contribute

### Reporting Issues

Before creating an issue:
1. Check if the issue already exists
2. Use the latest version of the code
3. Provide detailed information

**Issue Template:**
```
**Description:**
Brief description of the issue

**Steps to Reproduce:**
1. Step 1
2. Step 2
3. ...

**Expected Behavior:**
What you expected to happen

**Actual Behavior:**
What actually happened

**Environment:**
- OS: [e.g., Kali Linux 2024.1]
- Python Version: [e.g., 3.11]
- Installation Method: [Docker/Native]

**Additional Context:**
Any other relevant information
```

### Suggesting Features

Feature requests are welcome! Please include:
- Clear description of the feature
- Use cases and benefits
- Potential implementation approach
- Any security considerations

### Security Vulnerabilities

**Do NOT report security vulnerabilities as public issues.**

See [SECURITY.md](SECURITY.md) for vulnerability reporting procedures.

## Development Process

### Setting Up Development Environment

1. **Fork and clone the repository:**
```bash
git clone https://github.com/YOUR_USERNAME/forked-u-MCP-Kali-Server.git
cd forked-u-MCP-Kali-Server
```

2. **Create a virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install pylint flake8 bandit pytest black isort
```

4. **Install pre-commit hooks (optional but recommended):**
```bash
pip install pre-commit
pre-commit install
```

### Making Changes

1. **Create a feature branch:**
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make your changes:**
   - Write clear, readable code
   - Follow the existing code style
   - Add comments for complex logic
   - Update documentation as needed

3. **Write tests:**
   - Add unit tests for new features
   - Ensure existing tests pass
   - Aim for good test coverage

4. **Run quality checks:**
```bash
# Format code
black .
isort .

# Lint code
flake8 .
pylint *.py

# Security scan
bandit -r .

# Run tests
pytest -v
```

### Commit Guidelines

**Commit Message Format:**
```
type: brief description

Detailed explanation if needed

Fixes #issue_number
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `security`: Security improvements

**Examples:**
```
feat: add support for additional nmap scan types

Add support for UDP scans and service version detection
in the nmap endpoint.

Fixes #42
```

```
fix: prevent command injection in gobuster endpoint

Sanitize user input to prevent shell command injection
vulnerabilities.

Security: HIGH
```

### Pull Request Process

1. **Update documentation:**
   - Update README.md if needed
   - Add entry to CHANGELOG.md
   - Update API documentation

2. **Ensure quality:**
   - All tests pass
   - No linting errors
   - Security scans pass
   - Code is formatted consistently

3. **Create pull request:**
   - Use a clear, descriptive title
   - Reference related issues
   - Describe changes in detail
   - Explain testing performed

4. **Pull Request Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Security improvement
- [ ] Documentation update
- [ ] Code refactoring

## Testing
Describe testing performed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] No new warnings
- [ ] CHANGELOG.md updated

## Related Issues
Fixes #issue_number
```

5. **Review process:**
   - Respond to review comments
   - Make requested changes
   - Be patient and respectful

## Code Style Guidelines

### Python Style

Follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with these specifics:

**Formatting:**
- Line length: 120 characters maximum
- Indentation: 4 spaces (no tabs)
- Use Black for automatic formatting
- Use isort for import sorting

**Naming Conventions:**
```python
# Classes: PascalCase
class KaliToolsClient:
    pass

# Functions and variables: snake_case
def execute_command(command_str):
    result_data = {}
    return result_data

# Constants: UPPER_SNAKE_CASE
DEFAULT_TIMEOUT = 300
API_PORT = 5000

# Private methods: _leading_underscore
def _internal_helper():
    pass
```

**Type Hints:**
```python
from typing import Dict, Any, Optional

def process_data(
    input_data: Dict[str, Any],
    timeout: int = 300
) -> Optional[Dict[str, Any]]:
    """Process input data with timeout."""
    pass
```

**Docstrings:**
```python
def example_function(param1: str, param2: int = 0) -> Dict[str, Any]:
    """
    Brief description of function.
    
    More detailed explanation if needed. This can span
    multiple lines.
    
    Args:
        param1: Description of param1
        param2: Description of param2 (default: 0)
        
    Returns:
        Dictionary containing results
        
    Raises:
        ValueError: If param1 is empty
        ConnectionError: If server is unreachable
    """
    pass
```

### Security Guidelines

**Input Validation:**
```python
# Always validate and sanitize user input
def safe_command(user_input: str) -> str:
    # Validate input
    if not user_input:
        raise ValueError("Input cannot be empty")
    
    # Sanitize
    allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./")
    if not all(c in allowed_chars for c in user_input):
        raise ValueError("Invalid characters in input")
    
    return user_input
```

**Error Handling:**
```python
# Don't expose sensitive information in error messages
try:
    result = execute_sensitive_operation()
except Exception as e:
    logger.error(f"Operation failed: {str(e)}")
    return {"error": "Operation failed"}  # Generic message to user
```

**Logging:**
```python
# Be careful with logging sensitive data
logger.info(f"User {username} executed command")  # OK
logger.info(f"Password: {password}")  # NEVER DO THIS
```

## Testing Guidelines

### Test Structure

```python
import pytest

class TestFeatureName:
    """Test suite for feature"""
    
    def test_basic_functionality(self):
        """Test basic use case"""
        result = function_under_test()
        assert result == expected_value
    
    def test_edge_case(self):
        """Test edge case"""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest test_basic.py

# Run with verbose output
pytest -v
```

## Documentation

### README Updates

When adding features, update the README.md with:
- Feature description
- Usage examples
- Configuration options
- Any new dependencies

### Code Comments

```python
# Good: Explains WHY
# Using exponential backoff to handle rate limiting
time.sleep(2 ** retry_count)

# Bad: Explains WHAT (obvious from code)
# Increment counter
counter += 1
```

## Release Process

### Version Numbers

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR.MINOR.PATCH** (e.g., 1.2.3)
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Creating a Release

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create git tag
4. Create GitHub release
5. Update documentation

## Getting Help

- **Issues:** For bug reports and feature requests
- **Discussions:** For questions and general discussion
- **Documentation:** Check README.md and docs/

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- GitHub contributors page
- Release notes for major features

Thank you for contributing to MCP Kali Server! 🎉
