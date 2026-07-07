from pathlib import Path


STATIC = Path("app/static")


def test_frontend_files_exist():
    assert (STATIC / "index.html").exists()
    assert (STATIC / "styles.css").exists()
    assert (STATIC / "app.js").exists()
    assert (STATIC / "charts.js").exists()


def test_index_contains_visual_regions():
    html = (STATIC / "index.html").read_text()

    assert "match-list" in html
    assert "score-heatmap" in html
    assert "parlay-results" in html


def test_chart_helpers_export_functions():
    js = (STATIC / "charts.js").read_text()

    assert "export function renderBars" in js
    assert "export function renderHeatmap" in js
    assert "export function renderScatter" in js
