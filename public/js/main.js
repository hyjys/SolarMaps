import { analyzeAtPoint, getConstants, getPyodide } from "./py-bridge.js";
import { subscribe, subscribeDoc } from "./firestore.js";
import { initMap, onMapClick, renderCampusPolygons, renderStationMarkers } from "./map.js";
import { renderDashboard } from "./ui/dashboard.js";
import { renderError, renderLoading, renderPlaceholder, renderResult } from "./ui/result-panel.js";

async function boot() {
  const overlay = document.getElementById("boot-overlay");
  const resultPanel = document.getElementById("result-panel");
  const dashboardPanel = document.getElementById("dashboard-panel");

  renderPlaceholder(resultPanel);
  resultPanel.hidden = true; // 지도가 뜰 때까지는 숨김

  const map = initMap("map");

  // Pyodide 부팅과 지도 초기화를 병렬로 — 지도는 Pyodide 없이도 먼저 보인다(계획서 위험 대응).
  const [constants] = await Promise.all([
    getPyodide().then(() => getConstants()),
  ]);

  overlay.hidden = true;
  resultPanel.hidden = false;
  map.invalidateSize(); // 오버레이가 사라지며 레이아웃이 다시 확정된 뒤 지도 크기 재계산

  onMapClick(map, async (lat, lon) => {
    renderLoading(resultPanel);
    try {
      const utcOffsetHours = Math.round(lon / 15); // 경도 기반 표준시간대 근사 (geometry.py 표준시 규약과 동일)
      const result = await analyzeAtPoint(lat, lon, utcOffsetHours);
      renderResult(resultPanel, result);
    } catch (err) {
      console.error(err);
      renderError(resultPanel, err.message || String(err));
    }
  });

  // Firestore 모니터링 (미설정 시 조용히 건너뜀 — firestore.js 참고)
  subscribe("solar_stations", (docs) => {
    renderStationMarkers(map, docs.map((d) => d.data), constants.marker_state_thresholds);
  });

  subscribe("campus_polygons", (docs) => {
    renderCampusPolygons(
      map,
      docs.map((d) => ({ type: "Feature", id: d.id, properties: d.data.properties, geometry: d.data.geometry }))
    );
  });

  subscribeDoc("school_energy_summary", "latest", (data) => {
    renderDashboard(dashboardPanel, data);
  });
}

boot().catch((err) => {
  console.error("부팅 실패:", err);
  const bootText = document.getElementById("boot-text");
  if (bootText) bootText.textContent = `부팅 실패: ${err.message || err}`;
});
