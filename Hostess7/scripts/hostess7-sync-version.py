#!/usr/bin/env python3
"""Sync version from src/hostess7/__init__.py → pyproject, compose, README, RELEASE."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "src" / "hostess7" / "__init__.py"
PYPROJECT = ROOT / "pyproject.toml"
COMPOSE = ROOT / "docker-compose.yml"
README = ROOT / "README.md"
DOCKERFILE = ROOT / "Dockerfile"


def read_version() -> str:
    text = INIT.read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        raise SystemExit(f"no __version__ in {INIT}")
    return m.group(1)


def sync_pyproject(version: str) -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    text = re.sub(r'^version = ".*"$', f'version = "{version}"', text, count=1, flags=re.M)
    PYPROJECT.write_text(text, encoding="utf-8")


def sync_compose(version: str) -> None:
    if not COMPOSE.is_file():
        return
    text = COMPOSE.read_text(encoding="utf-8")
    text = re.sub(r"image: hostess7:[^\s]+", f"image: hostess7:{version}", text)
    COMPOSE.write_text(text, encoding="utf-8")


def sync_readme(version: str) -> None:
    if not README.is_file():
        return
    text = README.read_text(encoding="utf-8")
    text = re.sub(r"Hostess 7 2\.0\.7[a-z]", f"Hostess 7 {version}", text, count=1)
    text = re.sub(r"\*\*Version:\*\* `2\.0\.7[a-z]`", f"**Version:** `{version}`", text, count=1)
    text = re.sub(
        r"\[RELEASE-2\.0\.7[a-z]\.md\]\(RELEASE-2\.0\.7[a-z]\.md\)",
        f"[RELEASE-{version}.md](RELEASE-{version}.md)",
        text,
        count=1,
    )
    README.write_text(text, encoding="utf-8")


def ensure_release_stub(version: str) -> Path:
    path = ROOT / f"RELEASE-{version}.md"
    if path.is_file():
        return path
    body = f"""# Hostess7 {version}

## Highlights

- Packaging paths hardened (env > package > dev tree > fallback)
- Unified `brain/state` with migration warnings + legacy prune
- Package `war_realism` + `amouranth_bridge` — OODA, ROE, pip-safe cohesion
- `hostess7-war-train` console entry · Docker war profile · CI war smoke

## Verify

```bash
pip install -e ".[dev]"
python scripts/hostess7-sync-version.py
hostess7-cohesion
hostess7-war-train wargame advanced
./Hostess7.sh war-panel
```

## RTX

RTX 1.0.7h release assets remain compatible — layer on top of this package.
"""
    path.write_text(body, encoding="utf-8")
    return path


def sync_dockerfile(version: str) -> None:
    if not DOCKERFILE.is_file():
        return
    text = DOCKERFILE.read_text(encoding="utf-8")
    if "HOSTESS7_WAR_PROFILE" not in text:
        text = text.replace(
            "HOSTESS7_LICENSE_MODE=war",
            "HOSTESS7_LICENSE_MODE=war \\\n    HOSTESS7_WAR_PROFILE=1",
        )
    DOCKERFILE.write_text(text, encoding="utf-8")


def main() -> int:
    version = read_version()
    sync_pyproject(version)
    sync_compose(version)
    sync_readme(version)
    ensure_release_stub(version)
    sync_dockerfile(version)
    print(f"synced {version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())