#!/usr/bin/env python3
"""Sync pixi dependency versions from Kaggle+Colab requirement snapshots, to
keep mostly up-to-date.

This script updates only packages explicitly declared under
[feature.kaggle.dependencies] in pixi.toml.

NOTE 2026-02-26: We are basing requirements off of the Dockerfile at
https://github.com/Kaggle/docker-python/blob/main/Dockerfile.tmpl

Permalink at time of reference:
https://github.com/Kaggle/docker-python/blob/eb7204008d3d05708dd06d89dadb58c3aa4eb07c/Dockerfile.tmpl

It says:

```
# Merge requirements files:
RUN cat /colab_requirements.txt >> /requirements.txt
RUN cat /kaggle_requirements.txt >> /requirements.txt

Install Kaggle packages
RUN uv pip install --system --no-cache -r /requirements.txt
```

So we have kaggle override colab.

There's also some manual package installation afterwards which doesn't overlap
with our requirements, so we ignore that.
"""

from __future__ import annotations

import io
from pathlib import Path

import requests
import requirements
from tomlkit import dumps, parse
from tomlkit.items import Table as TomlTable
from tomlkit.toml_document import TOMLDocument

# ipython==7.34.0 (from Kaggle) is not available for osx-arm64, which makes
# pixi solves fail in this multi-platform project. Keep ipython out of sync and
# leave it unconstrained in pixi.toml.
EXEMPT_FROM_SYNC = {"ipython"}


def parse_pins(text: str) -> dict[str, str]:
    """Grab the dependency specifiers from a requirements.txt file.

    If a requirement is specified multiple times, the last one wins.
    """
    pins: dict[str, str] = {}
    for req in requirements.parse(io.StringIO(text)):
        if not req.name:
            continue
        if req.specs:
            pins[req.name] = ",".join(f"{op}{ver}" for op, ver in req.specs)
        else:
            pins[req.name] = "*"
    return pins


def sync_pixi_deps(
    deps_table: TomlTable,
    merged_pins: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Diff the dependencies in pixi.toml vs. what's nominally specified for Kaggle."""
    updates: dict[str, str] = {}
    missing = []

    for dep_name in deps_table.keys():
        if dep_name in EXEMPT_FROM_SYNC:
            continue
        current_spec = str(deps_table[dep_name])

        version = merged_pins.get(dep_name)
        if version is None:
            missing.append(dep_name)
            continue

        new_spec = version
        if current_spec == new_spec:
            continue

        updates[dep_name] = new_spec

    return updates, missing


def main() -> None:
    """Sync the dependencies.

    1. Get the upstream dependencies.
    2. Read the existing dependencies.
    3. For explicit dependencies, update the version.
    4. Write em back out.
    """
    kaggle_text = requests.get(
        "https://raw.githubusercontent.com/Kaggle/docker-python/main/kaggle_requirements.txt",
        timeout=30,
    ).text
    colab_text = requests.get(
        "https://raw.githubusercontent.com/googlecolab/backend-info/main/pip-freeze.txt",
        timeout=30,
    ).text
    merged_pins = parse_pins("\n".join([colab_text, kaggle_text]))

    repo_root = Path(__file__).resolve().parents[1]
    pixi_path = repo_root / "pixi.toml"
    pixi_doc: TOMLDocument = parse(pixi_path.read_text())
    deps_table: TomlTable = pixi_doc["feature"]["kaggle"]["dependencies"]

    updates, missing = sync_pixi_deps(deps_table, merged_pins)
    for dep_name, new_spec in updates.items():
        deps_table[dep_name] = new_spec

    print(f"{updates=}\n{missing=}")

    rendered = dumps(pixi_doc)
    if rendered != pixi_path.read_text(encoding="utf-8"):
        pixi_path.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
