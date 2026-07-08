# Official Sporttery Odds Data Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Verify and expose official China Sports Lottery odds for 胜平负、让球胜平负、比分、总进球数、半全场 before recommendation and UI redesign work.

**Architecture:** Keep the current FastAPI provider architecture. Extend the domain model with official market diagnostics, extend the Sporttery parser to normalize all five official pool codes, add a diagnostic service/API, and add a small frontend diagnostics view without changing the main recommendation model.

**Tech Stack:** Python 3, FastAPI, Pydantic, urllib JSON fetching, vanilla JavaScript/CSS, pytest with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

---

## File Structure

- Modify `app/domain.py`: add official market literals and diagnostic Pydantic models while keeping existing `OddsQuote` fields backward compatible.
- Modify `app/data/providers.py`: change the default Sporttery endpoint to request `had,hhad,crs,ttg,hafu`; add parsing helpers for all five official markets; expose a provider diagnostics method for Sporttery.
- Modify `app/services.py`: add an official odds diagnostics builder that can work with a provider exposing diagnostics.
- Modify `app/routes.py`: add `GET /api/official-odds/diagnostics`.
- Modify `app/static/index.html`: add a compact official odds diagnostics section.
- Modify `app/static/app.js`: fetch and render official odds diagnostics; keep existing analysis and selected parlay behavior intact.
- Modify `app/static/styles.css`: add diagnostics table and expandable market styles.
- Modify `tests/test_live_provider.py`: add all-five-market fixture parsing and diagnostics behavior tests.
- Modify `tests/test_api.py`: add endpoint shape test.
- Modify `tests/test_static_assets.py`: add static asset tests for diagnostics UI and escaping.
- Modify `README.md`: document local official odds diagnostics and official-only limitation.

## Task 1: Domain Models For Official Odds Diagnostics

**Files:**
- Modify: `app/domain.py`
- Test: `tests/test_domain.py`

- [ ] **Step 1: Write failing domain tests**

Add these tests to `tests/test_domain.py`:

```python
def test_official_market_diagnostic_accepts_available_market_with_quotes():
    diagnostic = OfficialMarketDiagnostic(
        market="score",
        label="比分",
        status="available",
        odds_count=2,
        odds=[
            OddsQuote(
                market="score",
                selection="2-1",
                selection_label="2-1",
                decimal_odds=9.0,
                source="sporttery",
                raw_selection="0102",
            )
        ],
        warnings=[],
    )

    assert diagnostic.market == "score"
    assert diagnostic.status == "available"
    assert diagnostic.odds[0].selection_label == "2-1"
    assert diagnostic.odds[0].raw_selection == "0102"


def test_official_odds_match_diagnostic_lists_missing_markets():
    diagnostic = OfficialOddsMatchDiagnostic(
        match_id="sporttery-2040427",
        home_name="阿根廷",
        away_name="埃及",
        kickoff_utc="2026-07-07T16:00:00Z",
        competition="世界杯",
        markets=[
            OfficialMarketDiagnostic(market="winner", label="胜平负", status="available", odds_count=3),
            OfficialMarketDiagnostic(market="score", label="比分", status="missing", odds_count=0),
        ],
    )

    assert diagnostic.missing_markets == ["score"]
```

- [ ] **Step 2: Run domain tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_domain.py::test_official_market_diagnostic_accepts_available_market_with_quotes tests/test_domain.py::test_official_odds_match_diagnostic_lists_missing_markets
```

Expected: both tests fail with `NameError` because `OfficialMarketDiagnostic` and `OfficialOddsMatchDiagnostic` do not exist.

- [ ] **Step 3: Implement domain models**

In `app/domain.py`, update and add:

```python
MarketName = Literal[
    "winner",
    "handicap_winner",
    "score",
    "total_goals",
    "half_full",
    "over_under",
    "half_time",
]
OfficialMarketStatus = Literal["available", "missing", "suspended", "malformed"]
```

Extend `OddsQuote`:

```python
class OddsQuote(BaseModel):
    market: MarketName
    selection: str
    decimal_odds: float = Field(gt=1)
    source: str | None = None
    updated_at: str | None = None
    previous_decimal_odds: float | None = Field(default=None, gt=1)
    movement: OddsMovement | None = None
    selection_label: str | None = None
    raw_selection: str | None = None
