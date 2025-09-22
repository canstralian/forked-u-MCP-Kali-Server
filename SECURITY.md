# CI/CD and Security

This repository implements comprehensive CI/CD workflows with security analysis using GitHub Actions.

## Workflows

### CodeQL Security Analysis (`.github/workflows/codeql.yml`)
- **Triggers**: Push to main/master, pull requests, weekly schedule
- **Languages**: Python
- **Features**:
  - Secure dependency installation with hash verification
  - Code quality checks (flake8, black, mypy)
  - Security scanning (bandit, safety)
  - CodeQL analysis focused on `models/` directory
  - SARIF results upload to GitHub Security tab

### Continuous Integration (`.github/workflows/ci.yml`)
- **Triggers**: Push to main/master, pull requests
- **Matrix**: Python 3.9, 3.10, 3.11, 3.12
- **Features**:
  - Unit testing with pytest
  - Code coverage reporting
  - Security scanning with multiple tools
  - Artifact upload for security reports

## Security Tools

### Static Analysis
- **flake8**: Python linting for syntax errors and code style
- **black**: Code formatting enforcement
- **mypy**: Static type checking
- **bandit**: Security vulnerability scanning for Python
- **safety**: Dependency vulnerability scanning
- **semgrep**: Advanced security pattern matching
- **CodeQL**: GitHub's semantic code analysis

### Dependency Management
- **Dependabot**: Automated dependency updates
- **Requirements**: Pinned versions with security constraints
- **Safety**: Continuous vulnerability monitoring

## Configuration Files

- `pyproject.toml`: Project configuration and tool settings
- `.github/codeql/codeql-config.yml`: CodeQL analysis configuration
- `.github/dependabot.yml`: Automated dependency updates
- `requirements.txt`: Python dependencies with security constraints

## Security Best Practices

1. **Action Versions**: All GitHub Actions pinned to specific versions
2. **Permissions**: Minimal required permissions for each workflow
3. **Secrets**: No hardcoded secrets in code
4. **Dependencies**: Regular updates with security scanning
5. **Code Analysis**: Multi-tool approach for comprehensive coverage

## Local Development

Install development dependencies:
```bash
pip install -r requirements.txt
```

Run linting and tests:
```bash
flake8 .
black --check .
mypy models/
pytest
```

Run security scans:
```bash
bandit -r .
safety check
```