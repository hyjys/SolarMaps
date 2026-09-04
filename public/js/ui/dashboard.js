// school_energy_summary/latest 요약 카드 (규격서 §3 컬렉션 4).

import { createCard, statRowHtml } from "./dom.js";

export function renderDashboard(container, summary) {
  container.innerHTML = "";
  if (!summary) {
    container.appendChild(
      createCard({
        title: "학교 전력 기여도",
        bodyHtml: `<p style="color:var(--text-secondary);font-size:12px;">아직 집계 데이터가 없습니다.</p>`,
      })
    );
    return;
  }

  const card = createCard({
    title: "학교 전력 기여도",
    subtitle: summary.date,
    bodyHtml: `
      ${statRowHtml("금일 실측 발전량", `${summary.today_total_generation_kwh?.toFixed(2) ?? "-"} kWh`)}
      ${statRowHtml("실제 기여율", `${summary.real_contribution_percent?.toFixed(2) ?? "-"} %`)}
      ${statRowHtml("전면 설치 시뮬레이션 자립률", `${summary.simulated_self_sufficiency_percent?.toFixed(1) ?? "-"} %`, { big: true })}
      ${statRowHtml("탄소 저감량", `${summary.co2_reduced_kg?.toFixed(2) ?? "-"} kg`)}
      ${statRowHtml("소나무 식재 환산", `${summary.tree_planted_equivalent?.toFixed(1) ?? "-"} 그루`)}
    `,
  });
  container.appendChild(card);
}
