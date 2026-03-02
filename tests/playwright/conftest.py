from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest


def _wait_for_server(url: str, retries: int = 30, sleep_seconds: float = 0.5) -> None:
    for _ in range(retries):
        try:
            with urlopen(url):
                return
        except URLError:
            time.sleep(sleep_seconds)
    raise RuntimeError(f"Timed out waiting for test server at {url}.")


@pytest.fixture(scope="session")
def server_bind() -> str:
    return os.environ.get("PUDL_TEST_SERVER_BIND", "localhost:8001")


@pytest.fixture(scope="session")
def server_base_url(server_bind: str) -> str:
    return f"http://{server_bind}"


@pytest.fixture(scope="session", autouse=True)
def marimo_test_server(server_bind: str, server_base_url: str) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    build_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "_build"))
    command = [
        sys.executable,
        "scripts/export_marimo_notebooks.py",
        "--serve",
        server_bind,
        "--target-directory",
        build_dir,
    ]
    process = subprocess.Popen(command, cwd=repo_root)
    try:
        _wait_for_server(f"{server_base_url}/plant-explorer.html")
        yield
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
