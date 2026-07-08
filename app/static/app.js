import { pct, renderScatter } from "./charts.js";

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
  decisionComparison: document.querySelector("#decision-comparison"),
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
    stable: "建议",
    balanced: "谨慎",
    small: "小额参考",
    avoid: "放弃",
    missing: "放弃",
  };
  return labels[level] || level;
}

function displayAdviceLabel(decision) {
  const label = decision?.advice_label || labelAdviceLevel(decision?.advice_level);
  if (decision?.market === "score" && (label === "放弃" || label === "仅作娱乐参考")) {
    return "仅作娱乐参考";
  }
  return label;
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
  const decisions = analysis.decision_comparisons || [];
  const primary =
    decisions.find((decision) => decision.advice_label === "建议") ||
    decisions.find((decision) => decision.advice_label === "小额参考") ||
    decisions[0];
  if (!primary) {
    nodes.recommendationSummary.innerHTML = "<p>当前没有可用建议。</p>";
    return;
  }
  const topModel = primary.model_suggestions?.[0];
  const warnings = primary.missing_info?.length
    ? `<div class="warning-list">${primary.missing_info.map((warning) => `<div>${escapeHtml(warning)}</div>`).join("")}</div>`
    : "";
  const reasons = primary.reasons?.length
    ? `<div class="reason-list">${primary.reasons.slice(0, 3).map((reason) => `<div>${escapeHtml(reason)}</div>`).join("")}</div>`
    : "";
  nodes.recommendationSummary.innerHTML = `
    <div class="pick-summary">
      <div>
        <span class="subtle">综合优先看</span>
        <h2>${escapeHtml(primary.market_label)}</h2>
      </div>
      <span class="value-pill">${escapeHtml(primary.advice_label || labelAdviceLevel(primary.advice_level))}</span>
    </div>
    <div class="quick-stats">
      <div><span>赔率模型看好</span><strong>${escapeHtml(modelLineText(primary.official_model, primary.market_favorite?.label || "缺官方赔率"))}</strong></div>
      <div><span>球队资料模型</span><strong>${escapeHtml(modelLineText(primary.team_model, topModel?.label || "资料缺失"))}</strong></div>
      <div><span>回报参考</span><strong>${escapeHtml(primary.best_return?.label || "无法计算")}</strong></div>
      <div><span>综合方案</span><strong>${escapeHtml(displayAdviceLabel(primary))}</strong></div>
    </div>
    <p class="plain-summary">${escapeHtml(primary.summary || "暂无综合说明。")}</p>
    ${reasons}
    ${warnings}
  `;
}

function renderAnalysis(analysis) {
  renderRecommendation(analysis);
  renderDecisionComparison(analysis.decision_comparisons || []);
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
                <span>${escapeHtml(displayAdviceLabel(decision))}</span>
              </div>
              <div class="decision-columns">
                <div>
                  <span>赔率模型看好</span>
                  <strong>${escapeHtml(modelLineText(decision.official_model, decision.market_favorite?.label || "官方赔率缺失"))}</strong>
                </div>
                <div>
                  <span>球队资料模型</span>
                  <strong>${escapeHtml(modelLineText(decision.team_model, "球队资料缺失"))}</strong>
                </div>
                <div>
                  <span>回报参考</span>
                  ${renderDecisionOption(decision.best_return, "无法计算")}
                </div>
                <div>
                  <span>综合方案</span>
                  <strong>${escapeHtml(displayAdviceLabel(decision))}</strong>
                  <small>${escapeHtml(decision.summary || "")}</small>
                </div>
              </div>
              ${decision.market === "score" ? renderScoreCandidates(decision.score_candidates || []) : ""}
              <div class="decision-missing">
                <span>缺失信息</span>
                <strong>${escapeHtml(decision.missing_info?.length ? decision.missing_info.join("；") : "无")}</strong>
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

function modelLineText(line, fallback) {
  if (!line) return fallback;
  const label = line.selection_label || line.label || "暂无";
  const probability = line.probability == null ? "" : ` · 概率 ${pct(line.probability)}`;
  const odds = line.decimal_odds == null ? "" : ` · 赔率 ${Number(line.decimal_odds).toFixed(2)}`;
  const payout =
    line.payout_if_hit_2 == null ? "" : ` · 2元一注中出返还 ${Number(line.payout_if_hit_2).toFixed(2)}元`;
  const confidence = line.confidence_label ? ` · 置信度${line.confidence_label}` : "";
  return `${label}${probability}${odds}${payout}${confidence}`;
}

function renderScoreCandidates(candidates) {
  if (!candidates?.length) return "";
  const visible = candidates.slice(0, 5);
  const rows = visible
    .map(
      (candidate) => `
        <tr>
          <td><strong>${escapeHtml(candidate.label)}</strong>${candidate.model_scoreline ? `<small>模型比分 ${escapeHtml(candidate.model_scoreline)}</small>` : ""}</td>
          <td>${candidate.official_probability == null ? "缺失" : pct(candidate.official_probability)}</td>
          <td>${candidate.team_probability == null ? "缺失" : pct(candidate.team_probability)}</td>
          <td>${candidate.combined_probability == null ? "缺失" : pct(candidate.combined_probability)}</td>
          <td>${candidate.decimal_odds == null ? "缺失" : Number(candidate.decimal_odds).toFixed(2)}</td>
          <td>${candidate.payout_if_hit_2 == null ? "无法计算" : `${Number(candidate.payout_if_hit_2).toFixed(2)}元`}</td>
          <td>${escapeHtml(candidate.confidence_label || "低")}</td>
          <td>${escapeHtml(candidate.reason || "")}</td>
        </tr>
      `,
    )
    .join("");
  return `
    <details class="score-candidates">
      <summary>比分候选表</summary>
      <table>
        <thead>
          <tr>
            <th>比分</th>
            <th>赔率概率</th>
            <th>资料概率</th>
            <th>综合概率</th>
            <th>赔率</th>
            <th>2元一注中出返还</th>
            <th>置信度</th>
            <th>理由</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </details>
  `;
}

function renderPayout(option) {
  if (!option || option.payout_if_hit_2 == null) return "2元一注返还：无法计算";
  return `2元一注返还：${Number(option.payout_if_hit_2).toFixed(2)}元`;
}

function renderDecisionOption(option, fallback) {
  if (!option) {
    return `<strong>${escapeHtml(fallback)}</strong><small>2元一注返还：无法计算</small>`;
  }
  const probability = option.probability == null ? "" : ` · 概率 ${pct(option.probability)}`;
  const odds = option.decimal_odds == null ? "" : ` · 赔率 ${Number(option.decimal_odds).toFixed(2)}`;
  return `
    <strong>${escapeHtml(option.label)}</strong>
    <small>${escapeHtml(`${renderPayout(option)}${odds}${probability}`)}</small>
  `;
}

function renderModelSuggestions(options) {
  if (!options?.length) {
    return '<strong>暂无</strong><small>模型依据不足</small>';
  }
  return `
    <div class="decision-option-list">
      ${options
        .map(
          (option) => `
            <div>
              <strong>${escapeHtml(option.label)}</strong>
              <small>${escapeHtml(`${renderPayout(option)}${option.decimal_odds == null ? "" : ` · 赔率 ${Number(option.decimal_odds).toFixed(2)}`}${option.probability == null ? "" : ` · 概率 ${pct(option.probability)}`}`)}</small>
            </div>
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
                <div><span>综合风险</span><strong>${escapeHtml(labelRisk(parlay.risk))}</strong></div>
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
