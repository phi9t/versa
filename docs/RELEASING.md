# Releasing Versa

## Prerequisites

- All changes merged to `main`
- `pyproject.toml` `version` matches the tag you will push (e.g. `0.1.0` → tag `v0.1.0`)
- `CHANGELOG.md` updated under a new `## [x.y.z]` section

## Cut a release

```bash
# 1. Bump version in pyproject.toml and CHANGELOG.md, commit on main
git checkout main
git pull

# 2. Tag and push (triggers .github/workflows/release.yml)
git tag -a v0.1.0 -m "v0.1.0"
git push origin main
git push origin v0.1.0
```

GitHub Actions will:

1. Verify the tag matches `pyproject.toml` version
2. Run unit tests (`pytest -m "not integration"`)
3. Build wheel + sdist
4. Publish a [GitHub Release](https://github.com/phi9t/versa/releases) with attached artifacts

## Install from a release

```bash
pip install https://github.com/phi9t/versa/releases/download/v0.1.0/versa-0.1.0-py3-none-any.whl
```

Or from source:

```bash
git clone https://github.com/phi9t/versa.git
cd versa
git checkout v0.1.0
pip install .
```

## CI

Every push to `main` and every pull request runs `.github/workflows/ci.yml` (Python 3.12–3.14, unit tests only).
