import { azimuthLossCurveSvg, monthlyBarChartSvg } from "./charts.js";
import { alertHtml, badgeHtml, createCard, statRowHtml } from "./dom.js";

const AZIMUTH_COMPASS = ["북", "북동", "동", "남동", "남", "남서", "서", "북서"];

function azimuthToCompassKo(deg) {
  const idx = Math.round(((deg % 360) / 45)) % 8;
  return AZIMUTH_COMPASS[idx];
}

export function renderLoading(container) {
  container.hidden = false;
  container.innerHTML = `
    <div class="card">
      <div class="loading-row"><div class="spinner"></div>계산 중…</div>
    </div>
  `;
}

export function renderPlaceholder(container) {
  container.hidden = false;
  container.innerHTML = `
    <div class="card">
      <div class="result-placeholder">지도를 클릭해 해당 위치의 최적 태양광 설치각을 계산하세요.</div>
    </div>
  `;
}

export function renderError(container, message) {
  container.hidden = false;
  container.innerHTML = "";
  const card = createCard({
    title: "계산 실패",
    bodyHtml: alertHtml(message, { variant: "warning" }),
  });
  container.appendChild(card);
}

export function renderResult(container, result) {
  container.hidden = false;
  container.innerHTML = "";

  const climateSourceBadge =
    result.climate_source === "nasa_power"
      ? badgeHtml("NASA POWER 실측 기후평년", { variant: "primary" })
      : badgeHtml("쾨펜 기반 근사치", { variant: "outline" });

  const powerWarning = result.power_error
    ? alertHtml(`NASA POWER 조회 실패로 쾨펜 근사치를 사용했습니다: ${result.power_error}`, { variant: "warning" })
    : "";

  const mainCard = createCard({
    title: "최적 설치각",
    subtitle: `북위 ${result.latitude.toFixed(4)}°, 동경 ${result.longitude.toFixed(4)}°`,
    headerActionsHtml: climateSourceBadge,
    bodyHtml: `
      ${powerWarning}
      <div class="grid-2">
        <div>${statRowHtml("경사각", `${result.tilt_deg.toFixed(1)}°`, { big: true })}</div>
        <div>${statRowHtml("방위각", `${result.azimuth_deg.toFixed(0)}° (${azimuthToCompassKo(result.azimuth_deg)})`, { big: true })}</div>
      </div>
      ${statRowHtml("수평 설치 대비 이득", `+${result.gain_vs_flat_percent.toFixed(1)}%`)}
      ${statRowHtml("연간 상대 발전량 지표", result.annual_energy_kwh_m2.toFixed(1))}
    `,
  });

  const climateCard = createCard({
    title: "기후 구분 (쾨펜)",
    bodyHtml: `
      ${statRowHtml("분류", `${result.koppen.code} — ${result.koppen.name_ko}`)}
      ${result.koppen.is_interpolated ? statRowHtml("비고", `가장 가까운 육지 데이터 사용 (${result.koppen.distance_deg.toFixed(1)}° 거리)`) : ""}
    `,
  });

  const monthlyCard = createCard({
    title: "월별 상대 발전량",
    bodyHtml: monthlyBarChartSvg(result.monthly),
  });

  const azimuthNote = result.azimuth_symmetric_model
    ? alertHtml(
        "월별 평년값 기반 모형은 하루 오전/오후가 대칭이라 방위각이 항상 적도 방향으로 계산됩니다. 아래 곡선은 방위각을 이 값에서 벗어났을 때의 손실률입니다.",
        { variant: "info" }
      )
    : "";

  const azimuthCard = createCard({
    title: "방위각 이탈 손실",
    bodyHtml: `${azimuthNote}${azimuthLossCurveSvg(result.azimuth_loss_curve)}`,
  });

  container.append(mainCard, climateCard, monthlyCard, azimuthCard);
}
