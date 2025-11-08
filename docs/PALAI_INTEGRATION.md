# Pal.AI Agent Integration Guide

This document explains the Pal.AI agent commands integrated into the MCP Kali Server CI/CD pipeline.

## Overview

Pal.AI provides AI-powered code analysis, documentation, security scanning, and refactoring capabilities integrated directly into our GitHub Actions workflows.

## Available Commands

### 📚 Document Command

Automatically generate documentation and comments for your code.

**Aliases:** `doc`, `d`

**Flavors:**
- `standard` (default) - Standard documentation with function/class level comments
- `line-by-line` - Add detailed inline comments for complex logic
- `verbose` - Comprehensive documentation with examples and edge cases

**Usage:**
```bash
# Local usage (when pal.ai CLI is installed)
palai document kali_server.py
palai document --flavor line-by-line mcp_server.py
palai doc -f verbose test_basic.py
```

**CI/CD Integration:**
- Runs automatically on pull requests
- Can be triggered manually via workflow dispatch

---

### 💡 Explain Command

Explain code logic, structure, and behavior.

**Aliases:** `exp`, `e`

**What it does:**
- Analyzes code logic and flow
- Explains data structures and patterns
- Describes runtime behavior
- Identifies design patterns used

**Usage:**
```bash
palai explain kali_server.py
palai exp mcp_server.py
```

**CI/CD Integration:**
- Manual trigger via workflow dispatch

---

### 📊 Analyze Command

Compute Big-O space and time complexity of your code.

**Aliases:** `a`

**What it analyzes:**
- Time complexity (Big-O notation)
- Space complexity
- Performance bottlenecks
- Algorithmic efficiency

**Usage:**
```bash
palai analyze kali_server.py
palai a mcp_server.py
```

**CI/CD Integration:**
- Runs automatically on pull requests
- Integrated into the main CI pipeline

---

### 🔒 Scan Command

Scan your code for potential vulnerabilities and security issues.

**Aliases:** `s`

**Security checks:**
- SQL injection vulnerabilities
- XSS (Cross-Site Scripting)
- Command injection
- Path traversal
- Insecure deserialization
- Hardcoded secrets

**Usage:**
```bash
palai scan kali_server.py
palai s mcp_server.py
```

**CI/CD Integration:**
- Runs automatically on push events
- Integrated into the security scanning job
- Results uploaded as artifacts

---

### ✅ Review Command

Provide a full code review with best practices, suggestions, and maintainability insights.

**Aliases:** `r`

**Review areas:**
- Best practices adherence
- Code maintainability
- Performance optimization opportunities
- Security considerations
- Style guide compliance (PEP 8)

**Usage:**
```bash
palai review kali_server.py
palai r mcp_server.py
```

**CI/CD Integration:**
- Runs automatically on pull requests
- Results uploaded as artifacts

---

### ♻️ Rephrase Command

Rephrase your code: alter names, comments, and structure while preserving functionality.

**Aliases:** `rep`

**What it modifies:**
- Variable and function names
- Code comments
- Code structure and organization
- Maintains original logic and behavior

**Usage:**
```bash
palai rephrase kali_server.py
palai rep mcp_server.py
```

**CI/CD Integration:**
- Manual trigger via workflow dispatch

---

### 🎯 Simplify Command

Convert complex code into a more readable or simplified version.

**Aliases:** `sim`

**Simplification targets:**
- Overly complex functions
- Nested conditionals
- Long methods
- Difficult-to-read logic

**Usage:**
```bash
palai simplify kali_server.py
palai sim mcp_server.py
```

**CI/CD Integration:**
- Manual trigger via workflow dispatch

---

### 🔧 Fix Command

Fix issues in your code. You provide a description of what needs fixing.

**Aliases:** `f`

**Can fix:**
- Syntax errors
- Type errors
- Security issues
- Style violations

**Usage:**
```bash
palai fix kali_server.py --description "Fix SQL injection vulnerability"
palai f mcp_server.py --description "Resolve type hints"
```

**CI/CD Integration:**
- Manual trigger via workflow dispatch

---

### 🏗️ Refactor Command

Improve readability, maintainability, or structure of code.

**Aliases:** `ref`

**Refactoring focus:**
- Code readability
- Maintainability improvements
- Performance optimization
- Security enhancements

**Usage:**
```bash
palai refactor kali_server.py
palai ref mcp_server.py
```

**CI/CD Integration:**
- Manual trigger via workflow dispatch

---

### 📋 Cheatsheet Command

Show a quick commands reference.

**Aliases:** `cs`

**Usage:**
```bash
palai cheatsheet
palai cs
```

**CI/CD Integration:**
- Manual trigger via workflow dispatch

---

## CI/CD Workflows

### Automated Workflow (palai-agent.yml)

The dedicated Pal.AI workflow runs various commands automatically:

**Triggers:**
- **Push to main/claude branches:** Runs security scan
- **Pull requests:** Runs documentation, analysis, and review
- **Manual dispatch:** Can run any command on demand

### Integrated into Main CI Pipeline

Key Pal.AI commands are integrated into the main CI pipeline:

**In the `lint-and-test` job:**
- Complexity analysis (after tests)
- Code review (after tests)

**In the `security` job:**
- Security vulnerability scan (alongside Bandit)

---

## Manual Workflow Triggers

You can manually trigger Pal.AI commands via GitHub Actions:

1. Go to **Actions** tab in GitHub
2. Select **Pal.AI Agent Commands** workflow
3. Click **Run workflow**
4. Choose the command to run
5. Select flavor (if applicable for document command)
6. Click **Run workflow**

