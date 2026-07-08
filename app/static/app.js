import { pct, renderBars, renderScatter } from "./charts.js";

const state = {
  matches: [],
  selectedMatchId: null,
  selectedParlayMatchIds: new Set(),
  strategy: "balanced",
  window: "next",
};

const nodes = {
  matchList: document.querySelector("#match-list"),
  feedStatus: document.querySelector("#feed-status"),
  refreshButton: document.querySelector("#refresh-button"),
  recommendationSummary: document.querySelector("#recommendation-summary"),
  winnerBars: document.querySelector("#winner-bars"),
  dataQuality: document.querySelector("#data-quality"),
  scoreBasis: document.querySelector("#score-basis"),
  decisionComparison: document.querySelector("#decision-comparison"),
  goalsBars: document.querySelector("#goals-bars"),
  overUnderBars: document.querySelector("#over-under-bars"),
  halfTimeBars: document.querySelector("#half-time-bars"),
  officialOddsDiagnostics: document.querySelector("#official-odds-diagnostics"),
  parlayScatter: document.querySelector("#parlay-scatter"),
  parlayResults: document.querySelector("#parlay-results"),
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value).replaceAll("`", "&#96;");
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function labelSelection(selection) {
  const labels = {
    home: "主胜",
    draw: "平局",
    away: "客胜",
  };
  if (labels[selection]) return labels[selection];
  if (selection.startsWith("over_")) return `大于 ${selection.replace("over_", "")} 球`;
  if (selection.startsWith("under_")) return `小于 ${selection.replace("under_", "")} 球`;
  if (selection === "5+") return "5球以上";
  return selection;
}

function labelRisk(risk) {
  const labels = {
    low: "风险较低",
    medium: "风险中等",
    high: "风险偏高",
  };
  return labels[risk] || risk;
}

function labelSource(source) {
  const labels = {
    sporttery: "体彩实时",
    sample: "示例数据",
    auto: "自动数据源",
    the_odds_api: "备用赔率",
  };
  return labels[source] || source;
}

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

function labelOfficialMarketStatus(status) {
  const labels = {
    available: "已抓到",
    missing: "缺失",
    suspended: "暂停",
    malformed: "异常",
  };
  return labels[status] || status;
}

function labelAdviceLevel(level) {
  const labels = {
    stable: "稳健参考",
    balanced: "均衡参考",
    small: "小额尝试",
    avoid: "放弃",
    missing: "信息不足",
  };
  return labels[level] || level;
}

function signedMoney(value) {
  const number = Number(value || 0);
  return `${number >= 0 ? "+" : "-"}${Math.abs(number).toFixed(1)}元`;
}

