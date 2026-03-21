# Publishing to PyPI

This guide covers how to publish `mythril-agent-skills` to PyPI and how to test the package before release.

---

## Prerequisites

1. **PyPI account** — register at https://pypi.org/account/register/
2. **TestPyPI account** (optional) — register at https://test.pypi.org/account/register/
3. **API tokens**:
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/

---

## Authentication

The publish script resolves credentials in this order:

1. **Environment variable** (recommended for CI/CD)
2. **`~/.pypirc` config file** (recommended for local use)
3. **Interactive prompt** (fallback — script will ask you to paste the token)

### Option 1: Environment variables

| Target | Environment variable | How to get a token |
|---|---|---|
| PyPI | `PYPI_API_TOKEN` | https://pypi.org/manage/account/token/ |
| TestPyPI | `TEST_PYPI_API_TOKEN` | https://test.pypi.org/manage/account/token/ |

Add to your shell config (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export PYPI_API_TOKEN="pypi-xxxxxx..."
export TEST_PYPI_API_TOKEN="pypi-xxxxxx..."
```

Then reload: `source ~/.zshrc`

### Option 2: `~/.pypirc` config file

Create or edit `~/.pypirc`:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-<your-pypi-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-<your-testpypi-token>
```

### Option 3: Interactive prompt

If neither env var nor `.pypirc` is configured, the publish script will prompt you to paste a token at upload time. This is fine for one-off use but not recommended for repeated publishing.

---

## Version Management

The version is defined in **three files** — they must always match:

| File | Field |
|---|---|
| `pyproject.toml` | `version = "x.y.z"` |
| `mythril_agent_skills/__init__.py` | `__version__ = "x.y.z"` |
| `.claude-plugin/marketplace.json` | `"version": "x.y.z"` (all plugin entries) |

Use the bump script to update all files at once:

```bash
python3 scripts/bump-version.py 0.3.0    # set new version
python3 scripts/bump-version.py          # show current version
```

The publish script checks all three files for consistency and aborts if any version is out of sync.

For the rationale behind unified versioning (no per-plugin versions), see [DEVELOPMENT.md — Versioning Strategy](./DEVELOPMENT.md#versioning-strategy).

Follow [Semantic Versioning](https://semver.org/):
- **Patch** (`0.1.0` → `0.1.1`): bug fixes, doc updates
- **Minor** (`0.1.0` → `0.2.0`): new skills, new features
- **Major** (`0.1.0` → `1.0.0`): breaking changes

> PyPI does not allow re-uploading the same version. Always bump the version before publishing.

---

## Publishing

### Publish to PyPI (production)

```bash
python3 scripts/publish.py
```

### Publish to TestPyPI (staging)

TestPyPI (`test.pypi.org`) is a separate, independent instance of PyPI for testing. It has its own accounts, tokens, and packages. Use it to verify the package before publishing to production — this avoids wasting a version number if something is wrong (PyPI does not allow re-uploading the same version).

```bash
python3 scripts/publish.py --test
```

### What the publish script does

1. **Version check** — verifies `pyproject.toml`, `__init__.py`, and `marketplace.json` versions all match
2. **Git status check** — warns if there are uncommitted changes
3. **Tool setup** — auto-installs `build` and `twine` if missing
4. **Clean** — removes old `dist/` artifacts
5. **Build** — creates sdist (`.tar.gz`) and wheel (`.whl`) in `dist/`
6. **Credential resolution** — env var → `~/.pypirc` → interactive prompt
7. **Upload** — uploads to PyPI or TestPyPI via `twine`

---

## Testing Before Release

### 1. Local development install

```bash
pip install -e .
```

Verify the CLI commands work:

```bash
skills-setup
skills-cleanup
skills-check gh-operations jira figma
```

### 2. Build and inspect locally

```bash
python3 -m build
```

Check the built package contents:

```bash
# List files in the sdist
tar tzf dist/mythril_agent_skills-*.tar.gz | head -30

# List files in the wheel
unzip -l dist/mythril_agent_skills-*.whl | head -30
```

Verify all skills are included:

```bash
tar tzf dist/mythril_agent_skills-*.tar.gz | grep SKILL.md
```

### 3. TestPyPI round-trip

Publish to TestPyPI:

```bash
python3 scripts/publish.py --test
```

Install from TestPyPI in a fresh virtual environment:

```bash
python3 -m venv /tmp/test-mas
source /tmp/test-mas/bin/activate
pip install -i https://test.pypi.org/simple/ mythril-agent-skills
```

Run the commands:

```bash
skills-setup
skills-cleanup
skills-check gh-operations
```

Clean up:

```bash
deactivate
rm -rf /tmp/test-mas
```

### 4. Post-publish verification

After publishing to production PyPI:

```bash
python3 -m venv /tmp/verify-mas
source /tmp/verify-mas/bin/activate
pip install mythril-agent-skills
skills-setup
deactivate
rm -rf /tmp/verify-mas
```

---

## Checklist

Before every release:

- [ ] Version bumped in all three files (`python3 scripts/bump-version.py <version>`)
- [ ] All changes committed and pushed
- [ ] `pip install -e .` works locally
- [ ] `skills-setup`, `skills-cleanup`, `skills-check` run correctly
- [ ] All skill `SKILL.md` files included in build (`tar tzf dist/*.tar.gz | grep SKILL.md`)
- [ ] (Optional) TestPyPI round-trip passed
- [ ] Git tag created: `git tag v<version> && git push origin v<version>`
