import { isFirebaseConfigured } from "../firebase-config.js?v=3";
import { fetchCollectionFromServer } from "../firestore.js?v=3";

const logFields = [
  "station_id",
  "timestamp",
  "iso_time",
  "date",
  "voltage_avg_v",
  "current_avg_a",
  "power_avg_w",
  "power_max_w",
  "energy_delta_wh",
  "temp_c",
  "sample_count",
];

function csvCell(value) {
  if (value == null) return "";
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  let cell = typeof value.toDate === "function"
    ? value.toDate().toISOString()
    : typeof value === "object" ? JSON.stringify(value) : String(value);
  // 스프레드시트가 텍스트를 수식으로 실행하지 않도록 한다.
  if (/^\s*[=+\-@\uFF1D\uFF0B\uFF0D\uFF20]/u.test(cell) || /^[\t\r\n]/u.test(cell)) cell = `'${cell}`;
  return `"${cell.replaceAll('"', '""')}"`;
}

function logTime({ data }) {
  const time = Date.parse(data.iso_time);
  if (Number.isFinite(time)) return time;
  if (typeof data.timestamp?.toMillis === "function") return data.timestamp.toMillis();
  const timestamp = Date.parse(data.timestamp);
  return Number.isFinite(timestamp) ? timestamp : Infinity;
}

function downloadLogs(logs) {
  const extraFields = new Set();
  for (const { data } of logs) {
    for (const field of Object.keys(data)) {
      if (!logFields.includes(field)) extraFields.add(field);
    }
  }
  const fields = [...logFields, ...Array.from(extraFields).sort()];
  let idColumn = "document_id";
  while (extraFields.has(idColumn)) idColumn = `_${idColumn}`;

  const rows = [[idColumn, ...fields].map(csvCell).join(",")];
  const orderedLogs = logs.map((log) => ({ ...log, time: logTime(log) }));
  orderedLogs.sort((left, right) => left.time - right.time || left.id.localeCompare(right.id));
  for (const { id, data } of orderedLogs) {
    rows.push([id, ...fields.map((field) => Object.hasOwn(data, field) ? data[field] : null)].map(csvCell).join(","));
  }

  const blob = new Blob(["\uFEFF", rows.join("\r\n"), "\r\n"], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "SolarMaps_solar_logs.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function initSolarLogExport(button, status) {
  if (!isFirebaseConfigured()) {
    status.textContent = "Firebase 연결 설정이 필요합니다.";
    return;
  }

  button.disabled = false;
  button.addEventListener("click", async () => {
    button.disabled = true;
    status.textContent = "전체 계측 기록을 불러오는 중…";

    try {
      const logs = await fetchCollectionFromServer("solar_logs");
      if (logs.length === 0) {
        status.textContent = "다운로드할 계측 기록이 없습니다.";
        return;
      }
      downloadLogs(logs);
      status.textContent = `${logs.length.toLocaleString("ko-KR")}건의 CSV 다운로드를 시작했습니다.`;
    } catch (err) {
      console.error("Solar Logs 다운로드 실패:", err);
      status.textContent = "기록을 다운로드하지 못했습니다. 잠시 후 다시 시도해 주세요.";
    } finally {
      button.disabled = false;
    }
  });
}
