#!/usr/bin/env python3
"""Export all marimo notebooks in a directory to WebAssembly."""

import argparse
import http.server
import subprocess
import sys
from pathlib import Path


def parse_bind(value: str) -> tuple[str, int]:
    """Parse a HOST:PORT binding string."""
    host, port_text = value.split(":")
    port = int(port_text)
    if not host:
        host = "localhost"
    return host, port


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
                "-f",
            ],
            check=True,
        )


def serve_directory(target_dir: Path, bind: str, port: int) -> None:
    """Serve the target directory over HTTP until interrupted."""

    def handler(request, client_address, server):
        return http.server.SimpleHTTPRequestHandler(
            request,
            client_address,
            server,
            directory=target_dir,
        )

    with http.server.ThreadingHTTPServer((bind, port), handler) as server:
        print(f"Serving {target_dir.resolve()} at http://{bind}:{port}")
        print("Press Ctrl+C to stop.")
        server.serve_forever()


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
        "--target-directory",
        type=Path,
        default=Path("docs"),
        help="Directory to write exported .html files (default: docs).",
    )
    parser.add_argument(
        "--serve",
        nargs="?",
        const="localhost:8000",
        type=parse_bind,
        metavar="HOST:PORT",
        help=(
            "Serve the exported HTML directory at HOST:PORT. "
            "If HOST:PORT is omitted, defaults to localhost:8000. "
            "If --serve is not provided, don't serve the directory at all."
        ),
    )

    args = parser.parse_args()

    export_notebooks(source_dir=args.source_dir, target_dir=args.target_dir)

    if args.serve is not None:
        bind, port = args.serve
        serve_directory(
            target_dir=args.target_dir,
            bind=bind,
            port=port,
        )
