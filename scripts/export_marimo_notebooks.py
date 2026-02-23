#!/usr/bin/env python3
"""Export all marimo notebooks in a directory to WebAssembly."""

import argparse
import subprocess
import sys
from pathlib import Path


def export_notebooks(source_dir: Path, target_dir: Path) -> None:
    """Export marimo notebooks to wasm, retaining directory structure.

    Args:
        source_dir: Directory containing marimo notebook .py files.
        target_dir: Directory to write exported .html files.
    """
    notebooks = sorted(source_dir.rglob("*.py"))
    if not notebooks:
        raise RuntimeError(f"No marimo notebooks found under {source_dir}/.")

    for notebook in notebooks:
        relative_path = notebook.relative_to(source_dir)
        target_path = target_dir / relative_path.with_suffix(".html")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"Exporting {notebook} to {target_path}")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "marimo",
                "export",
                "html-wasm",
                str(notebook),
                "-o",
                str(target_path),
                "--mode",
                "run",
            ],
            check=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Export marimo notebooks to static HTML files."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path("wasm/marimo"),
        help="Directory containing marimo notebook .py files (default: wasm/marimo).",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=Path("docs"),
        help="Directory to write exported .html files (default: docs).",
    )
    args = parser.parse_args()

    export_notebooks(source_dir=args.source_dir, target_dir=args.target_dir)
