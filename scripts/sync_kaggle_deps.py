#!/usr/bin/env python3
"""Sync [feature.kaggle.dependencies] in pixi.toml from a real Kaggle run.

Workflow:
1. Read package names from [feature.kaggle.dependencies].
2. Create a temporary Kaggle script kernel that captures installed versions.
3. Push/run the kernel using Kaggle API credentials.
4. Download versions.json output.
5. Update pixi.toml dependency specs.
6. Delete the temporary kernel.

Authentication:
- Uses Kaggle CLI with token-based auth via `KAGGLE_API_TOKEN`.
- Username is discovered via `kaggle config view`.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tomlkit import dumps, parse
from tomlkit.items import Table as TomlTable
from tomlkit.toml_document import TOMLDocument


@dataclass(frozen=True)
class KernelRef:
    owner: str
    slug: str

    @property
    def full(self) -> str:
        return f"{self.owner}/{self.slug}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--exclude",
        nargs="*",
        default=[],
        help="Dependency names to skip when syncing.",
    )
    return parser.parse_args()


def main() -> None:
    """Orchestrate Kaggle dependency sync:

    * grab relevant packages from pixi.toml
    * try to get versions from Kaggle
    * overwrite existing versions in pixi.toml
    * report anything that we couldn't find
    """
    args = parse_args()
    exempt_from_sync = set(args.exclude)
    timeout_seconds = 2 * 60
    poll_seconds = 5

    repo_root = Path(__file__).resolve().parents[1]
    pixi_path = repo_root / "pixi.toml"
    pixi_doc: TOMLDocument = parse(pixi_path.read_text(encoding="utf-8"))
    deps_table: TomlTable = pixi_doc["feature"]["kaggle"]["dependencies"]

    package_names = sorted(
        str(name)
        for name in deps_table.keys()
        if name not in exempt_from_sync and name != "python"
    )
    probe_result = probe_kaggle_runtime_dependencies(
        owner=load_kaggle_username(),
        package_names=package_names,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )

    apply_kaggle_pins_to_pixi_deps(deps_table, probe_result, exempt_from_sync)

    rendered = dumps(pixi_doc)
    original = pixi_path.read_text(encoding="utf-8")
    if rendered != original:
        pixi_path.write_text(rendered, encoding="utf-8")

    missing_in_kaggle_runtime = probe_result.get("missing", [])
    print(f"missing_in_kaggle_runtime={missing_in_kaggle_runtime}")


def probe_kaggle_runtime_dependencies(
    owner: str,
    package_names: list[str],
    timeout_seconds: int,
    poll_seconds: int,
) -> dict[str, Any]:
    """Probe real Kaggle runtime dependency versions.

    Steps:
    1. Build a temporary script kernel that inspects installed package versions.
    2. Push the kernel to Kaggle and start the run.
    3. Poll until the run completes (or fails/times out).
    4. Download `versions.json` from kernel outputs.
    5. Delete the temporary kernel.
    """

    def _make_kernel_slug() -> str:
        ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        return f"pudl-dep-sync-{ts}"

    kernel_ref = KernelRef(owner=owner, slug=_make_kernel_slug())
    print(f"Using temporary Kaggle kernel: {kernel_ref.full}")

    probe_result: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="kaggle-dep-sync-") as td:
        tmp = Path(td)
        kernel_dir = tmp / "kernel"
        output_dir = tmp / "output"
        kernel_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        write_kernel_files(kernel_dir, kernel_ref, package_names)

        try:
            run_command(["kaggle", "kernels", "push", "-p", str(kernel_dir)])
            wait_for_completion(kernel_ref, timeout_seconds, poll_seconds)
            probe_result = download_versions_json(kernel_ref, output_dir)
        finally:
            delete_kernel(kernel_ref)

    return probe_result


def apply_kaggle_pins_to_pixi_deps(
    deps_table: TomlTable,
    probe_result: dict[str, Any],
    exempt_from_sync: set[str],
) -> None:
    """Clobber existing dependencies with whatever came from Kaggle.

    Note that this *mutates* the deps_table and thus the pixi_doc. Which means
    we can just write pixi_doc after we call this.
    """
    kaggle_pins = probe_result["pins"]
    kaggle_pins["python"] = f"=={probe_result['python_version']}"

    for dep_name in deps_table.keys():
        if dep_name in exempt_from_sync:
            continue

        new_spec = kaggle_pins.get(dep_name)
        if new_spec is None:
            continue

        deps_table[dep_name] = new_spec


def load_kaggle_username() -> str:
    """Get Kaggle username from `kaggle config view` output."""
    if not os.environ.get("KAGGLE_API_TOKEN"):
        raise RuntimeError("KAGGLE_API_TOKEN is required for auth.")

    output = run_command(["kaggle", "config", "view"])
    username_line = next(line for line in output.splitlines() if "username:" in line)
    return username_line.split(":", 1)[1].strip()


def write_kernel_files(
    kernel_dir: Path, kernel_ref: KernelRef, package_names: list[str]
) -> None:
    """Set up input files for Kaggle CLI submission.

    * Write a script that grabs package versions + Python version from Kaggle
      env, and writes the versions to JSON
    * Make the metadata necessary to actually submit to Kaggle via CLI.
    """
    script_name = "probe_versions.py"
    metadata = {
        "id": kernel_ref.full,
        "title": kernel_ref.slug,
        "code_file": script_name,
        "language": "python",
        "kernel_type": "script",
    }
    payload = json.dumps(package_names, sort_keys=True)
    script_contents = f"""import json
