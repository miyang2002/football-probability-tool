from pathlib import Path

from tools.local_launcher import build_server_command, build_server_env, venv_python_path


ROOT = Path(__file__).resolve().parents[1]


def test_launcher_defaults_to_sporttery_live_source():
    env = build_server_env({})

    assert env["FOOTBALL_DATA_PROVIDER"] == "sporttery"
    assert env["SPORTTERY_REFRESH_SECONDS"] == "30"


def test_launcher_respects_existing_data_source_overrides():
    env = build_server_env({"FOOTBALL_DATA_PROVIDER": "sample", "SPORTTERY_REFRESH_SECONDS": "10"})

    assert env["FOOTBALL_DATA_PROVIDER"] == "sample"
    assert env["SPORTTERY_REFRESH_SECONDS"] == "10"


def test_launcher_builds_uvicorn_command_on_localhost():
    command = build_server_command(Path("/repo/.venv/bin/python"), port=8123)

    assert command == [
        "/repo/.venv/bin/python",
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8123",
    ]


def test_launcher_uses_platform_venv_python_path():
    posix_path = venv_python_path(Path("/repo"), platform_name="posix")
    windows_path = venv_python_path(Path("C:/repo"), platform_name="nt")

    assert posix_path.as_posix().endswith(".venv/bin/python")
    assert windows_path.as_posix().endswith(".venv/Scripts/python.exe")


def test_start_scripts_delegate_to_local_launcher():
    shell_script = (ROOT / "start_local.sh").read_text()
    command_script = (ROOT / "start_local.command").read_text()
    batch_script = (ROOT / "start_local.bat").read_text()

    assert "tools/local_launcher.py" in shell_script
    assert "tools/local_launcher.py" in command_script
    assert "tools\\local_launcher.py" in batch_script