---

## Configuration

The Pal.AI integration is configured in `.palai.yml`:

```yaml
project:
  name: "MCP Kali Server"
  language: python
  version: "3.11"

targets:
  include:
    - "kali_server.py"
    - "mcp_server.py"
    - "test_basic.py"

commands:
  scan:
    enabled: true
    severity_threshold: "medium"

  review:
    enabled: true
    style_guide: "pep8"
```

---

## Installation (Local Development)

To use Pal.AI commands locally:

```bash
# Install Pal.AI CLI (placeholder - replace with actual command)
pip install palai-cli

# Verify installation
palai --version

# Run commands
palai scan kali_server.py
palai review mcp_server.py
```

---

## Artifacts and Reports

Pal.AI generates reports that are uploaded as GitHub Actions artifacts:

- **Security Scan Results:** `palai-security-scan`
- **Code Review Results:** `palai-code-review`

Access artifacts:
1. Go to the workflow run
2. Scroll to **Artifacts** section
3. Download the reports

---

## Best Practices

1. **Review AI Suggestions:** Always review AI-generated suggestions before applying
2. **Security Scans:** Run security scans before merging critical changes
3. **Documentation:** Use verbose flavor for complex algorithms
4. **Code Reviews:** Leverage automated reviews as a first pass, not a replacement for human review
5. **Refactoring:** Test thoroughly after AI-suggested refactoring

---

## Troubleshooting

### Command Not Found

If you see "command not found" errors:
- Ensure Pal.AI CLI is installed: `pip install palai-cli`
- Check PATH configuration
- Verify Python environment is activated

### Configuration Issues

If commands fail:
- Check `.palai.yml` syntax
- Verify file paths in `targets.include`
- Ensure correct permissions

### CI/CD Failures

If workflows fail:
- Check workflow logs in GitHub Actions
- Verify all required secrets are configured
- Ensure branch protection rules allow the workflow

---

## Support and Documentation

- **Pal.AI Documentation:** [pal.ai/docs](https://pal.ai/docs)
- **GitHub Issues:** Report integration issues in this repository
- **Configuration Reference:** See `.palai.yml` for all options

---

## Automated Security Fix Workflow

### `cp assign` Command

The Pal.AI Agent can automatically generate fixes for security vulnerabilities using the `cp assign` command.

**How it works:**

1. **Security Issue Detection:** A security vulnerability is identified (manually or via scanning)
2. **Create Issue:** Use the "Security Vulnerability" issue template
3. **Trigger Auto-Fix:** Comment `cp assign` on the issue
4. **Agent Analysis:** Pal.AI Agent analyzes the vulnerability
5. **PR Generation:** Agent creates a pull request with proposed fix
6. **Human Review:** Review the generated PR before merging

**Example Workflow:**

```bash
# Step 1: Scanner finds vulnerability
Issue #123 created: "SQL Injection in kali_server.py line 142"
Label: security-vuln

# Step 2: Comment on issue
cp assign implement fix for SQL injection in database query

# Step 3: Pal.AI Agent responds
- Scans the code
- Identifies vulnerable code patterns
- Generates secure replacement code
- Creates PR #124
- Comments on issue with PR link

# Step 4: Review and merge
- Review PR #124
- Verify fix addresses vulnerability
- Check tests pass
- Merge when satisfied
```

**Advanced Usage:**

```bash
# Auto-fix with specific context
cp assign implement fix for buffer overflow in module X

# Fix with additional requirements
cp assign fix authentication bypass and add input validation

# Chain with labeling
# When issue is labeled 'security-vuln', auto-scan triggers
# Then comment 'cp assign' to generate fix
```

### Workflow Metrics & Feedback Loop

The integration tracks important metrics:

- **Time to PR:** Issue creation → PR generation time
- **Fix Accuracy:** Percentage of auto-fixes that merge without changes
- **Human Intervention:** How often manual changes are needed
- **Severity Distribution:** Types and severity of auto-fixed issues

**Monitoring Dashboard (Planned):**
- Track automated fix success rate
- Identify patterns in vulnerability types
- Measure time savings from automation

### Permissions & Setup

**Required Permissions:**
- Agent needs rights to create PRs
- Agent needs rights to assign issues
- Repository write access for automated commits

**Configuration:**
```yaml
# .palai.yml
ci_integration:
  auto_fix:
    enabled: true
    require_label: "security-vuln"
    auto_assign: true
    create_pr: true
```

### Security Considerations

**Important Notes:**
- **Human Review Required:** Always review AI-generated fixes
- **Test Coverage:** Ensure tests verify the fix
- **Security Verification:** Re-scan after fix is applied
- **No Auto-Merge:** Require manual approval before merging
- **Audit Trail:** All automated fixes are logged and tracked

### Limitations

- Documentation is light on supported issue types (test on your repos)
- Agent capabilities depend on vulnerability complexity
- Some vulnerabilities require manual intervention
- Not all security issues can be automatically fixed

---

## Future Enhancements

Planned improvements for Pal.AI integration:

- [x] Automatic PR generation for security issues
- [x] `cp assign` command support
- [x] Security issue templates
- [ ] Automatic PR comments with review results
- [ ] Custom rules for security scanning
- [ ] Integration with code coverage reports
- [ ] Automated refactoring suggestions in PRs
- [ ] Performance regression detection
- [ ] Custom training on project-specific patterns
- [ ] Metrics dashboard for fix accuracy tracking
- [ ] Integration with SIEM/monitoring tools

---

## License

This integration is part of the MCP Kali Server project and follows the same MIT License.
