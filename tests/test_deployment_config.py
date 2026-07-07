from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_render_blueprint_deploys_fastapi_with_live_sporttery_source():
    render_yaml = (ROOT / "render.yaml").read_text()

    assert "type: web" in render_yaml
    assert "runtime: python" in render_yaml
    assert "plan: free" in render_yaml
    assert "plan: starter" not in render_yaml
    assert "pip install -r requirements.txt" in render_yaml
    assert "uvicorn app.main:app --host 0.0.0.0 --port $PORT" in render_yaml
    assert "healthCheckPath: /api/health" in render_yaml
    assert "FOOTBALL_DATA_PROVIDER" in render_yaml
    assert "value: sporttery" in render_yaml
    assert "SPORTTERY_REFRESH_SECONDS" in render_yaml
    assert "value: \"30\"" in render_yaml


def test_render_blueprint_does_not_require_access_password():
    render_yaml = (ROOT / "render.yaml").read_text().lower()

    assert "password" not in render_yaml
    assert "basic_auth" not in render_yaml
    assert "auth" not in render_yaml
