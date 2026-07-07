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


def test_frontend_escapes_dynamic_html_and_attributes():
    app_js = (STATIC / "app.js").read_text()
    charts_js = (STATIC / "charts.js").read_text()

    assert "function escapeHtml" in app_js
    assert "function escapeAttribute" in app_js
    assert "function escapeHtml" in charts_js
    assert "function escapeAttribute" in charts_js
    assert 'data-match-id="${escapeAttribute(match.match_id)}"' in app_js
    assert "${escapeHtml(match.home.name)} vs ${escapeHtml(match.away.name)}" in app_js
    assert "${escapeHtml(parlay.explanation)}" in app_js
    assert "${escapeHtml(leg.label)}" in app_js
    assert "${escapeHtml(row.label)}" in charts_js
    assert "escapeAttribute(`${label} ${pct(item.probability)}`)" in charts_js


def test_heatmap_handles_zero_probability_and_mobile_overflow():
    charts_js = (STATIC / "charts.js").read_text()
    css = (STATIC / "styles.css").read_text()

    assert "maxProbability <= 0" in charts_js
    assert 'node.innerHTML = "<p>暂无有效比分分布。</p>";' in charts_js
    assert "NaN" not in charts_js
    assert "#score-heatmap" in css
    assert "overflow-x: auto" in css