```

Add models below `SourceStatus`:

```python
class OfficialMarketDiagnostic(BaseModel):
    market: MarketName
    label: str
    status: OfficialMarketStatus
    odds_count: int = Field(ge=0)
    odds: list[OddsQuote] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class OfficialOddsMatchDiagnostic(BaseModel):
    match_id: str
    home_name: str
    away_name: str
    kickoff_utc: str
    competition: str
    markets: list[OfficialMarketDiagnostic]

    @property
    def missing_markets(self) -> list[str]:
        return [market.market for market in self.markets if market.status != "available"]


class OfficialOddsDiagnostics(BaseModel):
    status: SourceStatus
    match_count: int = Field(ge=0)
    matches: list[OfficialOddsMatchDiagnostic]
```

- [ ] **Step 4: Run domain tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_domain.py::test_official_market_diagnostic_accepts_available_market_with_quotes tests/test_domain.py::test_official_odds_match_diagnostic_lists_missing_markets
```

Expected: both tests pass.

- [ ] **Step 5: Commit task**

```bash
git add app/domain.py tests/test_domain.py
git commit -m "feat: add official odds diagnostic models"
```

## Task 2: Parse All Five Official Sporttery Markets

**Files:**
- Modify: `app/data/providers.py`
- Test: `tests/test_live_provider.py`

- [ ] **Step 1: Write failing parser tests**

Add a new fixture helper to `tests/test_live_provider.py`:

```python
def sporttery_all_markets_payload() -> dict:
    payload = sporttery_payload()
    match = payload["value"]["matchInfoList"][0]["subMatchList"][0]
    match["crs"] = {
        "s0100": "5.50",
        "s0201": "9.00",
        "s0000": "7.00",
        "updateDate": "2026-07-07",
        "updateTime": "20:07:51",
    }
    match["ttg"] = {
        "s0": "12.00",
        "s1": "5.50",
        "s2": "3.60",
        "s3": "3.80",
        "s4": "5.20",
        "s5": "8.00",
        "s6": "16.00",
        "s7": "25.00",
        "updateDate": "2026-07-07",
        "updateTime": "20:07:51",
    }
    match["hafu"] = {
        "hh": "2.20",
        "hd": "13.00",
        "ha": "35.00",
        "dh": "4.60",
        "dd": "6.00",
        "da": "18.00",
        "ah": "22.00",
        "ad": "13.00",
        "aa": "15.00",
        "updateDate": "2026-07-07",
        "updateTime": "20:07:51",
    }
    return payload
```

Add tests:

```python
def test_parse_sporttery_payload_builds_all_official_market_odds():
    matches = parse_sporttery_payload(sporttery_all_markets_payload())
    match = next(match for match in matches if match.match_id == "sporttery-2040427")

    markets = {quote.market for quote in match.odds}
    assert {"winner", "handicap_winner", "score", "total_goals", "half_full"}.issubset(markets)

    handicap = next(quote for quote in match.odds if quote.market == "handicap_winner" and quote.selection == "home")
    assert handicap.selection_label == "让球主胜"
    assert handicap.decimal_odds == 1.74

    score = next(quote for quote in match.odds if quote.market == "score" and quote.selection == "2-1")
    assert score.selection_label == "2-1"
    assert score.decimal_odds == 9.00
    assert score.raw_selection == "s0201"

    total = next(quote for quote in match.odds if quote.market == "total_goals" and quote.selection == "3")
    assert total.selection_label == "3球"
    assert total.decimal_odds == 3.80

    half_full = next(quote for quote in match.odds if quote.market == "half_full" and quote.selection == "home_home")
    assert half_full.selection_label == "胜胜"
    assert half_full.decimal_odds == 2.20


def test_sporttery_endpoint_requests_all_official_pool_codes():
    assert "poolCode=had,hhad,crs,ttg,hafu" in SPORTTERY_ENDPOINT
```

