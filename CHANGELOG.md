# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Wireless Attack Stack Analysis Dashboard (HTML/Chart.js)
  - Interactive visualizations for tool categorization
  - Attack vector frequency analysis
  - Operational workflow diagram
  - Capability gap analysis with radar charts
- New API endpoints for reports:
  - `/api/reports` - List all available reports
  - `/api/reports/wireless-analysis` - Serve HTML dashboard
  - `/api/reports/wireless-analysis/data` - Serve JSON data
- Comprehensive documentation for wireless analysis (`docs/WIRELESS_ANALYSIS.md`)
- Structured data file (`docs/reports/wireless-analysis/data.json`)
- Reports directory structure (`docs/reports/`)
- Initial release preparation
- Comprehensive security documentation
- Environment configuration template (.env.example)
- Proper .gitignore for Python projects
- CHANGELOG.md for version tracking

### Changed
- Enhanced Flask server with report serving capabilities
- Added `send_from_directory` and `send_file` to Flask imports
- Code style improvements and linting fixes
- Enhanced documentation in README.md

### Security
- Added input validation guidelines
- Documented security best practices
- Added security scanning in CI pipeline

### Features
- Accessibility-compliant reporting (WCAG 2.1 AA)
- Responsive design for mobile, tablet, and desktop
- Print/Export functionality for reports
- Error handling for CDN failures
- Custom "Neon Night" theme for security tools visualization

## [0.1.0] - TBD

### Added
- MCP Server integration with Kali Linux tools
- API endpoints for security tools (nmap, gobuster, nikto, sqlmap, etc.)
- Command execution framework with timeout management
- Health check endpoint
- CI/CD pipeline with GitHub Actions
- CodeQL security scanning
- Docker support
- Comprehensive README with installation and usage instructions

### Features
- AI-assisted penetration testing capabilities
- Integration with MCP clients (Claude Desktop, 5ire)
- Support for multiple security tools:
  - Network scanning (nmap)
  - Directory enumeration (gobuster, dirb)
  - Web vulnerability scanning (nikto, sqlmap, wpscan)
  - Password cracking (hydra, john)
  - SMB enumeration (enum4linux)
  - Metasploit integration

### Security
- MIT License
- Educational and ethical testing purpose only
- Command execution with proper timeout handling
- Logging and monitoring capabilities

[Unreleased]: https://github.com/canstralian/forked-u-MCP-Kali-Server/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/canstralian/forked-u-MCP-Kali-Server/releases/tag/v0.1.0