function formatKickoff(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function movementClass(movement) {
  if (movement === "up") return "odds-move-up";
  if (movement === "down") return "odds-move-down";
  return "odds-move-flat";
}

function movementMark(movement) {
  if (movement === "up") return "↑";
  if (movement === "down") return "↓";
  return "→";
}

function renderOddsMovement(match) {
  const winnerOdds = match.odds.filter((quote) => quote.market === "winner");
  if (!winnerOdds.length) {
    return '<div class="odds-strip muted">暂无胜平负赔率</div>';
  }
  return `
    <div class="odds-strip">
      ${winnerOdds
        .map(
          (quote) => `
            <span class="odds-chip ${movementClass(quote.movement)}">
              ${escapeHtml(labelSelection(quote.selection))} ${Number(quote.decimal_odds).toFixed(2)} ${escapeHtml(movementMark(quote.movement))}
            </span>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderFeedStatus(status) {
  const healthClass = status.healthy ? "healthy" : "unhealthy";
  const fallback = status.using_fallback ? " · 备用" : "";
  nodes.feedStatus.innerHTML = `
    <span class="feed-dot ${healthClass}"></span>
    <span>${escapeHtml(labelSource(status.source))}${fallback}</span>
    <span>${escapeHtml(status.message)}</span>
    ${status.last_success_at ? `<span>${escapeHtml(formatKickoff(status.last_success_at))}</span>` : ""}
  `;
}

function renderMatches() {
  if (!state.matches.length) {
    nodes.matchList.innerHTML = '<p class="empty-state">当前窗口没有未开赛比赛。</p>';
    return;
  }
  nodes.matchList.innerHTML = state.matches
    .map(
      (match) => `
        <div class="match-row ${match.match_id === state.selectedMatchId ? "active" : ""}">
          <button class="match-main" data-match-id="${escapeAttribute(match.match_id)}">
            <strong>${escapeHtml(match.home.name)} vs ${escapeHtml(match.away.name)}</strong>
            <div>${escapeHtml(match.competition)} · ${escapeHtml(formatKickoff(match.kickoff_utc))}</div>
            <span class="pill">数据质量 ${pct(match.context.data_quality)}</span>
            ${renderOddsMovement(match)}
          </button>
          <label class="parlay-toggle">
            <input type="checkbox" data-parlay-match-id="${escapeAttribute(match.match_id)}" ${state.selectedParlayMatchIds.has(match.match_id) ? "checked" : ""} />
            <span>加入串关</span>
          </label>
        </div>
      `,
    )
    .join("");
}

function renderRecommendation(analysis) {
  const pick = analysis.recommendations[0];
  if (!pick) {
    nodes.recommendationSummary.innerHTML = "<p>当前模型不建议强行选择。</p>";
    return;
  }
  const warnings = pick.warnings?.length
    ? `<div class="warning-list">${pick.warnings.map((warning) => `<div>${escapeHtml(warning)}</div>`).join("")}</div>`
    : "";
  const reasons = pick.reasons?.length
    ? `<div class="reason-list">${pick.reasons.slice(0, 3).map((reason) => `<div>${escapeHtml(reason)}</div>`).join("")}</div>`
    : "";
  nodes.recommendationSummary.innerHTML = `
    <div class="pick-summary">
      <div>
        <span class="subtle">首选倾向</span>
        <h2>${escapeHtml(labelSelection(pick.selection))}</h2>
      </div>
      <span class="value-pill">${escapeHtml(pick.value_label || "没有赔率，无法判断")}</span>
    </div>
    <div class="quick-stats">
      <div><span>模型认为</span><strong>${pct(pick.model_probability)}</strong></div>
      <div><span>当前赔率</span><strong>${pick.decimal_odds ? Number(pick.decimal_odds).toFixed(2) : "无"}</strong></div>
      <div><span>赔率是否划算</span><strong>${escapeHtml(pick.value_label || "无法判断")}</strong></div>
      <div><span>风险</span><strong>${escapeHtml(labelRisk(pick.risk))}</strong></div>
    </div>
    <p class="plain-summary">${escapeHtml(pick.plain_summary || "模型暂时没有足够信息给出详细解释。")}</p>
    ${reasons}
    ${warnings}
  `;
}

function renderAnalysis(analysis) {
  renderRecommendation(analysis);
  renderBars(
    nodes.winnerBars,
    analysis.winner_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })),
  );
  nodes.dataQuality.innerHTML = `
    <div class="pill">${pct(analysis.data_quality)}</div>
    <p>数据越高，模型越可信；低于60%需要人工复核。</p>
  `;
  nodes.scoreBasis.innerHTML = `
    <p>${escapeHtml(analysis.score_method_summary)}</p>
    <p>${escapeHtml(analysis.odds_basis_summary)}</p>
  `;
  renderDecisionComparison(analysis.decision_comparisons || []);
  renderBars(
    nodes.goalsBars,
    analysis.total_goal_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })),
    "var(--blue)",
  );
  renderBars(
    nodes.overUnderBars,
    analysis.over_under_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })),
    "var(--amber)",
  );
  renderBars(
    nodes.halfTimeBars,
    analysis.half_time_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })),
    "var(--blue)",
  );
}

