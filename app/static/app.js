import { pct, renderBars, renderHeatmap, renderScatter } from "./charts.js";

const state = {
  matches: [],
  selectedMatchId: null,
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
  scoreHeatmap: document.querySelector("#score-heatmap"),
  topScores: document.querySelector("#top-scores"),
  goalsBars: document.querySelector("#goals-bars"),
  overUnderBars: document.querySelector("#over-under-bars"),
  halfTimeBars: document.querySelector("#half-time-bars"),
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
  return labels[selection] || selection.replace("_", " ");
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
  const fallback = status.using_fallback ? " · fallback" : "";
  nodes.feedStatus.innerHTML = `
    <span class="feed-dot ${healthClass}"></span>
    <span>${escapeHtml(status.source)}${fallback}</span>
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
        <button class="match-row ${match.match_id === state.selectedMatchId ? "active" : ""}" data-match-id="${escapeAttribute(match.match_id)}">
          <strong>${escapeHtml(match.home.name)} vs ${escapeHtml(match.away.name)}</strong>
          <div>${escapeHtml(match.competition)} · ${escapeHtml(formatKickoff(match.kickoff_utc))}</div>
          <span class="pill">数据质量 ${pct(match.context.data_quality)}</span>
          ${renderOddsMovement(match)}
        </button>
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
  nodes.recommendationSummary.innerHTML = `
    <h2>${escapeHtml(labelSelection(pick.selection))}</h2>
    <p>市场：${escapeHtml(pick.market)}</p>
    <p>模型概率：${pct(pick.model_probability)}</p>
    <p>期望值：${pick.expected_value === null ? "无赔率" : pct(pick.expected_value)}</p>
    <p>风险：${escapeHtml(pick.risk)}</p>
  `;
}

function renderAnalysis(analysis) {
  renderRecommendation(analysis);
  renderBars(
    nodes.winnerBars,
    analysis.winner_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })),
  );
  nodes.dataQuality.innerHTML = `<div class="pill">${pct(analysis.data_quality)}</div><p>预期进球 ${analysis.expected_home_goals.toFixed(2)} - ${analysis.expected_away_goals.toFixed(2)}</p>`;
  renderHeatmap(nodes.scoreHeatmap, analysis.score_probabilities);
  nodes.topScores.innerHTML = `<div class="score-list">${analysis.top_scores
    .map((item) => `<div><strong>${item.home_goals}-${item.away_goals}</strong> ${pct(item.probability)}</div>`)
    .join("")}</div>`;
  renderBars(
    nodes.goalsBars,
    analysis.total_goal_probabilities.map((item) => ({ label: item.selection, value: item.probability })),
    "var(--blue)",
  );
  renderBars(
    nodes.overUnderBars,
    analysis.over_under_probabilities.map((item) => ({ label: item.selection, value: item.probability })),
    "var(--amber)",
  );
  renderBars(
    nodes.halfTimeBars,
    analysis.half_time_probabilities.map((item) => ({ label: labelSelection(item.selection), value: item.probability })),
    "var(--blue)",
  );
}

function renderParlays(parlays) {
  renderScatter(nodes.parlayScatter, parlays);
  if (!parlays.length) {
    nodes.parlayResults.innerHTML = "<p>当前没有满足条件的串关组合。</p>";
    return;
  }
  nodes.parlayResults.innerHTML = parlays
    .map(
      (parlay) => `
        <article class="parlay-card">
          <h3>${parlay.leg_count}串1 · ${escapeHtml(parlay.risk)}</h3>
          <p>命中率 ${pct(parlay.combined_probability)} · 总赔率 ${parlay.combined_odds.toFixed(2)} · EV ${pct(parlay.expected_value)}</p>
          <p>${escapeHtml(parlay.explanation)}</p>
          ${parlay.legs.map((leg) => `<div>${escapeHtml(leg.label)} · ${pct(leg.probability)} · ${leg.decimal_odds.toFixed(2)}</div>`).join("")}
        </article>
      `,
    )
    .join("");
}

async function loadAnalysis(matchId) {
  const analysis = await fetchJson(`/api/matches/${matchId}/analysis`);
  renderAnalysis(analysis);
}

async function loadParlays() {
  const parlays = await fetchJson(`/api/parlays?strategy=${state.strategy}&window=${state.window}`);
  renderParlays(parlays);
}

async function loadFeedStatus() {
  const status = await fetchJson("/api/feed/status");
  renderFeedStatus(status);
}

async function loadMatches() {
  state.matches = await fetchJson(`/api/matches?window=${state.window}`);
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
}

nodes.matchList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-match-id]");
  if (!button) return;
  state.selectedMatchId = button.dataset.matchId;
  renderMatches();
  await loadAnalysis(state.selectedMatchId);
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
    await refreshLiveData();
  });
});

nodes.refreshButton.addEventListener("click", refreshLiveData);

setInterval(refreshLiveData, 30_000);

refreshLiveData().catch((error) => {
  document.body.insertAdjacentHTML("afterbegin", `<div class="panel">加载失败：${escapeHtml(error.message)}</div>`);
});
