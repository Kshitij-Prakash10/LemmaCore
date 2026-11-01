// Failover Guardian front end. Plain JS and canvas, no external libraries. Works offline.
"use strict";

const FAULTS = ["U1_TRIP", "U2_TRIP", "STANDBY_STUCK", "MCB_TRIP", "UNIT_DERATE",
  "BLOWER_FAIL", "COMPRESSOR_FAIL", "TEMP_SENSOR_STUCK"];

// Plain-language names. The ids stay visible in small type so the app matches the code and the report.
const FAULT_TEXT = {
  U1_TRIP: ["Converter 1 trips off", "Converter 1"],
  U2_TRIP: ["Converter 2 trips off", "Converter 2"],
  STANDBY_STUCK: ["Standby does not take over", "Standby stuck"],
  MCB_TRIP: ["Panel breaker trips", "Breaker trips"],
  UNIT_DERATE: ["Converter 2 loses half its capacity", "Converter derated"],
  BLOWER_FAIL: ["Motor cooling blower fails", "Blower fails"],
  COMPRESSOR_FAIL: ["Brake compressor fails", "Compressor fails"],
  TEMP_SENSOR_STUCK: ["Temperature sensor freezes", "Sensor frozen"],
};
const FAULT_SHORT = {
  U1_TRIP: "Converter 1 off", U2_TRIP: "Converter 2 off", STANDBY_STUCK: "Standby stuck", MCB_TRIP: "Breaker trips",
  UNIT_DERATE: "Converter derated", BLOWER_FAIL: "Blower fails", COMPRESSOR_FAIL: "Compressor fails",
  TEMP_SENSOR_STUCK: "Sensor frozen",
};
const LOAD_TEXT = {
  motor_blower: "Motor cooling blower", oil_cooling_blower: "Oil cooling blower", oil_pump: "Oil pump",
  brake_compressor: "Brake air compressor", control_and_charger: "Control power and battery charger",
  cab_ac: "Cab air conditioning", lighting_and_fans: "Lighting and fans",
};
const DECISION_TEXT = {
  CONTINUE: ["Keep going to the next station", "tone-safe"],
  STOP_AT_NEXT: ["Stop at the nearest safe place", "tone-stop"],
  STOP_NOW: ["Stop now and call for help", "tone-unsafe"],
};
const LIMIT_TEXT = {
  heat: "Motor heat: the traction motors reach their trip temperature",
  air: "Brake air: the reservoir pressure falls to its safe minimum",
  battery: "Battery: control power runs flat",
  power: "Power: the working converters cannot carry the load",
  none: "Nothing within two hours",
};
const LIMIT_SHORT = {
  heat: "the motors overheat", air: "the brake air runs low", battery: "control power runs out",
  power: "the converters cannot carry the load", none: "any limit is reached",
};
const OUTCOME_TEXT = { SAFE: "Reaches the station safely", CONTROLLED_STOP: "Stopped in time", UNSAFE: "Unsafe" };
const LIMIT_HIT_TEXT = { motor_temp: "motor over-temperature", brake_air: "brake air too low", battery: "battery flat" };
const FLAG_TEXT = {
  temp_sensors_disagree: "The temperature reading looks frozen while the motor should be heating, so the advisor assumes the worst.",
  faults_inferred_from_signals: "The faults were guessed from the signals, not given.",
};
const COND_TEXT = { cool_flat: "Cool, flat", hot_flat: "Hot, flat", cool_climb: "Cool, climb", hot_climb: "Hot, climb" };
const TABS = ["guide", "advisor", "coverage", "realdata", "assumptions", "report"];

const $ = (id) => document.getElementById(id);
const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
let lastCase = null;
let stickTemp = false;

async function api(path, body) {
  const opt = body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
  };
  const r = await fetch(path, opt);
  return r.json();
}
function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}
const nice = (n) => LOAD_TEXT[n] || String(n).replace(/_/g, " ");
const tagList = (names, cls = "") => names.length
  ? `<div class="tags">${names.map((n) => `<span class="tag ${cls}">${esc(nice(n))}</span>`).join("")}</div>` : "";
