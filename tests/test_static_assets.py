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


def test_frontend_does_not_use_visual_charts():
    app_js = (STATIC / "app.js").read_text()
    html = (STATIC / "index.html").read_text()

    assert "renderScatter" not in app_js
    assert "parlay-scatter" not in html
    assert "score-heatmap" not in html


def test_frontend_escapes_dynamic_html_and_attributes():
    app_js = (STATIC / "app.js").read_text()

    assert "function escapeHtml" in app_js
    assert "function escapeAttribute" in app_js
    assert 'data-match-id="${escapeAttribute(match.match_id)}"' in app_js
    assert "${escapeHtml(match.home.name)} vs ${escapeHtml(match.away.name)}" in app_js
    assert "${escapeHtml(match.competition)}" in app_js
    assert "${escapeHtml(status.message)}" in app_js
    assert "escapeHtml(parlayReason(parlay))" in app_js
    assert "escapeHtml(leg.label)" in app_js


def test_chart_file_is_only_a_compatibility_stub():
    charts_js = (STATIC / "charts.js").read_text()

    assert "export function pct" in charts_js
    assert "renderScatter" not in charts_js
    assert "renderHeatmap" not in charts_js
    assert "风险" not in charts_js
    assert "折算" not in charts_js


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

    assert "五种玩法建议" in html
    assert "推荐买法" in app_js
    assert "概率" in app_js
    assert "2元一注返还" in app_js
    assert "赔率缺失" in app_js
    assert "赔率是否划算" not in app_js
    assert "相对稳的一关" not in app_js
    assert "2元一注理论盈亏" not in app_js
    assert "期望值" not in app_js
    assert ">EV<" not in app_js
    assert "每100元" not in app_js
    assert "模型比赔率" not in app_js
    assert "赔率偏低" not in app_js
    assert "综合风险" not in app_js
    assert "最高返还" not in app_js


def test_frontend_renders_minimal_odds_advice_only():
    app_js = (STATIC / "app.js").read_text()
    html = (STATIC / "index.html").read_text()

    assert "页面版本" in html
    assert "推荐买法" in app_js
    assert "候选" in app_js
    assert "model_suggestions" in app_js
    assert "赔率数量" in app_js
    assert "2元一注返还" in app_js
    assert "score_candidates" not in app_js
    assert "球队资料模型" not in app_js
    assert "赔率模型看好" not in app_js


def test_frontend_rejects_technical_ev_copy_after_redesign():
    app_js = (STATIC / "app.js").read_text()

    forbidden = ["EV", "期望值", "每100元", "模型比赔率", "赔率偏低", "理论盈亏"]
    for word in forbidden:
        assert word not in app_js


def test_frontend_removes_official_odds_diagnostics_view():
    html = (STATIC / "index.html").read_text()
    app_js = (STATIC / "app.js").read_text()

    assert "official-odds-diagnostics" not in html
    assert "/api/official-odds/diagnostics" not in app_js
    assert "官方赔率完整性" not in html
    assert "推荐买法" in app_js


def test_frontend_supports_minimal_real_odds_parlays():
    app_js = (STATIC / "app.js").read_text()

    assert "加入串关" in app_js
    assert "/api/selected-parlays" in app_js
    assert "2元一注" in app_js
    assert "真实赔率串关" in app_js
    assert "总赔率 × 2元" in app_js
    assert "parlay.explanation" not in app_js
    assert "按表内总赔率乘以2元计算" in app_js
    assert "比分串关" not in app_js
    assert "模型理论赔率" not in app_js
    assert "probability_label" not in app_js