- [ ] **Step 2: Run parser tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_live_provider.py::test_parse_sporttery_payload_builds_all_official_market_odds tests/test_live_provider.py::test_sporttery_endpoint_requests_all_official_pool_codes
```

Expected: first test fails because only `winner` odds are parsed; second fails because endpoint only requests `had,hhad`.

- [ ] **Step 3: Implement official market parsing**

In `app/data/providers.py`, change endpoint:

```python
SPORTTERY_ENDPOINT = (
    "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"
    "?channel=c&poolCode=had,hhad,crs,ttg,hafu"
)
SPORTTERY_REFERER = "https://m.sporttery.cn/mjc/jsq/zqspf/"
```

Add label maps near `build_winner_odds`:

```python
HANDICAP_LABELS = {"home": "让球主胜", "draw": "让球平", "away": "让球客胜"}
HALF_FULL_SELECTIONS = {
    "hh": ("home_home", "胜胜"),
    "hd": ("home_draw", "胜平"),
    "ha": ("home_away", "胜负"),
    "dh": ("draw_home", "平胜"),
    "dd": ("draw_draw", "平平"),
    "da": ("draw_away", "平负"),
    "ah": ("away_home", "负胜"),
    "ad": ("away_draw", "负平"),
    "aa": ("away_away", "负负"),
}
```

Add helper:

```python
def build_market_quote(
    match_id: str,
    market: str,
    selection: str,
    label: str,
    raw_selection: str,
    decimal_odds: float,
    updated_at: str | None,
    previous_odds: dict[tuple[str, str, str], float],
    movement_flag: Any = None,
) -> OddsQuote:
    previous = previous_odds.get((match_id, market, selection))
    fallback_movement = movement_from_flag(movement_flag)
    return OddsQuote(
        market=market,
        selection=selection,
        selection_label=label,
        raw_selection=raw_selection,
        decimal_odds=decimal_odds,
        source="sporttery",
        updated_at=updated_at,
        previous_decimal_odds=previous,
        movement=movement_from_previous(decimal_odds, previous, fallback_movement),
    )
```

Add parsers:

```python
def build_handicap_winner_odds(match_id: str, hhad: dict[str, Any], previous_odds: dict[tuple[str, str, str], float]) -> list[OddsQuote]:
    mapping = {"home": ("h", "hf"), "draw": ("d", "df"), "away": ("a", "af")}
    updated = odds_updated_at(hhad)
    quotes = []
    for selection, (value_key, flag_key) in mapping.items():
        decimal_odds = parse_decimal(hhad.get(value_key))
        if decimal_odds is None:
            continue
        quotes.append(build_market_quote(match_id, "handicap_winner", selection, HANDICAP_LABELS[selection], value_key, decimal_odds, updated, previous_odds, hhad.get(flag_key)))
    return quotes


def score_selection_from_key(raw_key: str) -> tuple[str, str] | None:
    digits = raw_key.removeprefix("s")
    if len(digits) != 4 or not digits.isdigit():
        return None
    home_goals = int(digits[:2])
    away_goals = int(digits[2:])
    label = f"{home_goals}-{away_goals}"
    return label, label


def build_score_odds(match_id: str, crs: dict[str, Any], previous_odds: dict[tuple[str, str, str], float]) -> list[OddsQuote]:
    updated = odds_updated_at(crs)
    quotes = []
    for raw_key, raw_value in crs.items():
        parsed = score_selection_from_key(str(raw_key))
        decimal_odds = parse_decimal(raw_value)
        if parsed is None or decimal_odds is None:
            continue
        selection, label = parsed
        quotes.append(build_market_quote(match_id, "score", selection, label, str(raw_key), decimal_odds, updated, previous_odds, crs.get(f"{raw_key}f")))
    return quotes


def build_total_goals_odds(match_id: str, ttg: dict[str, Any], previous_odds: dict[tuple[str, str, str], float]) -> list[OddsQuote]:
    updated = odds_updated_at(ttg)
    quotes = []
    for total in range(8):
        raw_key = f"s{total}"
        decimal_odds = parse_decimal(ttg.get(raw_key))
        if decimal_odds is None:
            continue
        selection = str(total)
        label = f"{total}球" if total < 7 else "7+球"
        quotes.append(build_market_quote(match_id, "total_goals", selection, label, raw_key, decimal_odds, updated, previous_odds, ttg.get(f"{raw_key}f")))
    return quotes


def build_half_full_odds(match_id: str, hafu: dict[str, Any], previous_odds: dict[tuple[str, str, str], float]) -> list[OddsQuote]:
    updated = odds_updated_at(hafu)
    quotes = []
    for raw_key, (selection, label) in HALF_FULL_SELECTIONS.items():
        decimal_odds = parse_decimal(hafu.get(raw_key))
        if decimal_odds is None:
            continue
        quotes.append(build_market_quote(match_id, "half_full", selection, label, raw_key, decimal_odds, updated, previous_odds, hafu.get(f"{raw_key}f")))
    return quotes