function showError(el, what) {
  el.innerHTML = `<div class="error"><b>Something went wrong.</b> ${esc(what)} Check that the app server is still running, then try again.</div>`;
}

// ---------- tabs (the tab is kept in the address, so a link opens the same screen) ----------
document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
function showTab(name) {
  if (!TABS.includes(name)) name = "advisor";
  document.querySelectorAll("nav button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === name)));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === "tab-" + name));
  if (location.hash !== "#" + name) history.replaceState(null, "", "#" + name);
  if (name === "coverage") loadCoverage();
  if (name === "realdata") loadRealData();
  if (name === "assumptions") loadAssumptions();
  if (name === "report") loadReport();
}
window.addEventListener("hashchange", () => showTab(location.hash.slice(1)));

// ---------- advisor ----------
function buildFaultPicks() {
  $("fault-picks").innerHTML = FAULTS.map((f) =>
    `<label><input type="checkbox" value="${f}"><span class="f-name">${esc(FAULT_TEXT[f][0])}</span><span class="f-id">${f}</span></label>`).join("");
  $("fault-picks").addEventListener("change", (e) => {
    const on = [...document.querySelectorAll("#fault-picks input:checked")];
    if (on.length > 2) e.target.checked = false;
  });
}
[["ambient", "v-ambient"], ["gradient", "v-gradient"], ["dist", "v-dist"]].forEach(([i, v]) =>
  $(i).addEventListener("input", () => { $(v).textContent = $(i).value; }));
["ambient", "gradient", "train_load", "units", "dist"].forEach((i) =>
  $(i).addEventListener("change", () => { if (lastCase) runAdvisor(lastCase.diagnose); }));

function selectedFaults() {
  return [...document.querySelectorAll("#fault-picks input:checked")].map((x) => x.value);
}
function setFaults(list) {
  document.querySelectorAll("#fault-picks input").forEach((x) => { x.checked = list.includes(x.value); });
}
function setCondition(c) {
  $("ambient").value = c.ambient_c; $("v-ambient").textContent = c.ambient_c;
  $("gradient").value = c.gradient_pct; $("v-gradient").textContent = c.gradient_pct;
  if (c.train_load) $("train_load").value = c.train_load;
}
function setStick(on) {
  stickTemp = on;
  $("btn-stick").textContent = on ? "Unfreeze the temperature sensor" : "Freeze the temperature sensor";
}

async function runAdvisor(diagnose = false) {
  const req = {
    faults: selectedFaults(), ambient_c: +$("ambient").value, gradient_pct: +$("gradient").value,
    train_load: $("train_load").value, units: +$("units").value, dist_next_station_km: +$("dist").value,
    speed_kmph: 40, stick_temp: stickTemp, diagnose: diagnose, seed: 1, noise: 0.02,
  };
  lastCase = req;
  const busy = $("btn-run");
  busy.setAttribute("aria-busy", "true");
  $("decision-card").className = "sheet";
  $("decision-card").innerHTML = '<h2>Working it out</h2><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div>';
  try {
    const res = await api("/api/advise", req);
    renderAdvice(res, req);
    renderOutcomes(res);
    drawSeries($("chart-temp"), res.chart.t_s, [
      { y: res.chart.motor_temp_baseline, c: "--chart-base" },
      { y: res.chart.motor_temp_advisor, c: "--chart-adv" },
      { y: res.chart.motor_temp_observed, c: "--chart-obs", dash: true },
    ], res.chart.motor_temp_limit_c, "C");
    drawSeries($("chart-air"), res.chart.t_s, [
      { y: res.chart.air_baseline, c: "--chart-base" },
      { y: res.chart.air_advisor, c: "--chart-adv" },
    ], res.chart.air_min_bar, "bar");
  } catch (err) {
    showError($("decision-card"), "The advisor did not answer.");
  } finally {
    busy.removeAttribute("aria-busy");
  }
}

function renderAdvice(res, req) {
  const a = res.advice, d = res.diagnosis;
  const dec = DECISION_TEXT[a.decision] || [a.decision, ""];
  const dark = [];
  const other = [];
  a.flags.forEach((f) => {
    if (f.startsWith("dark_loads:")) dark.push(...f.slice(11).split(",").filter(Boolean));
    else other.push(f);
  });
  const tStation = req.dist_next_station_km / req.speed_kmph * 60;
  const why = `At least ${a.minutes_left_p5.toFixed(1)} minutes remain before ${LIMIT_SHORT[a.limiting_factor] || "a limit is reached"}. ` +
    `The next station is ${req.dist_next_station_km} km away, about ${tStation.toFixed(0)} minutes at ${req.speed_kmph} km/h.`;
  let diag = "";
  if (d) {
    if (!d.available) diag = `<div class="alert">Auto-diagnose is not available (${esc(d.reason || "no reason given")}). The advisor used its own rules.</div>`;
    else {
      const top = Object.entries(d.faults).sort((x, y) => y[1] - x[1]).slice(0, 4)
        .map(([f, p]) => `${esc((FAULT_TEXT[f] || [f])[0])} ${(p * 100).toFixed(0)}%`).join(", ");
      diag = `<dl class="facts"><div><dt>Auto-diagnosis</dt><dd>${esc(d.predicted.map((f) => (FAULT_TEXT[f] || [f])[0]).join(" and ") || "no fault found")}
        <span class="note">confidence ${(d.confidence * 100).toFixed(0)}%. Most likely: ${top}.
        ${d.used_by_advisor ? "" : "Not used for the advice: the advisor took the cautious path."}</span></dd></div></dl>`;
    }
  }
  const sure = a.confidence === "high" ? "High" : "Low";
  $("decision-card").className = "sheet";
  $("decision-card").innerHTML = `
    ${res.stub ? '<p class="warn">Stand-in core: these numbers are fake.</p>' : ""}
    <h2 class="decision ${dec[1]}">${esc(dec[0])}</h2>
    <p class="why">${esc(why)}</p>
    <dl class="facts">
      <div><dt>Minutes left</dt><dd><span class="num big">at least ${a.minutes_left_p5.toFixed(1)}</span>
        <span class="note">A cautious figure. The typical case is ${a.minutes_left_nominal.toFixed(1)} minutes.</span></dd></div>
      <div><dt>What limits it</dt><dd>${esc(LIMIT_TEXT[a.limiting_factor] || a.limiting_factor)}</dd></div>
      <div><dt>Switch off</dt><dd>${a.shed.length ? tagList(a.shed) : "Nothing needs switching off"}</dd></div>
      ${dark.length ? `<div><dt>Already without power</dt><dd>${tagList(dark, "dark")}<span class="note">These stopped when the converter failed. Switching them off is not an option.</span></dd></div>` : ""}
      <div><dt>Keep on</dt><dd>${tagList(a.keep)}</dd></div>
      <div><dt>How sure</dt><dd>${sure}${a.confidence === "high" ? "" : ". " + esc(other.map((f) => FLAG_TEXT[f] || f).join(" "))}</dd></div>
    </dl>
    ${a.confidence === "high" && other.length ? `<div class="alert">${esc(other.map((f) => FLAG_TEXT[f] || f).join(" "))}</div>` : ""}
    ${res.leak && res.leak.line ? `<div class="alert">${esc(res.leak.line)}</div>` : ""}
    ${diag}
    <p class="note">Faults applied: ${esc(res.scenario.faults.map((f) => (FAULT_TEXT[f] || [f])[0]).join(" and ") || "none")}.
      Assumed values used: ${esc(a.assumptions_used.join(", "))}. Core ${esc(res.core_version)}.</p>`;
}

function renderOutcomes(res) {
  const o = res.runs;
  const cell = (p) => {
    const r = o[p];
    const hit = r.limit_hit ? `${LIMIT_HIT_TEXT[r.limit_hit] || r.limit_hit} after ${Math.round(r.t_limit_s / 60)} min` : "";
    const arrived = r.reached_station && r.outcome !== "UNSAFE" ? "Reached the station" : "";
    const detail = [hit, arrived].filter(Boolean).map((x) => `<span class="note">${esc(x)}</span>`).join("");
    return `<td class="o-${esc(r.outcome)}"><strong>${esc(OUTCOME_TEXT[r.outcome] || r.outcome)}</strong>${detail}</td>`;
  };
  $("run-outcomes").innerHTML = `<table class="compare"><caption>What happened in the simulation</caption>
    <thead><tr><th></th><th>Without the advisor</th><th>With the advisor</th></tr></thead>
    <tbody><tr><th scope="row">Result</th>${cell("baseline")}${cell("advisor")}</tr></tbody></table>`;
}

function fitCanvas(cv) {
  const dpr = window.devicePixelRatio || 1;
  const w = cv.clientWidth || 900, h = cv.clientHeight || 220;
  cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
  const ctx = cv.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, W: w, H: h };
}
function drawSeries(cv, t, series, limit, unit) {
  const { ctx, W, H } = fitCanvas(cv);
  const L = 46, R = 12, T = 12, B = 26;
  ctx.clearRect(0, 0, W, H);
  const ys = series.flatMap((s) => s.y || []).filter((v) => Number.isFinite(v));
  if (limit != null) ys.push(limit);
  if (!ys.length) return;
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi - lo < 1e-6) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const tmax = t[t.length - 1] || 1;
  const X = (v) => L + (v / tmax) * (W - L - R);
  const Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  ctx.font = `12px ${cssVar("--font-outlier")}`;
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = lo + (hi - lo) * i / 4;
    ctx.strokeStyle = cssVar("--color-rule"); ctx.beginPath(); ctx.moveTo(L, Y(v)); ctx.lineTo(W - R, Y(v)); ctx.stroke();
    ctx.fillStyle = cssVar("--color-muted"); ctx.fillText(v.toFixed(v < 20 ? 1 : 0), 2, Y(v) + 4);
  }
  for (let m = 0; m <= tmax / 60; m += 5) {
    ctx.fillStyle = cssVar("--color-muted"); ctx.fillText(m + " min", Math.min(W - R - 40, Math.max(0, X(m * 60) - 12)), H - 8);
  }
  const faultT = 60; // the harness injects the fault at 60 s
  if (faultT < tmax) {
    ctx.strokeStyle = cssVar("--color-muted"); ctx.setLineDash([2, 3]);
    ctx.beginPath(); ctx.moveTo(X(faultT), T); ctx.lineTo(X(faultT), H - B); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = cssVar("--color-muted"); ctx.fillText("fault", X(faultT) + 4, T + 12);
  }
  if (limit != null) {
    ctx.strokeStyle = cssVar("--chart-limit"); ctx.lineWidth = 1.5; ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(L, Y(limit)); ctx.lineTo(W - R, Y(limit)); ctx.stroke(); ctx.setLineDash([]);
  }
  series.forEach((s) => {
    if (!s.y) return;
    ctx.strokeStyle = cssVar(s.c); ctx.lineWidth = s.dash ? 1 : 2.4; ctx.globalAlpha = s.dash ? 0.7 : 1;
    ctx.setLineDash(s.dash ? [3, 3] : []);
    ctx.beginPath();
    s.y.forEach((v, i) => { const x = X(t[i]), y = Y(v); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
  });
}

$("btn-run").addEventListener("click", () => runAdvisor(false));
$("btn-diagnose").addEventListener("click", () => runAdvisor(true));
$("btn-stick").addEventListener("click", () => {
  setStick(!stickTemp);
  runAdvisor(lastCase ? lastCase.diagnose : false);
});
$("btn-hard").addEventListener("click", () => {
  setFaults(["U1_TRIP", "STANDBY_STUCK"]);
  setCondition({ ambient_c: 45, gradient_pct: 2.7, train_load: "loaded" });
  $("dist").value = 15; $("v-dist").textContent = 15;
  runAdvisor(false);
});

// ---------- coverage map ----------
let coverageData = null;
async function loadCoverage() {
  try {
    coverageData = await api("/api/coverage");
  } catch (err) { showError($("coverage-head"), "The coverage data did not load."); return; }
  const s = coverageData.summary || {};
  const n = s.runs_per_policy;
  const stat = (num, of, label) => `<div class="stat"><span class="num">${num}${of ? ` <small>of ${of}</small>` : ""}</span><span class="label">${label}</span></div>`;
  $("coverage-head").innerHTML =
    `${coverageData.stub ? '<p class="warn">Stand-in coverage: fake outcomes until the harness runs.</p>' : ""}
     <div class="stats">
       ${stat(s.baseline_unsafe, n, "tests unsafe without the advisor")}
       ${stat(s.advisor_unsafe, n, "tests unsafe with the advisor")}
       ${s.false_stops != null ? stat(s.false_stops, n, "stops that were not needed") : ""}
       ${stat(s.properties_failed, "", "safety checks failed")}
     </div>
     <p class="note">Source ${esc(coverageData._source_file)}. Core ${esc(coverageData.core_version)}. Generated ${esc(coverageData.generated_utc)}. Seed ${esc(coverageData.seed)}.
       These results come from our simulation with assumed loco numbers.</p>`;
  ["baseline", "advisor"].forEach((p) => { $("grid-" + p).innerHTML = gridHtml(coverageData, p); });
  document.querySelectorAll("td.cell").forEach((td) => td.addEventListener("click", () => openCase(td.dataset.case)));
}
function gridHtml(cov, policy) {
  const conds = cov.conditions.map((c) => c.id);
  const byKey = {};
  cov.cases.forEach((c) => { byKey[c.faults.join("+") + "|" + c.condition] = c; });
  const combos = [];
  cov.cases.forEach((c) => { const k = c.faults.join("+"); if (!combos.includes(k)) combos.push(k); });
  const letter = { SAFE: "S", CONTROLLED_STOP: "C", UNSAFE: "U" };
  let h = `<table class="grid"><thead><tr><th></th>${conds.map((c) => `<th>${esc(COND_TEXT[c] || c)}</th>`).join("")}</tr></thead><tbody>`;
  combos.forEach((k) => {
    const label = k.split("+").map((f) => FAULT_SHORT[f] || f).join(" + ");
    h += `<tr><th scope="row">${esc(label)}</th>`;
    conds.forEach((cid) => {
      const c = byKey[k + "|" + cid];
      const o = c ? c[policy].outcome : "";
      h += `<td class="cell ${o}" data-case="${esc(c ? c.case_id : "")}" title="${esc(label + ", " + (COND_TEXT[cid] || cid) + ": " + (OUTCOME_TEXT[o] || o))}">${letter[o] || ""}</td>`;
    });
    h += "</tr>";
  });
  return h + "</tbody></table>";
}
function openCase(caseId) {
  const c = coverageData.cases.find((x) => x.case_id === caseId);
  if (!c) return;
  const cond = coverageData.conditions.find((x) => x.id === c.condition);
  setFaults(c.faults.filter((f) => f !== "TEMP_SENSOR_STUCK"));
  setStick(c.faults.includes("TEMP_SENSOR_STUCK"));
  setCondition(cond);
  showTab("advisor");
  runAdvisor(false);
}

// ---------- real data ----------
async function loadRealData() {
  let r, cfg;
  try { r = await api("/api/anomaly-demo"); cfg = await api("/api/config"); }
  catch (err) { showError($("realdata-body"), "The real-data results did not load."); return; }
  let h = "";
  if (r.air_fit) {
    const l = r.air_fit.leak_bar_per_min;
    const air = (cfg.assumptions || []).find((a) => a.key === "air");
    const mine = air && air.value && air.value.leak_bar_per_min;
    h += `<div class="block"><h3>How fast does brake air leak away?</h3>
      <p>From ${esc(r.air_fit.n_segments)} stretches where the compressor was off, the pressure fell by about
      <span class="num">${l.nominal.toFixed(3)}</span> bar per minute (range ${l.min.toFixed(3)} to ${l.max.toFixed(3)}).</p>
      ${mine ? `<p>The leak range in our loco model is ${mine.min} to ${mine.max} bar per minute, taken from public dispatch test sheets. The two sources are the same size, which is a useful sanity check.</p>` : ""}
      <p class="note">Status: ${esc(r.air_fit.status)}. A proxy fit, not a loco measurement.</p></div>`;
  }
  if (r.metrics) {
    const m = r.metrics;
    h += `<div class="block"><h3>Can a model spot an air leak early?</h3>
      <p>We trained an anomaly detector (Isolation Forest) on February and fixed its alarm threshold on March. We then tested it on the months from ${esc(m.test_from)}, which it had never seen. With the threshold fixed in advance (${esc(m.false_alarm_budget)}), it caught
      <b class="num">${esc(m.events_detected)}</b> of the 4 labelled air leaks, with ${esc(m.false_alarm_episodes_per_day)} false alarms per day.</p>
      <p>Looser alarm settings catch more leaks and raise more false alarms. All settings were fixed before testing, and all are shown.</p>
      <div class="table-wrap"><table class="data"><thead><tr><th>Alarm setting</th><th class="num">Leaks caught (of 4)</th><th class="num">False alarms per day</th><th class="num">Alarms that were real</th></tr></thead><tbody>
      ${m.budget_table.map((b) => `<tr><td class="num">${b.val_quantile}</td><td class="num">${b.events_detected}</td><td class="num">${b.false_alarm_episodes_per_day}</td><td class="num">${b.alarm_bin_precision ?? "none"}</td></tr>`).join("")}
      </tbody></table></div></div>`;
  }
  if (!r.available && !r.air_fit) h += '<p class="note">Real-data results are not built yet.</p>';
  $("realdata-body").innerHTML = h;
  if (r.demo) drawAnomaly(r.demo);
}
function drawAnomaly(d) {
  const cv = $("chart-anomaly");
  const { ctx, W, H } = fitCanvas(cv);
  const L = 12, R = 12, T = 12, B = 22;
  ctx.clearRect(0, 0, W, H);
  const n = d.score.length; if (!n) return;
  const hi = Math.max(...d.score, d.threshold) * 1.05, lo = Math.min(...d.score, 0);
  const X = (i) => L + (i / (n - 1)) * (W - L - R);
  const Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  ctx.fillStyle = cssVar("--cell-unsafe"); ctx.globalAlpha = 0.25;
  (d.failure_idx || []).forEach(([a, b]) => ctx.fillRect(X(a), T, Math.max(2, X(b) - X(a)), H - T - B));
  ctx.globalAlpha = 1;
  ctx.strokeStyle = cssVar("--chart-limit"); ctx.lineWidth = 1.5; ctx.setLineDash([6, 4]);
  ctx.beginPath(); ctx.moveTo(L, Y(d.threshold)); ctx.lineTo(W - R, Y(d.threshold)); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = cssVar("--color-accent"); ctx.lineWidth = 1.4; ctx.beginPath();
  d.score.forEach((v, i) => { i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)); });
  ctx.stroke();
  ctx.fillStyle = cssVar("--color-muted"); ctx.font = `12px ${cssVar("--font-outlier")}`;
  ctx.fillText(d.label || "anomaly score over time", L, H - 6);
}

