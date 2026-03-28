# CI/CD Plan for python-trader / ShoonyaApi-py

## 📋 Project Summary

- **Repo**: `github.com/venkatseshadri/python-trader`
- **Test Framework**: pytest (20 passed, 8 skipped)
- **Language**: Python 3
- **Key Dependency**: Custom wheel (`NorenRestApi-0.0.30-py2.py3-none-any.whl`)

---

## 🎯 CI/CD Goals

| Goal | Priority | Description |
|------|----------|-------------|
| Automated Tests | 🔴 High | Run unit tests on every push |
| Lint & Format | 🟡 Medium | Code quality checks |
| Security Scan | 🟡 Medium | Detect vulnerabilities |
| Publish to PyPI | 🟢 Low | Auto-publish releases |

---

## 🚀 Recommended: GitHub Actions Workflows

### Option 1: Basic CI (Recommended Start)
**File**: `.github/workflows/test.yml`

```yaml
name: Test

on:
  push:
    branches: [main, master]
  pull_request:
    branches: [main, master]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
          
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
          pip install ./ShoonyaApi-py/dist/NorenRestApi-0.0.30-py2.py3-none-any.whl
          
      - name: Run unit tests
        working-directory: ./ShoonyaApi-py
        run: pytest tests/ -m "not integration" -v
        
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

### Option 2: Full CI with Quality Gates
**File**: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main, master]
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install ruff
      - run: ruff check ShoonyaApi-py/

  test:
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ['3.10', '3.11', '3.12']
      - name: Install deps
        run: |
          pip install pytest pytest-cov
          pip install -r ShoonyaApi-py/requirements.txt || true
          pip install ShoonyaApi-py/dist/NorenRestApi-*.whl
      - name: Run tests
        working-directory: ShoonyaApi-py
        run: pytest tests/ -m "not integration" -v --cov=. --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v4

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: pip install safety
      - run: safety check || true
```

### Option 3: Release Pipeline (Optional)
**File**: `.github/workflows/release.yml`

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Build package
        run: |
          pip install build
          python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```

---

## 📦 Files to Create

| File | Purpose |
|------|---------|
| `.github/workflows/test.yml` | Basic test automation |
| `.github/workflows/ci.yml` | Full CI with lint + tests |
| `.github/workflows/release.yml` | Auto-publish on tags |
| `.github/dependabot.yml` | Auto-update dependencies |

---

## 🛡️ Security Considerations

1. **Secrets**: Never commit credentials to repo
2. **Use**: `cred.yml.example` as template
3. **CI Secrets**: Add these in GitHub repo Settings → Secrets:
   - `PYPI_API_TOKEN` (for releases)
   - `CODECOV_TOKEN` (optional)

---

## ⏱️ Time Estimate

| Task | Effort |
|------|--------|
| Basic workflow | 10 min |
| Full CI workflow | 30 min |
| Release workflow | 20 min |
| Testing & debugging | 30 min |

---

## ✅ Action Items

- [ ] Create `.github/workflows/test.yml`
- [ ] Add pytest-cov to requirements
- [ ] Configure Codecov (optional, free for public repos)
- [ ] Test workflow on a branch
- [ ] Add badges to README.md
- [ ] (Optional) Set up Dependabot
- [ ] (Optional) Add release workflow

---

## 📖 References

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [PyPA Publishing](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