import platform
from importlib.metadata import PackageNotFoundError, version

PACKAGES = {payload}

pins = {{}}
missing = []

for name in PACKAGES:
    try:
        pins[name] = f"=={{version(name)}}"
    except PackageNotFoundError:
        missing.append(name)

result = {{
    "pins": pins,
    "missing": sorted(missing),
    "python_version": platform.python_version(),
}}

with open("/kaggle/working/versions.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, sort_keys=True)
"""

    (kernel_dir / script_name).write_text(script_contents, encoding="utf-8")
    (kernel_dir / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )


def wait_for_completion(
    kernel_ref: KernelRef, timeout_seconds: int, poll_seconds: int
) -> None:
    """Poll Kaggle kernel status until it completes."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        status = run_command(["kaggle", "kernels", "status", kernel_ref.full])
        print(status)
        if "complete" in status.lower():
            return
        if "failed" in status.lower():
            raise RuntimeError(f"Kaggle kernel failed:\n{status.strip()}")
        time.sleep(poll_seconds)

    raise TimeoutError(
        f"Timed out waiting for {kernel_ref.full} after {timeout_seconds} seconds"
    )


def download_versions_json(kernel_ref: KernelRef, output_dir: Path) -> dict[str, Any]:
    """Download the outputs from the kernel as JSON."""
    print(f"Downloading versions.json from {kernel_ref.full}")
    run_command(
        [
            "kaggle",
            "kernels",
            "output",
            kernel_ref.full,
            "-p",
            str(output_dir),
            "--force",
        ]
    )
    versions_path = output_dir / "versions.json"
    print(f"Downloaded to {versions_path}")
    return json.loads(versions_path.read_text(encoding="utf-8"))


def delete_kernel(kernel_ref: KernelRef) -> None:
    print(f"Deleting temporary kernel: {kernel_ref.full}")
    run_command(["kaggle", "kernels", "delete", kernel_ref.full, "-y"])
    print(f"Deleted temporary kernel: {kernel_ref.full}")


def run_command(cmd: list[str], *, cwd: Path | None = None) -> str:
    """Run a command and return stdout."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        details = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{details}") from exc
    return proc.stdout


if __name__ == "__main__":
    main()