// ---------- assumptions ----------
function fmtValue(v) {
  if (v && typeof v === "object" && "nominal" in v && "min" in v && "max" in v)
    return `<span>${v.min} to ${v.max}, typical ${v.nominal}</span>`;
  if (v && typeof v === "object") {
    return Object.entries(v).map(([k, x]) =>
      `<span>${esc(k)}: ${typeof x === "object" && x !== null ? ("nominal" in x ? `${x.min} to ${x.max}, typical ${x.nominal}` : esc(JSON.stringify(x))) : esc(x)}</span>`).join("");
  }
  return `<span>${esc(v)}</span>`;
}
async function loadAssumptions() {
  let r;
  try { r = await api("/api/config"); } catch (err) { showError($("assumption-count"), "The assumptions did not load."); return; }
  const rows = r.assumptions;
  const assumed = rows.filter((a) => a.status === "assumed").length;
  $("assumption-count").textContent = `${assumed} of ${rows.length} values are assumed. ${rows.length - assumed} are confirmed by a source. A value changes to confirmed only when a named source or person backs it.`;
  $("assumptions-table").querySelector("tbody").innerHTML = rows.map((a) =>
    `<tr><td>${esc(a.key.replace(/\./g, " / ").replace(/_/g, " "))}</td><td><div class="value-lines">${fmtValue(a.value)}</div></td>
     <td><span class="status ${esc(a.status)}">${esc(a.status)}</span></td><td>${esc(a.source)}</td></tr>`).join("");
}

