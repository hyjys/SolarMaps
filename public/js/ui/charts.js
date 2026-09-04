// 인라인 SVG 차트. 별도 차트 라이브러리를 쓰지 않는다(계획서: charts.js — 차트 라이브러리 미사용).

const MONTH_LABELS_KO = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"];

export function monthlyBarChartSvg(monthly, { width = 320, height = 120 } = {}) {
  const padding = { top: 8, right: 8, bottom: 18, left: 8 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;
  const maxVal = Math.max(1e-6, ...monthly.map((m) => m.energy_kwh_m2));
  const barW = chartW / monthly.length;

  const bars = monthly
    .map((m, i) => {
      const h = (m.energy_kwh_m2 / maxVal) * chartH;
      const x = padding.left + i * barW + barW * 0.15;
      const y = padding.top + (chartH - h);
      const w = barW * 0.7;
      return `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${w.toFixed(1)}" height="${h.toFixed(1)}" rx="2" fill="var(--primary)" opacity="0.85"><title>${MONTH_LABELS_KO[m.month - 1]}월: ${m.energy_kwh_m2.toFixed(1)}</title></rect>`;
    })
    .join("");

  const labels = monthly
    .map((m, i) => {
      const x = padding.left + i * barW + barW / 2;
      return `<text x="${x.toFixed(1)}" y="${height - 4}" font-size="8" text-anchor="middle" fill="var(--text-secondary)">${MONTH_LABELS_KO[m.month - 1]}</text>`;
    })
    .join("");

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg">${bars}${labels}</svg>`;
}

export function azimuthLossCurveSvg(points, { width = 320, height = 100 } = {}) {
  const padding = { top: 10, right: 10, bottom: 18, left: 28 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;
  const maxLoss = Math.max(1, ...points.map((p) => p.loss_percent));
  const minAz = Math.min(...points.map((p) => p.azimuth_deg));
  const maxAz = Math.max(...points.map((p) => p.azimuth_deg));
  const span = maxAz - minAz || 1;

  const coords = points.map((p) => {
    const x = padding.left + ((p.azimuth_deg - minAz) / span) * chartW;
    const y = padding.top + chartH - (p.loss_percent / maxLoss) * chartH;
    return [x, y];
  });

  const path = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const zeroX = padding.left + ((0 - minAz) / span) * chartW;

  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" xmlns="http://www.w3.org/2000/svg">
    <line x1="${zeroX.toFixed(1)}" y1="${padding.top}" x2="${zeroX.toFixed(1)}" y2="${padding.top + chartH}" stroke="var(--border)" stroke-dasharray="3,3" />
    <path d="${path}" fill="none" stroke="var(--warning)" stroke-width="2" />
    <text x="${padding.left}" y="${height - 4}" font-size="8" fill="var(--text-secondary)">${minAz}°</text>
    <text x="${width - padding.right}" y="${height - 4}" font-size="8" text-anchor="end" fill="var(--text-secondary)">+${maxAz}°</text>
    <text x="${zeroX.toFixed(1)}" y="${padding.top - 2}" font-size="8" text-anchor="middle" fill="var(--text-secondary)">최적</text>
  </svg>`;
}