```

Update `parse_sporttery_payload` odds building:

```python
odds = []
odds.extend(build_winner_odds(match_id, had, previous))
odds.extend(build_handicap_winner_odds(match_id, hhad, previous))
odds.extend(build_score_odds(match_id, item.get("crs") or {}, previous))
odds.extend(build_total_goals_odds(match_id, item.get("ttg") or {}, previous))
odds.extend(build_half_full_odds(match_id, item.get("hafu") or {}, previous))
```

- [ ] **Step 4: Run parser tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_live_provider.py::test_parse_sporttery_payload_builds_all_official_market_odds tests/test_live_provider.py::test_sporttery_endpoint_requests_all_official_pool_codes
```

Expected: both tests pass.

- [ ] **Step 5: Run live provider regression tests**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_live_provider.py
```

Expected: all tests in `tests/test_live_provider.py` pass.

- [ ] **Step 6: Commit task**

```bash
git add app/data/providers.py tests/test_live_provider.py
git commit -m "feat: parse official sporttery markets"
```

## Task 3: Official Odds Diagnostics Service And API

**Files:**
- Modify: `app/data/providers.py`
- Modify: `app/services.py`
- Modify: `app/routes.py`
- Test: `tests/test_api.py`
- Test: `tests/test_live_provider.py`

- [ ] **Step 1: Write failing provider diagnostic test**

Add to `tests/test_live_provider.py`:

```python
def test_sporttery_provider_diagnostics_reports_market_coverage():
    provider = SportteryDataProvider(fetch_json=sporttery_all_markets_payload, refresh_seconds=1)

    diagnostics = provider.official_odds_diagnostics(window="7d")
    match = next(item for item in diagnostics.matches if item.match_id == "sporttery-2040427")
    markets = {market.market: market for market in match.markets}

    assert diagnostics.match_count >= 1
    assert markets["winner"].status == "available"
    assert markets["handicap_winner"].status == "available"
    assert markets["score"].status == "available"
    assert markets["total_goals"].status == "available"
    assert markets["half_full"].status == "available"
    assert markets["score"].odds_count >= 3
```

- [ ] **Step 2: Write failing API diagnostic test**

Add to `tests/test_api.py`:

```python
def test_official_odds_diagnostics_endpoint_returns_market_coverage():
    payload = get_json("/api/official-odds/diagnostics?window=7d")

    assert payload["status"]["source"]
    assert payload["match_count"] >= 1
    match = payload["matches"][0]
    assert "match_id" in match
    assert "markets" in match
    market_names = {market["market"] for market in match["markets"]}
    assert {"winner", "handicap_winner", "score", "total_goals", "half_full"}.issubset(market_names)
```

- [ ] **Step 3: Run diagnostics tests and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_live_provider.py::test_sporttery_provider_diagnostics_reports_market_coverage tests/test_api.py::test_official_odds_diagnostics_endpoint_returns_market_coverage
```

Expected: first test fails because `official_odds_diagnostics` does not exist; second fails because endpoint does not exist.

- [ ] **Step 4: Implement diagnostic helpers in provider**

In `app/data/providers.py`, import diagnostic models:

```python
from app.domain import OfficialMarketDiagnostic, OfficialOddsDiagnostics, OfficialOddsMatchDiagnostic
```

Add constants:

```python
OFFICIAL_MARKETS = [
    ("winner", "胜平负"),
    ("handicap_winner", "让球胜平负"),
    ("score", "比分"),
    ("total_goals", "总进球"),
    ("half_full", "半全场"),
]
```

Add helper:

```python
def build_match_official_diagnostic(match: MatchInput) -> OfficialOddsMatchDiagnostic:
    markets = []
    for market_name, label in OFFICIAL_MARKETS:
        odds = [quote for quote in match.odds if quote.market == market_name]
        status = "available" if odds else "missing"
        warnings = [] if odds else [f"官方{label}赔率缺失"]
        markets.append(
            OfficialMarketDiagnostic(
                market=market_name,
                label=label,
                status=status,
                odds_count=len(odds),
                odds=odds,
                warnings=warnings,
            )
        )
    return OfficialOddsMatchDiagnostic(
        match_id=match.match_id,
        home_name=match.home.name,
        away_name=match.away.name,
        kickoff_utc=match.kickoff_utc,
        competition=match.competition,
        markets=markets,
    )
```

Add method to `SportteryDataProvider`:

```python
def official_odds_diagnostics(self, window: MatchWindow = "next") -> OfficialOddsDiagnostics:
    matches = self.list_matches(window=window)
    diagnostics = [build_match_official_diagnostic(match) for match in matches]
    return OfficialOddsDiagnostics(status=self.status(), match_count=len(diagnostics), matches=diagnostics)
```

- [ ] **Step 5: Implement service and route**

In `app/services.py`, add:

```python
from app.domain import OfficialOddsDiagnostics, SourceStatus
from app.data.providers import build_match_official_diagnostic


def build_official_odds_diagnostics(provider, window: str = "next") -> OfficialOddsDiagnostics:
    if hasattr(provider, "official_odds_diagnostics"):
        return provider.official_odds_diagnostics(window=window)
    matches = provider.list_matches(window=window)
    diagnostics = [build_match_official_diagnostic(match) for match in matches]
    return OfficialOddsDiagnostics(status=provider.status(), match_count=len(diagnostics), matches=diagnostics)
```

In `app/routes.py`, import and add route:

```python
from app.services import build_official_odds_diagnostics


@router.get("/api/official-odds/diagnostics")
async def official_odds_diagnostics(window: str = Query(default="next"), provider: MatchProvider = Depends(get_provider)):
    return build_official_odds_diagnostics(provider, window=window)
```

- [ ] **Step 6: Run diagnostics tests and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_live_provider.py::test_sporttery_provider_diagnostics_reports_market_coverage tests/test_api.py::test_official_odds_diagnostics_endpoint_returns_market_coverage
```

Expected: both tests pass.

- [ ] **Step 7: Commit task**

```bash
git add app/data/providers.py app/services.py app/routes.py tests/test_live_provider.py tests/test_api.py
git commit -m "feat: add official odds diagnostics api"
```

## Task 4: Diagnostic UI

**Files:**
- Modify: `app/static/index.html`
- Modify: `app/static/app.js`
- Modify: `app/static/styles.css`
- Test: `tests/test_static_assets.py`

- [ ] **Step 1: Write failing static asset test**

Add to `tests/test_static_assets.py`:

```python
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
```

- [ ] **Step 2: Run static test and verify failure**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_static_assets.py::test_frontend_contains_official_odds_diagnostics_view
```

Expected: fails because diagnostic UI does not exist.

- [ ] **Step 3: Add HTML container**

In `app/static/index.html`, add this section above the current parlay section:

```html
<section class="panel">
  <div class="parlay-header">
    <div>
      <div class="panel-title">官方赔率完整性</div>
      <p>只检查中国体育彩票官方五类玩法是否抓到，不使用第三方赔率。</p>
    </div>
  </div>
  <div id="official-odds-diagnostics"></div>
</section>
```

- [ ] **Step 4: Add JS rendering**

In `app/static/app.js`, add node:

```javascript
officialOddsDiagnostics: document.querySelector("#official-odds-diagnostics"),
```

Add market label helper:

```javascript
function labelOfficialMarket(market) {
  const labels = {
    winner: "胜平负",
    handicap_winner: "让球胜平负",
    score: "比分",
    total_goals: "总进球",
    half_full: "半全场",
  };
  return labels[market] || market;
}
```

Add renderer:

```javascript
function renderOfficialOddsDiagnostics(payload) {
  if (!payload.matches?.length) {
    nodes.officialOddsDiagnostics.innerHTML = "<p>当前窗口没有官方赔率诊断数据。</p>";
    return;
  }
  nodes.officialOddsDiagnostics.innerHTML = `
    <div class="official-market-table">
      ${payload.matches
        .map(
          (match) => `
            <details>
              <summary>
                <strong>${escapeHtml(match.home_name)} vs ${escapeHtml(match.away_name)}</strong>
                <span>${escapeHtml(match.competition)}</span>
              </summary>
              <div class="official-market-grid">
                ${match.markets
                  .map(
                    (market) => `
                      <div class="official-market-cell ${market.status}">
                        <strong>${escapeHtml(labelOfficialMarket(market.market))}</strong>
                        <span>${escapeHtml(market.status === "available" ? "已抓到" : market.status === "missing" ? "缺失" : market.status)}</span>
                        <small>${market.odds_count} 项赔率</small>
                        ${
                          market.odds?.length
                            ? `<div class="official-odds-list">${market.odds
                                .slice(0, 12)
                                .map((quote) => `<span>${escapeHtml(quote.selection_label || quote.selection)} ${Number(quote.decimal_odds).toFixed(2)}</span>`)
                                .join("")}</div>`
                            : `<em>${escapeHtml((market.warnings || []).join("；") || "暂无官方赔率")}</em>`
                        }
                      </div>
                    `,
                  )
                  .join("")}
              </div>
            </details>
          `,
        )
        .join("")}
    </div>
  `;
}
```

