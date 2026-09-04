// Pyodide 부트스트랩: solarmaps 패키지와 쾨펜 이진 격자를 가상 FS에 올리고
// solarmaps.api 함수를 호출하는 얇은 래퍼만 제공한다. 계산 로직은 전혀
// 여기 두지 않는다 — 전부 파이썬 쪽 solarmaps/ 가 단일 진실 원천이다.

const PYODIDE_VERSION = "v314.0.6"; // Pyodide는 314.x.y부터 내장 CPython 버전과 정렬해 버전을 매김 (Python 3.14)
const PYODIDE_CDN_BASE = `https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/`;

let pyodideReadyPromise = null;

function onBootProgress(message) {
  const el = document.getElementById("boot-text");
  if (el) el.textContent = message;
}

async function loadPyodideRuntime() {
  if (!window.loadPyodide) {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PYODIDE_CDN_BASE + "pyodide.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Pyodide 스크립트 로드 실패"));
      document.head.appendChild(script);
    });
  }

  onBootProgress("Python 런타임 불러오는 중…");
  const pyodide = await window.loadPyodide({ indexURL: PYODIDE_CDN_BASE });

  onBootProgress("계산 엔진(solarmaps) 준비 중…");
  const zipResp = await fetch("py/solarmaps.zip");
  const zipBuf = await zipResp.arrayBuffer();
  pyodide.unpackArchive(zipBuf, "zip");

  onBootProgress("쾨펜 기후 데이터 불러오는 중…");
  // fetch 경로는 페이지 루트(=public/) 기준 "data/...", 가상 FS 경로는
  // solarmaps.koppen.load_grid()의 기본 탐색 경로(_PACKAGE_DIR.parent/public/data)와
  // 맞추기 위해 "public/data/..." — 패키지가 cwd/solarmaps/*.py 로 풀리므로 parent=cwd.
  await mountDataFile(pyodide, "data/koppen.bin", "public/data/koppen.bin");
  await mountDataFile(pyodide, "data/koppen_legend.json", "public/data/koppen_legend.json");

  pyodide.runPython("import sys; sys.path.insert(0, '.')");

  onBootProgress("완료");
  return pyodide;
}

async function mountDataFile(pyodide, fetchPath, vfsPath) {
  const resp = await fetch(fetchPath);
  if (!resp.ok) throw new Error(`데이터 파일 로드 실패: ${fetchPath}`);
  const buf = new Uint8Array(await resp.arrayBuffer());
  const parts = vfsPath.split("/");
  let dir = "";
  for (let i = 0; i < parts.length - 1; i++) {
    dir += (dir ? "/" : "") + parts[i];
    try {
      pyodide.FS.mkdir(dir);
    } catch (e) {
      // 이미 존재하면 무시
    }
  }
  pyodide.FS.writeFile(vfsPath, buf);
}

export function getPyodide() {
  if (!pyodideReadyPromise) {
    pyodideReadyPromise = loadPyodideRuntime();
  }
  return pyodideReadyPromise;
}

export async function getConstants() {
  const pyodide = await getPyodide();
  const result = pyodide.runPython(`
import json
from solarmaps.api import get_constants
json.dumps(get_constants())
`);
  return JSON.parse(result);
}

// NASA POWER 조회는 solarmaps.nasa_power(pyodide.http.pyfetch)가 처리한다 —
// JS에서 별도로 fetch 로직을 중복 구현하지 않는다.
export async function analyzeAtPoint(lat, lon, utcOffsetHours, options = {}) {
  const pyodide = await getPyodide();
  const preciseAzimuth = options.preciseAzimuth ? "True" : "False";

  const code = `
import json
from solarmaps.nasa_power import fetch_monthly_climate_async, PowerFetchError
from solarmaps.api import analyze
from dataclasses import asdict

async def _run():
    payload = None
    power_error = None
    try:
        monthly = await fetch_monthly_climate_async(${lat}, ${lon})
        payload = [asdict(m) for m in monthly]
    except PowerFetchError as e:
        power_error = str(e)
    result = analyze(
        ${lat}, ${lon}, ${utcOffsetHours},
        monthly_climate_payload=payload,
        precise_azimuth_mode=${preciseAzimuth},
    )
    result["power_error"] = power_error
    return json.dumps(result)

await _run()
`;
  const resultJson = await pyodide.runPythonAsync(code);
  return JSON.parse(resultJson);
}

export async function lookupKoppen(lat, lon) {
  const pyodide = await getPyodide();
  const code = `
import json
from solarmaps.api import lookup_koppen
json.dumps(lookup_koppen(${lat}, ${lon}))
`;
  return JSON.parse(pyodide.runPython(code));
}
