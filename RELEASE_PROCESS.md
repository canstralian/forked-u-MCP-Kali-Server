# How to Create the v0.1.0 Release

This guide explains how to create and publish the v0.1.0 release of MCP Kali Server.

## Prerequisites

- All changes merged to main branch
- All tests passing
- Documentation reviewed and approved

## Steps to Release

### 1. Update Version Information

Verify version is set to `0.1.0` in:
- ✅ `pyproject.toml` (line 7)
- ✅ `CHANGELOG.md` (set release date)

### 2. Update CHANGELOG.md

Edit `CHANGELOG.md` and:
- Change `[Unreleased]` section to `[0.1.0] - YYYY-MM-DD`
- Add today's date
- Move any "Unreleased" items to the 0.1.0 section

Example:
```markdown
## [0.1.0] - 2024-10-02

### Added
- Initial release preparation
...
```

### 3. Commit Final Changes

```bash
git add CHANGELOG.md
git commit -m "Prepare for v0.1.0 release"
git push origin main
```

### 4. Create Git Tag

```bash
# Create annotated tag
git tag -a v0.1.0 -m "Release v0.1.0 - First official release"

# Push tag to GitHub
git push origin v0.1.0
```

### 5. GitHub Release Creation

The `release.yml` workflow will automatically:
- ✅ Run all tests
- ✅ Build Docker image
- ✅ Create GitHub Release
- ✅ Upload Docker image as artifact

**OR** Create manually:

1. Go to: https://github.com/canstralian/forked-u-MCP-Kali-Server/releases/new
2. Choose tag: `v0.1.0`
3. Release title: `v0.1.0 - First Official Release`
4. Copy content from `RELEASE_NOTES.md`
5. Attach Docker image (if built manually)
6. Click "Publish release"

### 6. Verify Release

Check that:
- [ ] Tag is visible on GitHub
- [ ] Release is published
- [ ] Docker image artifact is available
- [ ] Release notes are displayed correctly
- [ ] All links in release notes work

### 7. Announce Release

Consider announcing on:
- GitHub Discussions
- Project README (add release badge)
- Social media (if applicable)
- Related communities

## Post-Release Tasks

### 1. Create Next Version Section in CHANGELOG

```markdown
## [Unreleased]

### Added
- 

### Changed
- 

### Fixed
- 
```

### 2. Update Project Status

Update README.md badges if needed:
- Version badge
- Release status
- Build status

### 3. Plan Next Release

Start planning v0.2.0 features in:
- GitHub Issues
- Project boards
- CHANGELOG.md (Unreleased section)

## Rollback Procedure

If issues are found:

```bash
# Delete tag locally
git tag -d v0.1.0

# Delete tag remotely
git push origin :refs/tags/v0.1.0

# Delete GitHub release manually through web interface
```

## Docker Image Distribution

### Option 1: GitHub Release Artifact
- Available in release downloads
- Users: `docker load < mcp-kali-server-v0.1.0-docker.tar.gz`

### Option 2: Docker Hub (Future)
```bash
docker tag mcp-kali-server:0.1.0 username/mcp-kali-server:0.1.0
docker push username/mcp-kali-server:0.1.0
```

### Option 3: GitHub Container Registry (Future)
```bash
docker tag mcp-kali-server:0.1.0 ghcr.io/canstralian/mcp-kali-server:0.1.0
docker push ghcr.io/canstralian/mcp-kali-server:0.1.0
```

## Verification Checklist

Before releasing, verify:

- [ ] All CI/CD checks pass
- [ ] Tests pass (7/7 tests)
- [ ] Docker builds successfully
- [ ] Documentation is complete
- [ ] Security scans reviewed
- [ ] No sensitive data in commits
- [ ] License is correct
- [ ] Version numbers match
- [ ] CHANGELOG is updated
- [ ] Release notes prepared

## Notes

- This is an **alpha release** (v0.1.0)
- Breaking changes expected in future versions
- Semantic versioning will be followed
- Community feedback will shape v0.2.0

## Support

For questions about the release process:
- Open an issue on GitHub
- Check CONTRIBUTING.md
- Contact maintainers

---

**Last Updated:** 2024
**Next Review:** Before v0.2.0 release