Add loader:

```javascript
async function loadOfficialOddsDiagnostics() {
  const payload = await fetchJson(`/api/official-odds/diagnostics?window=${state.window}`);
  renderOfficialOddsDiagnostics(payload);
}
```

Update `refreshLiveData`:

```javascript
async function refreshLiveData() {
  await loadFeedStatus();
  await loadMatches();
  await loadOfficialOddsDiagnostics();
}
```

- [ ] **Step 5: Add CSS**

In `app/static/styles.css`, add:

```css
.official-market-table {
  display: grid;
  gap: 10px;
}

.official-market-table details {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #ffffff;
}

.official-market-table summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  cursor: pointer;
}

.official-market-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 8px;
  padding: 0 12px 12px;
}

.official-market-cell {
  min-width: 0;
  padding: 9px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fbfcfc;
}

.official-market-cell.available {
  border-color: rgba(34, 122, 92, 0.35);
}

.official-market-cell.missing,
.official-market-cell.malformed {
  border-color: rgba(181, 68, 68, 0.28);
  background: #fff7f7;
}

.official-market-cell span,
.official-market-cell small,
.official-market-cell em {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
  font-style: normal;
}

.official-odds-list {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-top: 8px;
}

.official-odds-list span {
  padding: 3px 6px;
  border-radius: 999px;
  background: #edf3f1;
  color: var(--green);
  font-weight: 700;
}

@media (max-width: 980px) {
  .official-market-grid {
    grid-template-columns: 1fr;
  }
}
```

- [ ] **Step 6: Run static test and verify pass**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q tests/test_static_assets.py::test_frontend_contains_official_odds_diagnostics_view
```

Expected: test passes.

- [ ] **Step 7: Commit task**

```bash
git add app/static/index.html app/static/app.js app/static/styles.css tests/test_static_assets.py
git commit -m "feat: show official odds diagnostics"
```

## Task 5: Final Verification And Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document official-only diagnostics**

Add to `README.md` under Data Sources:

```markdown
## Official Odds Diagnostics

For local-first validation, open the app and check **官方赔率完整性**. The diagnostic view requests China Sports Lottery official odds for:

- 胜平负
- 让球胜平负
- 比分
- 总进球
- 半全场

The diagnostic view does not use third-party odds and does not treat model-theoretical odds as real odds. If an official market is missing, it is shown as missing and must not be used for recommendation or parlay calculations.

API:

```text
GET /api/official-odds/diagnostics?window=next
```
```

- [ ] **Step 2: Run full test suite**

Run:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q
```

Expected: all tests pass with zero failures.

- [ ] **Step 3: Optional local diagnostics smoke check**

Run local sample mode:

```bash
FOOTBALL_DATA_PROVIDER=sample python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8012
```

In a separate shell, request:

```bash
curl -s http://127.0.0.1:8012/api/official-odds/diagnostics?window=7d
```

Expected: JSON response includes `match_count`, `matches`, and five market diagnostics per match. If the shell environment cannot connect to the local server because of sandbox isolation, document that the ASGI API tests are the verification source and stop the uvicorn process with `Ctrl+C`.

- [ ] **Step 4: Commit documentation**

```bash
git add README.md
git commit -m "docs: document official odds diagnostics"
```

- [ ] **Step 5: Push branch**

```bash
git status --short
git log --oneline -5
git push origin HEAD:main
```

Expected: working tree clean, latest commits include all five task commits, and GitHub `main` receives the new commits.

## Self-Review Checklist

- Spec coverage: all five markets, official-only source, diagnostic API, diagnostic UI, missing-market handling, no third-party substitution, no model-theoretical odds are covered by tasks.
- No placeholders: every task includes concrete files, tests, commands, and implementation snippets.
- Type consistency: `handicap_winner`, `score`, `total_goals`, and `half_full` are used consistently across domain, parser, diagnostics, API, and UI.
- Scope control: recommendation redesign, model calibration, parlay workstation, and backtesting are intentionally deferred until the official odds data layer is verified.
