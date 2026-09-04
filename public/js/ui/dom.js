// DOM 카드/행 생성 공용 팩토리 (계획서 "대원칙 1" — 중복 제거).
// result-panel.js, station-popup.js, dashboard.js가 모두 이 함수들을 공유한다.

export function createCard({ title, subtitle, bodyHtml, headerActionsHtml = "" }) {
  const card = document.createElement("div");
  card.className = "card";
  card.innerHTML = `
    <div class="card-header" style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
      <div>
        <h2>${title}</h2>
        ${subtitle ? `<p>${subtitle}</p>` : ""}
      </div>
      ${headerActionsHtml}
    </div>
    <div class="card-body">${bodyHtml}</div>
  `;
  return card;
}

export function statRowHtml(label, value, { big = false } = {}) {
  return `<div class="stat-row"><span class="label">${label}</span><span class="value${big ? " big" : ""}">${value}</span></div>`;
}

export function badgeHtml(text, { variant = "outline" } = {}) {
  return `<span class="badge badge-${variant}">${text}</span>`;
}

export function alertHtml(text, { variant = "info" } = {}) {
  return `<div class="alert alert-${variant}">${text}</div>`;
}