function renderDecisionComparison(decisions) {
  if (!decisions.length) {
    nodes.decisionComparison.innerHTML = "<p>当前没有可对照的模型和赔率建议。</p>";
    return;
  }
  nodes.decisionComparison.innerHTML = `
    <div class="decision-list">
      ${decisions
        .map(
          (decision) => `
            <article class="decision-card ${escapeAttribute(decision.advice_level)}">
              <div class="decision-title">
                <strong>${escapeHtml(decision.market_label)}</strong>
                <span>${escapeHtml(decision.advice_label || labelAdviceLevel(decision.advice_level))}</span>
              </div>
              <div class="decision-columns">
                <div>
                  <span>模型推荐</span>
                  <strong>${escapeHtml(decision.model_selection_label || "暂无")}</strong>
                  <small>${decision.model_probability == null ? "缺少模型概率" : `模型概率 ${pct(decision.model_probability)}`}</small>
                </div>
                <div>
                  <span>赔率推荐</span>
                  <strong>${escapeHtml(decision.odds_selection_label || "暂无")}</strong>
                  <small>${
                    decision.odds_decimal == null
                      ? "缺少体彩官方赔率"
                      : `官方赔率 ${Number(decision.odds_decimal).toFixed(2)} · 赔率反推 ${pct(decision.odds_probability || 0)}`
                  }</small>
                </div>
                <div>
                  <span>综合建议</span>
                  <strong>${escapeHtml(decision.advice_label || labelAdviceLevel(decision.advice_level))}</strong>
                  <small>${escapeHtml(decision.summary || "")}</small>
                </div>
              </div>
              ${
                decision.reasons?.length
                  ? `<div class="reason-list">${decision.reasons.map((reason) => `<div>${escapeHtml(reason)}</div>`).join("")}</div>`
                  : ""
              }
              ${
                decision.warnings?.length
                  ? `<div class="warning-list">${decision.warnings.map((warning) => `<div>${escapeHtml(warning)}</div>`).join("")}</div>`
                  : ""
              }
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderParlayList(parlays, title, emptyText) {
  if (!parlays.length) {
    return `<section class="parlay-section"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(emptyText)}</p></section>`;
  }
  return `
    <section class="parlay-section">
      <h3>${escapeHtml(title)}</h3>
      ${parlays
        .map(
          (parlay) => `
            <article class="parlay-card">
              <div class="parlay-title">
                <h3>${parlay.leg_count}串1 · ${escapeHtml(parlay.strategy_label || "")}</h3>
                <span class="value-pill">${escapeHtml(parlay.value_label || "")}</span>
              </div>
              <div class="quick-stats parlay-stats">
                <div><span>预计命中</span><strong>${pct(parlay.combined_probability)}</strong></div>
                <div><span>总赔率</span><strong>${parlay.combined_odds.toFixed(2)}</strong></div>
                <div><span>2元一注中出返还</span><strong>${Number(parlay.payout_if_hit_2 || 0).toFixed(1)}元</strong></div>
                <div><span>2元一注理论盈亏</span><strong>${signedMoney(parlay.expected_profit_2)}</strong></div>
              </div>
              <p class="plain-summary">${escapeHtml(parlay.explanation)}</p>
              <div class="parlay-focus">
                <div><span>最稳一关</span><strong>${escapeHtml(parlay.strongest_leg || "暂无")}</strong></div>
                <div><span>拖后腿一关</span><strong>${escapeHtml(parlay.weakest_leg || "暂无")}</strong></div>
              </div>
              <div class="reason-list">${(parlay.reasons || []).map((reason) => `<div>${escapeHtml(reason)}</div>`).join("")}</div>
              ${
                parlay.warnings?.length
                  ? `<div class="warning-list">${parlay.warnings.map((warning) => `<div>${escapeHtml(warning)}</div>`).join("")}</div>`
                  : ""
              }
              <div class="leg-list">
                ${parlay.legs
                  .map(
                    (leg) => `
                      <div class="leg-row">
                        <strong>${escapeHtml(leg.label)}</strong>
                        <span>模型 ${pct(leg.probability)} · 赔率 ${leg.decimal_odds.toFixed(2)} · ${escapeHtml(leg.value_label || "")} · ${escapeHtml(labelRisk(leg.risk))}</span>
                      </div>
                    `,
                  )
                  .join("")}
              </div>
            </article>
          `,
        )
        .join("")}
    </section>
  `;
}

function renderParlays(payload) {
  const winnerParlays = Array.isArray(payload) ? payload : payload.winner_parlays || [];
  const scoreParlays = Array.isArray(payload) ? [] : payload.score_parlays || [];
  renderScatter(nodes.parlayScatter, winnerParlays.concat(scoreParlays));
  if (!Array.isArray(payload) && payload.selected_match_ids?.length < 2) {
    nodes.parlayResults.innerHTML = "<p>请先勾选至少两场比赛，再生成串关分析。</p>";
    return;
  }
  nodes.parlayResults.innerHTML = [
    renderParlayList(winnerParlays, "真实胜平负赔率", "所选比赛没有足够的胜平负赔率，暂时不能计算真实赔率串关。"),
    renderParlayList(scoreParlays, "比分串关", "所选比赛没有足够的比分模型结果。比分串关会使用模型理论赔率。"),
  ].join("");
}

function renderOfficialOddsDiagnostics(payload) {
  if (!nodes.officialOddsDiagnostics) return;
  if (!payload.matches?.length) {
    nodes.officialOddsDiagnostics.innerHTML = '<p class="empty-state">当前窗口没有官方赔率诊断数据。</p>';
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
                <span>${escapeHtml(match.competition)} · ${escapeHtml(formatKickoff(match.kickoff_utc))}</span>
              </summary>
              <div class="official-market-grid">
                ${(match.markets || [])
                  .map(
                    (market) => `
                      <div class="official-market-cell ${escapeAttribute(market.status)}">
                        <strong>${escapeHtml(labelOfficialMarket(market.market))}</strong>
                        <span>${escapeHtml(labelOfficialMarketStatus(market.status))}</span>
                        <small>${Number(market.odds_count || 0)} 项官方赔率</small>
                        ${
                          market.odds?.length
                            ? `<div class="official-odds-list">${market.odds
                                .slice(0, 12)
                                .map(
                                  (quote) =>
                                    `<span>${escapeHtml(quote.selection_label || quote.selection)} ${Number(quote.decimal_odds).toFixed(2)}</span>`,
                                )
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

async function loadAnalysis(matchId) {
  const analysis = await fetchJson(`/api/matches/${matchId}/analysis`);
  renderAnalysis(analysis);
}

async function loadParlays() {
  const selectedIds = [...state.selectedParlayMatchIds].filter((matchId) =>
    state.matches.some((match) => match.match_id === matchId),
  );
  if (selectedIds.length < 2) {
    nodes.parlayScatter.innerHTML = "";
    renderParlays({ selected_match_ids: selectedIds, winner_parlays: [], score_parlays: [] });
    return;
  }
  const params = new URLSearchParams({ strategy: state.strategy, window: state.window });
  selectedIds.forEach((matchId) => params.append("match_ids", matchId));
  const parlays = await fetchJson(`/api/selected-parlays?${params.toString()}`);
  renderParlays(parlays);
}

async function loadFeedStatus() {
  const status = await fetchJson("/api/feed/status");
  renderFeedStatus(status);
}

async function loadOfficialOddsDiagnostics() {
  if (!nodes.officialOddsDiagnostics) return;
  try {
    const payload = await fetchJson(`/api/official-odds/diagnostics?window=${state.window}`);
    renderOfficialOddsDiagnostics(payload);
  } catch (error) {
    nodes.officialOddsDiagnostics.innerHTML = `<p class="empty-state">官方赔率诊断加载失败：${escapeHtml(error.message)}</p>`;
  }
}

async function loadMatches() {
  state.matches = await fetchJson(`/api/matches?window=${state.window}`);
  const visibleIds = new Set(state.matches.map((match) => match.match_id));
  state.selectedParlayMatchIds = new Set([...state.selectedParlayMatchIds].filter((matchId) => visibleIds.has(matchId)));
  const selectedStillVisible = state.matches.some((match) => match.match_id === state.selectedMatchId);
  state.selectedMatchId = selectedStillVisible ? state.selectedMatchId : state.matches[0]?.match_id;
  renderMatches();
  if (state.selectedMatchId) {
    await loadAnalysis(state.selectedMatchId);
  } else {
    nodes.recommendationSummary.innerHTML = "<p>没有可分析的未开赛比赛。</p>";
  }
  await loadParlays();
}

async function refreshLiveData() {
  await loadFeedStatus();
  await loadMatches();
  await loadOfficialOddsDiagnostics();
}

nodes.matchList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-match-id]");
  if (!button) return;
  state.selectedMatchId = button.dataset.matchId;
  renderMatches();
  await loadAnalysis(state.selectedMatchId);
});

nodes.matchList.addEventListener("change", async (event) => {
  const checkbox = event.target.closest("[data-parlay-match-id]");
  if (!checkbox) return;
  if (checkbox.checked) {
    state.selectedParlayMatchIds.add(checkbox.dataset.parlayMatchId);
  } else {
    state.selectedParlayMatchIds.delete(checkbox.dataset.parlayMatchId);
  }
  renderMatches();
  await loadParlays();
});

document.querySelectorAll("[data-strategy]").forEach((button) => {
  button.addEventListener("click", async () => {
    document.querySelectorAll("[data-strategy]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.strategy = button.dataset.strategy;
    await loadParlays();
  });
});

document.querySelectorAll("[data-window]").forEach((button) => {
  button.addEventListener("click", async () => {
    document.querySelectorAll("[data-window]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    state.window = button.dataset.window;
    state.selectedMatchId = null;
    state.selectedParlayMatchIds.clear();
    await refreshLiveData();
  });
});

nodes.refreshButton.addEventListener("click", refreshLiveData);

setInterval(refreshLiveData, 30_000);

refreshLiveData().catch((error) => {
  document.body.insertAdjacentHTML("afterbegin", `<div class="panel">加载失败：${escapeHtml(error.message)}</div>`);
});
