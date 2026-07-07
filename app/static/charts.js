export function pct(value) {
  return `${(value * 100).toFixed(1)}%`;
}

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

export function renderBars(node, rows, color = "var(--green)") {
  node.innerHTML = rows
    .map(
      (row) => `
        <div class="chart-row">
          <div>${escapeHtml(row.label)}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${Math.max(0, Math.min(100, row.value * 100))}%; background:${color}"></div></div>
          <strong>${pct(row.value)}</strong>
        </div>
      `,
    )
    .join("");
}

export function renderHeatmap(node, scores) {
  if (!scores.length) {
    node.innerHTML = "<p>暂无比分分布。</p>";
    return;
  }
  const maxProbability = Math.max(...scores.map((item) => item.probability));
  if (maxProbability <= 0) {
    node.innerHTML = "<p>暂无有效比分分布。</p>";
    return;
  }
  const visible = scores.filter((item) => item.home_goals <= 8 && item.away_goals <= 8);
  if (!visible.length) {
    node.innerHTML = "<p>暂无可显示比分分布。</p>";
    return;
  }
  node.innerHTML = `<div class="heatmap">${visible
    .map((item) => {
      const intensity = item.probability / maxProbability;
      const alpha = 0.12 + intensity * 0.78;
      const label = `${item.home_goals}-${item.away_goals}`;
      return `<div class="heat-cell" style="background: rgba(34, 122, 92, ${alpha})" title="${escapeAttribute(`${label} ${pct(item.probability)}`)}">${escapeHtml(label)}<br>${pct(item.probability)}</div>`;
    })
    .join("")}</div>`;
}

export function renderScatter(node, parlays) {
  if (!parlays.length) {
    node.innerHTML = "";
    return;
  }
  const width = 640;
  const height = 220;
  const padding = 28;
  const maxProfit = Math.max(5, ...parlays.map((item) => Math.max(0, item.expected_profit_100 ?? item.expected_value * 100)));
  const points = parlays
    .map((item) => {
      const x = padding + item.combined_probability * (width - padding * 2);
      const profit = item.expected_profit_100 ?? item.expected_value * 100;
      const y = height - padding - (Math.max(0, profit) / maxProfit) * (height - padding * 2);
      return `<circle cx="${x}" cy="${y}" r="${7 + item.leg_count}" fill="#2f5f98"><title>${item.leg_count}串1 预计命中 ${pct(item.combined_probability)} 长期理论盈亏 ${profit.toFixed(1)}元</title></circle>`;
    })
    .join("");

  node.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="串关风险收益图">
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#d9e1df" />
      <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#d9e1df" />
      ${points}
      <text x="${padding}" y="${height - 6}" font-size="12">预计命中</text>
      <text x="4" y="${padding}" font-size="12">理论盈亏</text>
    </svg>
  `;
}
