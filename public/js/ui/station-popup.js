// 규격서(docs/DATA_SPEC.md) §4 마커 상태 매핑. 임계값 자체는 solarmaps.constants
// (Python)에서 가져온다 — 색상 숫자를 JS에 다시 정의하지 않는다.

export function computeMarkerVisual(station, thresholds) {
  const live = station.live_status || {};
  const rated = station.hardware?.rated_power_w ?? 0;
  const power = live.power_w ?? 0;
  const lastUpdated = live.last_updated ? new Date(live.last_updated) : null;
  const staleMinutes = lastUpdated ? (Date.now() - lastUpdated.getTime()) / 60000 : Infinity;

  if (staleMinutes > thresholds.OFFLINE.stale_minutes) {
    return thresholds.OFFLINE;
  }
  if (rated > 0 && power >= rated * thresholds.GENERATING_HIGH.power_ratio_of_rated) {
    return thresholds.GENERATING_HIGH;
  }
  if (power > thresholds.GENERATING_LOW.power_w_min) {
    return thresholds.GENERATING_LOW;
  }
  return thresholds.IDLE;
}

export function stationPopupHtml(station, visual) {
  const live = station.live_status || {};
  const hw = station.hardware || {};
  return `
    <div style="min-width:200px">
      <strong>${station.name || station.station_id}</strong>
      <div style="margin-top:4px;color:var(--text-secondary)">${station.building_name || ""}</div>
      <div style="margin-top:8px;display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;font-size:12px;">
        <span>출력</span><strong>${(live.power_w ?? 0).toFixed(1)} W</strong>
        <span>금일 발전량</span><strong>${(live.today_energy_wh ?? 0).toFixed(0)} Wh</strong>
        <span>설치각</span><strong>${hw.tilt_angle_deg ?? "-"}° / ${hw.azimuth_deg ?? "-"}°</strong>
        <span>패널온도</span><strong>${live.temp_c != null ? live.temp_c.toFixed(1) + "°C" : "-"}</strong>
      </div>
    </div>
  `;
}
