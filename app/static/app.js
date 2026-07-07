import { pct, renderBars, renderHeatmap, renderScatter } from "./charts.js";

const state = {
  matches: [],
  selectedMatchId: null,
  strategy: "balanced",
};

const nodes = {
  matchList: document.querySelector("#match-list"),
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

function renderMatches() {
  nodes.matchList.innerHTML = state.matches
    .map(
      (match) => `
        <button class="match-row ${match.match_id === state.selectedMatchId ? "active" : ""}" data-match-id="${match.match_id}">
          <strong>${match.home.name} vs ${match.away.name}</strong>
          <div>${match.competition}</div>
          <span class="pill">数据质量 ${pct(match.context.data_quality)}</span>
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
    <h2>${labelSelection(pick.selection)}</h2>
    <p>市场：${pick.market}</p>
    <p>模型概率：${pct(pick.model_probability)}</p>
    <p>期望值：${pick.expected_value === null ? "无赔率" : pct(pick.expected_value)}</p>
    <p>风险：${pick.risk}</p>
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
          <h3>${parlay.leg_count}串1 · ${parlay.risk}</h3>
          <p>命中率 ${pct(parlay.combined_probability)} · 总赔率 ${parlay.combined_odds.toFixed(2)} · EV ${pct(parlay.expected_value)}</p>
          <p>${parlay.explanation}</p>
          ${parlay.legs.map((leg) => `<div>${leg.label} · ${pct(leg.probability)} · ${leg.decimal_odds.toFixed(2)}</div>`).join("")}
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
  const parlays = await fetchJson(`/api/parlays?strategy=${state.strategy}`);
  renderParlays(parlays);
}

async function loadMatches() {
  state.matches = await fetchJson("/api/matches");
  state.selectedMatchId = state.selectedMatchId || state.matches[0]?.match_id;
  renderMatches();
  if (state.selectedMatchId) {
    await loadAnalysis(state.selectedMatchId);
  }
  await loadParlays();
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

nodes.refreshButton.addEventListener("click", loadMatches);

loadMatches().catch((error) => {
  document.body.insertAdjacentHTML("afterbegin", `<div class="panel">加载失败：${error.message}</div>`);
});
