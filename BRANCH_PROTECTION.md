# Branch Protection Configuration

This document provides instructions for configuring branch protection rules for the `main` branch to ensure code quality and prevent accidental changes.

## Overview

Branch protection rules help maintain code quality by:
- Preventing force pushes and branch deletion
- Requiring status checks to pass before merging
- Requiring pull request reviews before merging
- Ensuring a clean commit history

## Recommended Settings for Main Branch

### Prerequisites
You must have admin access to the repository to configure branch protection rules.

### Configuration Steps

1. **Navigate to Branch Protection Settings**
   - Go to your repository on GitHub
   - Click on `Settings` → `Branches` → `Add branch protection rule`
   - Enter `main` in the "Branch name pattern" field

2. **Required Settings**

   #### Protect against force pushes and deletion
   - ✅ Enable "Lock branch" (read-only, prevents force pushes and deletion)
   - OR ✅ Enable "Do not allow force pushes" 
   - ✅ Enable "Do not allow deletions"

   #### Require status checks before merging
   - ✅ Enable "Require status checks to pass before merging"
   - ✅ Enable "Require branches to be up to date before merging"
   - Select the following required status checks:
     - `Lint and Test` (from CI Pipeline workflow - job: lint-and-test)
     - `Analyze` (from CodeQL Security Scan workflow - job: codeql)

   #### Recommended Additional Settings
   - ✅ Enable "Require a pull request before merging"
   - ✅ Set "Required number of approvals before merging" to at least 1
   - ✅ Enable "Dismiss stale pull request approvals when new commits are pushed"
   - ✅ Enable "Require review from Code Owners" (if CODEOWNERS file exists)
   - ✅ Enable "Require linear history" (prevents merge commits)
   - ✅ Enable "Require signed commits" (for additional security)
   - ✅ Include administrators in these restrictions

3. **Save Changes**
   - Click "Create" or "Save changes" at the bottom of the page

## Status Checks

The following GitHub Actions workflows provide status checks:

### CI Pipeline (`ci.yml`)
- **Job Name**: `Lint and Test` (job id: `lint-and-test`)
- **Checks**: Python linting (Pylint, Flake8), pytest tests, Docker build
- **Triggers**: Push to main, Pull requests to main

### CodeQL Security Scan (`codeql.yml`)
- **Job Name**: `Analyze` (job id: `codeql`)
- **Checks**: Security vulnerability scanning
- **Triggers**: Push to main, Pull requests to main, Weekly schedule

## Verification

After configuring branch protection, verify the settings by:

1. Attempting to push directly to main (should fail)
   ```bash
   git push origin main
   # Should return: "refusing to allow an integration to update main"
   ```

2. Creating a pull request and verifying that:
   - Status checks must pass before merging is allowed
   - The merge button is disabled until all checks pass
   - Force push protection is active

## Troubleshooting

### Status checks not appearing
- Ensure the workflows have run at least once on the main branch
- Check that workflow files are present in `.github/workflows/`
- Verify workflows are enabled in repository settings

### Unable to merge even with passing checks
- Check if administrators are included in restrictions
- Verify your account has necessary permissions
- Ensure all required status checks are passing

### Need to bypass protection temporarily
- Only repository administrators can temporarily disable protection rules
- This should be done sparingly and only for emergency situations
- Always re-enable protections immediately after

## Additional Resources

- [GitHub Branch Protection Documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Configuring Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)
- [GitHub Actions Status Checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks)

## Support

If you encounter issues with branch protection configuration, please:
1. Check this documentation for troubleshooting steps
2. Review GitHub's official documentation
3. Open an issue in this repository with details about the problem
