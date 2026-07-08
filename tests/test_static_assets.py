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
    assert "decision-comparison" in html
    assert "score-heatmap" not in html
    assert "parlay-results" in html
    assert "feed-status" in html
    assert "match-window" in html


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
    assert "${escapeHtml(match.competition)}" in app_js
    assert "${escapeHtml(status.message)}" in app_js
    assert "${escapeHtml(parlay.explanation)}" in app_js
    assert "${escapeHtml(leg.label)}" in app_js
    assert "${escapeHtml(row.label)}" in charts_js
    assert "escapeAttribute(`${label} ${pct(item.probability)}`)" in charts_js


def test_chart_helpers_handle_zero_probability():
    charts_js = (STATIC / "charts.js").read_text()

    assert "maxProbability <= 0" in charts_js
    assert 'node.innerHTML = "<p>暂无有效比分分布。</p>";' in charts_js
    assert "NaN" not in charts_js


def test_frontend_auto_refreshes_feed_and_displays_odds_movement():
    html = (STATIC / "index.html").read_text()
    app_js = (STATIC / "app.js").read_text()
    css = (STATIC / "styles.css").read_text()

    assert 'data-window="next"' in html
    assert 'data-window="tomorrow"' in html
    assert "setInterval(refreshLiveData, 30_000)" in app_js
    assert "function renderOddsMovement" in app_js
    assert "odds-move-up" in app_js
    assert "odds-move-down" in app_js
    assert ".odds-move-up" in css
    assert ".odds-move-down" in css


def test_frontend_uses_plain_chinese_analysis_copy():
    html = (STATIC / "index.html").read_text()
    app_js = (STATIC / "app.js").read_text()

    assert "一句话结论" in html
    assert "模型依据" in html
    assert "模型推荐" in app_js
    assert "赔率推荐" in app_js
    assert "综合建议" in app_js
    assert "赔率是否划算" in app_js
    assert "最稳一关" in app_js
    assert "2元一注理论盈亏" in app_js
    assert "期望值" not in app_js
    assert ">EV<" not in app_js


def test_frontend_contains_official_odds_diagnostics_view():
    html = (STATIC / "index.html").read_text()
    app_js = (STATIC / "app.js").read_text()
    css = (STATIC / "styles.css").read_text()

    assert "official-odds-diagnostics" in html
    assert "/api/official-odds/diagnostics" in app_js
    assert "官方赔率完整性" in html
    assert "胜平负" in app_js
    assert "让球胜平负" in app_js
    assert "比分" in app_js
    assert "总进球" in app_js
    assert "半全场" in app_js
    assert "official-market-table" in css


def test_frontend_supports_selected_match_score_parlays():
    app_js = (STATIC / "app.js").read_text()

    assert "加入串关" in app_js
    assert "/api/selected-parlays" in app_js
    assert "2元一注" in app_js
    assert "比分串关" in app_js
    assert "真实胜平负赔率" in app_js
    assert "模型理论赔率" in app_js
