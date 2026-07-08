const state = {
  matches: [],
  selectedMatchId: null,
  selectedParlayMatchIds: new Set(),
  window: "next",
};

const nodes = {
  matchList: document.querySelector("#match-list"),
  feedStatus: document.querySelector("#feed-status"),
  refreshButton: document.querySelector("#refresh-button"),
  decisionComparison: document.querySelector("#decision-comparison"),
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

function formatKickoff(value) {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
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

function labelSelection(selection) {
  const labels = {
    home: "主胜",
    draw: "平局",
    away: "客胜",
  };
  return labels[selection] || selection;
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

function renderFeedStatus(status) {
  const healthClass = status.healthy ? "healthy" : "unhealthy";
  const fallback = status.using_fallback ? " · 备用" : "";
  nodes.feedStatus.innerHTML = `
    <span class="feed-dot ${healthClass}"></span>
    <span>${escapeHtml(labelSource(status.source))}${fallback}</span>
    <span>${escapeHtml(status.message)}</span>
  `;
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

function money(value) {
  if (value == null) return "--";
  return `${Number(value).toFixed(2)}元`;
}

function odds(value) {
  if (value == null) return "--";
  return Number(value).toFixed(2);
}

function adviceReason(decision) {
  if (decision.missing_info?.length) {
    return decision.missing_info.join("；");
  }
  const label = decision.odds_selection_label || decision.market_favorite?.label || "--";
  return `体彩当前最低赔率是 ${label}，按真实赔率给出参考。`;
}

function renderDecisionComparison(decisions) {
  if (!decisions.length) {
    nodes.decisionComparison.innerHTML = "<p>当前没有可用的体彩赔率建议。</p>";
    return;
  }
  nodes.decisionComparison.innerHTML = `
    <table class="simple-table">
      <thead>
        <tr>
          <th>玩法</th>
          <th>推荐买法</th>
          <th>赔率</th>
          <th>2元一注返还</th>
          <th>理由</th>
        </tr>
      </thead>
      <tbody>
        ${decisions
          .map(
            (decision) => `
              <tr>
                <td>${escapeHtml(decision.market_label)}</td>
                <td><strong>${escapeHtml(decision.odds_selection_label || decision.market_favorite?.label || "赔率缺失")}</strong></td>
                <td>${escapeHtml(odds(decision.odds_decimal || decision.market_favorite?.decimal_odds))}</td>
                <td>${escapeHtml(money(decision.market_favorite?.payout_if_hit_2))}</td>
                <td>${escapeHtml(adviceReason(decision))}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderAnalysis(analysis) {
  renderDecisionComparison(analysis.decision_comparisons || []);
}

function renderParlayList(parlays, title) {
  if (!parlays.length) {
    return `<section class="parlay-section"><h3>${escapeHtml(title)}</h3><p>所选比赛没有足够的体彩真实赔率，暂时不能计算串关。</p></section>`;
  }
  return `
    <section class="parlay-section">
      <h3>${escapeHtml(title)}</h3>
      <table class="simple-table">
        <thead>
          <tr>
            <th>串法</th>
            <th>推荐组合</th>
            <th>总赔率</th>
            <th>2元一注返还</th>
            <th>理由</th>
          </tr>
        </thead>
        <tbody>
          ${parlays
            .slice(0, 3)
            .map(
              (parlay) => `
                <tr>
                  <td>${parlay.leg_count}串1</td>
                  <td>${parlay.legs.map((leg) => escapeHtml(leg.label)).join("<br>")}</td>
                  <td>${Number(parlay.combined_odds || 0).toFixed(2)}</td>
                  <td>${money(parlay.payout_if_hit_2)}</td>
                  <td>${escapeHtml(parlay.explanation || "按真实赔率相乘计算。")}</td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    </section>
  `;
}

function renderParlays(payload) {
  if (!payload.strategy_groups) {
    nodes.parlayResults.innerHTML = renderParlayList(payload.winner_parlays || [], "真实赔率串关");
    return;
  }
  if (payload.selected_match_ids?.length < 2) {
    nodes.parlayResults.innerHTML = "<p>请先勾选至少两场比赛，再生成串关建议。</p>";
    return;
  }
  nodes.parlayResults.innerHTML = payload.strategy_groups
    .map((group) => renderParlayList(group.parlays || [], `${group.label} · 真实赔率串关`))
    .join("");
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
    renderParlays({ selected_match_ids: selectedIds, strategy_groups: [] });
    return;
  }
  const strategies = [
    ["conservative", "稳健"],
    ["balanced", "均衡"],
    ["return_seeking", "博收益"],
  ];
  const groups = await Promise.all(
    strategies.map(async ([strategy, label]) => {
      const params = new URLSearchParams({ strategy, window: state.window });
      selectedIds.forEach((matchId) => params.append("match_ids", matchId));
      const payload = await fetchJson(`/api/selected-parlays?${params.toString()}`);
      return { strategy, label, parlays: payload.winner_parlays || [] };
    }),
  );
  renderParlays({ selected_match_ids: selectedIds, strategy_groups: groups });
}

async function loadFeedStatus() {
  const status = await fetchJson("/api/feed/status");
  renderFeedStatus(status);
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
    nodes.decisionComparison.innerHTML = "<p>没有可分析的未开赛比赛。</p>";
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