// ---------- report ----------
async function loadReport() {
  try {
    const r = await fetch("/api/report");
    $("report-status").innerHTML = r.ok ? '<p class="note">The report is ready.</p>'
      : `<p class="warn">${esc((await r.json()).reason)}</p>`;
    const m = await api("/api/metrics");
    $("metrics-box").textContent = m.metrics ? JSON.stringify(m.metrics, null, 2) : "Classifier not trained yet.";
    $("metrics-table").innerHTML = m.metrics ? metricsHtml(m.metrics) : '<p class="note">The classifier is not trained yet.</p>';
  } catch (err) { showError($("report-status"), "The report status did not load."); }
}
function pct(x) { return (x * 100).toFixed(0) + "%"; }
function metricsHtml(m) {
  const row = (label, o) => o ? `<tr><td>${esc(label)}</td><td class="num">${esc(o.n_windows)}</td><td class="num">${pct(o.exact_set_accuracy)}</td><td class="num">${pct(o.micro_recall)}</td><td class="num">${pct(o.micro_precision)}</td></tr>` : "";
  return `<p>The classifier reads a short window of sensor readings and says which faults are present. All figures are on data it was not trained on. It was trained and tested on simulated data only.</p>
    <div class="table-wrap"><table class="data"><thead><tr><th>Test</th><th class="num">Windows</th><th class="num">Whole fault set right</th><th class="num">Faults found</th><th class="num">Calls that were right</th></tr></thead><tbody>
    ${row("Unseen scenarios", m.test_seed_split)}${row("Fault pairs it never saw in training", m.heldout_pairs_eval)}
    ${row("Noise 0.05", (m.by_noise || {}).noise_0_05 || (m.by_noise || {})["noise_0.05"])}${row("Noise 0.10", (m.by_noise || {})["noise_0.1"])}
    ${row("Loco values outside the training range", m.params_outside_training_range)}</tbody></table></div>
    <p class="note">${esc(m.limits || "")}</p>`;
}

// ---------- init ----------
(async function init() {
  buildFaultPicks();
  setStick(false);
  try {
    const s = await api("/api/status");
    const b = $("core-badge");
    b.textContent = s.stub ? "stand-in core " + s.core_version : "simulation core " + s.core_version;
    b.className = "badge " + (s.stub ? "stub" : "real");
  } catch (err) { $("core-badge").textContent = "server not answering"; }
  showTab(location.hash.slice(1) || "advisor");
})();
