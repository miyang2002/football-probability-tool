from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import venv
import webbrowser
from pathlib import Path
from typing import Mapping


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def venv_python_path(root: Path, platform_name: str | None = None) -> Path:
    platform = platform_name or os.name
    if platform == "nt":
        return root / ".venv" / "Scripts" / "python.exe"
    return root / ".venv" / "bin" / "python"


def build_server_env(base_env: Mapping[str, str]) -> dict[str, str]:
    env = dict(base_env)
    env.setdefault("FOOTBALL_DATA_PROVIDER", "sporttery")
    env.setdefault("SPORTTERY_REFRESH_SECONDS", "30")
    return env


def build_server_command(python_path: Path, port: int) -> list[str]:
    return [
        str(python_path),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        DEFAULT_HOST,
        "--port",
        str(port),
    ]


def find_free_port(start_port: int = DEFAULT_PORT, attempts: int = 30) -> int:
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((DEFAULT_HOST, port)) != 0:
                return port
    raise RuntimeError(f"No free localhost port found from {start_port} to {start_port + attempts - 1}")


def wait_for_health(url: str, timeout_seconds: float = 30.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except (OSError, urllib.error.URLError):
            time.sleep(0.4)
    return False


def ensure_virtualenv(root: Path) -> Path:
    python_path = venv_python_path(root)
    if not python_path.exists():
        print("Creating local Python environment...")
        venv.EnvBuilder(with_pip=True).create(root / ".venv")
    return python_path


def install_requirements(root: Path, python_path: Path) -> None:
    requirements = root / "requirements.txt"
    print("Installing or updating dependencies...")
    subprocess.check_call([str(python_path), "-m", "pip", "install", "-r", str(requirements)], cwd=root)


def launch() -> int:
    root = repo_root()
    python_path = ensure_virtualenv(root)
    install_requirements(root, python_path)

    port = int(os.getenv("FOOTBALL_TOOL_PORT", str(find_free_port())))
    url = f"http://{DEFAULT_HOST}:{port}"
    env = build_server_env(os.environ)
    command = build_server_command(python_path, port)

    print(f"Starting Football Probability Tool at {url}")
    print(f"Data provider: {env['FOOTBALL_DATA_PROVIDER']}")
    process = subprocess.Popen(command, cwd=root, env=env)

    try:
        if wait_for_health(f"{url}/api/health"):
            webbrowser.open(url)
            print("Browser opened. Press Ctrl+C here to stop the local server.")
        else:
            print(f"Server did not become ready in time. Try opening {url} manually.")
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping local server...")
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
    return process.returncode or 0


if __name__ == "__main__":
    raise SystemExit(launch())
