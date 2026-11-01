// Failover Guardian front end. Plain JS and canvas, no external libraries.
"use strict";

const FAULTS = ["U1_TRIP", "U2_TRIP", "STANDBY_STUCK", "MCB_TRIP", "UNIT_DERATE",
  "BLOWER_FAIL", "COMPRESSOR_FAIL", "TEMP_SENSOR_STUCK"];
const COLORS = { base: "#d23c3c", adv: "#1f6fd1", obs: "#8a8f98", lim: "#000000" };
const $ = (id) => document.getElementById(id);
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

// ---------- tabs ----------
document.querySelectorAll("nav button").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.tab)));
function showTab(name) {
  document.querySelectorAll("nav button").forEach((b) => b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === "tab-" + name));
  if (name === "coverage") loadCoverage();
  if (name === "realdata") loadRealData();
  if (name === "assumptions") loadAssumptions();
  if (name === "report") loadReport();
}

// ---------- advisor ----------
function buildFaultPicks() {
  $("fault-picks").innerHTML = FAULTS.map((f) =>
    `<label><input type="checkbox" value="${f}"> ${f}</label>`).join("");
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

async function runAdvisor(diagnose = false) {
  const req = {
    faults: selectedFaults(), ambient_c: +$("ambient").value, gradient_pct: +$("gradient").value,
    train_load: $("train_load").value, units: +$("units").value, dist_next_station_km: +$("dist").value,
    speed_kmph: 40, stick_temp: stickTemp, diagnose: diagnose, seed: 1, noise: 0.02,
  };
  lastCase = req;
  $("decision-card").innerHTML = "Running...";
  const res = await api("/api/advise", req);
  renderAdvice(res);
  drawSeries($("chart-temp"), res.chart.t_s, [
    { y: res.chart.motor_temp_baseline, c: COLORS.base },
    { y: res.chart.motor_temp_advisor, c: COLORS.adv },
    { y: res.chart.motor_temp_observed, c: COLORS.obs, dash: true },
  ], res.chart.motor_temp_limit_c);
  drawSeries($("chart-air"), res.chart.t_s, [
    { y: res.chart.air_baseline, c: COLORS.base },
    { y: res.chart.air_advisor, c: COLORS.adv },
  ], res.chart.air_min_bar);
  const o = res.runs;
  $("run-outcomes").innerHTML = ["baseline", "advisor"].map((p) =>
    `<div class="line"><b>${p}</b> ${esc(o[p].outcome)}${o[p].limit_hit ? " (" + esc(o[p].limit_hit) +
      " at " + Math.round(o[p].t_limit_s / 60) + " min)" : ""}${o[p].reached_station ? ", reached station" : ""}</div>`
  ).join("") + `<div class="small">Core ${esc(res.core_version)}${res.stub ? " (STUB, fake numbers)" : ""}</div>`;
}

function renderAdvice(res) {
  const a = res.advice;
  const d = res.diagnosis;
  let diag = "";
  if (d) {
    if (!d.available) diag = `<p class="small">Auto-diagnose: ${esc(d.reason || "unavailable")}. Advisor used its own rules.</p>`;
    else {
      const top = Object.entries(d.faults).sort((x, y) => y[1] - x[1]).slice(0, 4)
        .map(([f, p]) => `${esc(f)} ${(p * 100).toFixed(0)}%`).join(", ");
      diag = `<p><b>Diagnosis:</b> ${esc(d.predicted.join(" + ") || "no fault")} (confidence ${(d.confidence * 100).toFixed(0)}%)` +
        `${d.used_by_advisor ? "" : " Not used: advisor inferred the faults from signals (cautious path)"}<br><span class="small">${top}</span></p>`;
    }
  }
  $("decision-card").innerHTML = `
    ${res.stub ? '<p class="warn">STUB core: these numbers are fake.</p>' : ""}
    <div class="decision ${esc(a.decision)}">${esc(a.decision.replace(/_/g, " "))}</div>
    <div class="line"><b>Switch off</b> ${esc(a.shed.join(", ") || "nothing")}</div>
    <div class="line"><b>Keep on</b> ${esc(a.keep.join(", "))}</div>
    <div class="line"><b>Minutes left</b> <span class="minutes">at least ${a.minutes_left_p5.toFixed(1)}</span></div>
    <div class="small">5th percentile. Nominal ${a.minutes_left_nominal.toFixed(1)} min. Limiting factor: <b>${esc(a.limiting_factor)}</b>. Confidence: ${esc(a.confidence)}.</div>
    <p>${esc(a.reason)}</p>
    <div class="flags">${a.flags.map((f) => `<span>${esc(f)}</span>`).join("")}</div>
    ${diag}
    <p class="small">Faults injected: ${esc(res.scenario.faults.join(" + ") || "none")}. Assumed values used: ${esc(a.assumptions_used.join(", "))}</p>`;
}

function drawSeries(cv, t, series, limit) {
  const ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height, L = 44, R = 10, T = 10, B = 24;
  ctx.clearRect(0, 0, W, H);
  let ys = series.flatMap((s) => s.y || []).filter((v) => Number.isFinite(v));
  if (limit != null) ys.push(limit);
  if (!ys.length) return;
  let lo = Math.min(...ys), hi = Math.max(...ys);
  if (hi - lo < 1e-6) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
  const tmax = t[t.length - 1] || 1;
  const X = (v) => L + (v / tmax) * (W - L - R);
  const Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  ctx.strokeStyle = "#ccc"; ctx.fillStyle = "#555"; ctx.font = "11px sans-serif"; ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const v = lo + (hi - lo) * i / 4;
    ctx.beginPath(); ctx.moveTo(L, Y(v)); ctx.lineTo(W - R, Y(v)); ctx.stroke();
    ctx.fillText(v.toFixed(1), 2, Y(v) + 4);
  }
  for (let m = 0; m <= tmax / 60; m += 5) ctx.fillText(m + " min", X(m * 60) - 10, H - 6);
  if (limit != null) {
    ctx.strokeStyle = COLORS.lim; ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(L, Y(limit)); ctx.lineTo(W - R, Y(limit)); ctx.stroke(); ctx.setLineDash([]);
  }
  series.forEach((s) => {
    if (!s.y) return;
    ctx.strokeStyle = s.c; ctx.lineWidth = 2; ctx.setLineDash(s.dash ? [3, 3] : []);
    ctx.beginPath();
    s.y.forEach((v, i) => { const x = X(t[i]), y = Y(v); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); });
    ctx.stroke(); ctx.setLineDash([]);
  });
}

$("btn-run").addEventListener("click", () => runAdvisor(false));
$("btn-diagnose").addEventListener("click", () => runAdvisor(true));
$("btn-stick").addEventListener("click", () => {
  stickTemp = !stickTemp;
  $("btn-stick").textContent = stickTemp ? "Unstick the temperature sensor" : "Stick the temperature sensor";
  runAdvisor(lastCase ? lastCase.diagnose : false);
});
$("btn-hard").addEventListener("click", () => {
  setFaults(["U1_TRIP", "STANDBY_STUCK"]);
  setCondition({ ambient_c: 45, gradient_pct: 2.7, train_load: "loaded" });
  $("dist").value = 15; $("v-dist").textContent = 15;
  runAdvisor(false);
});

// ---------- coverage ----------
let coverageData = null;
async function loadCoverage() {
  coverageData = await api("/api/coverage");
  const s = coverageData.summary || {};
  $("coverage-head").innerHTML =
    `${coverageData.stub ? '<p class="warn">STUB coverage: fake outcomes until the harness runs.</p>' : ""}
     <div class="headline">Unsafe runs: baseline <b>${s.baseline_unsafe}</b> of ${s.runs_per_policy},
       with advisor <b>${s.advisor_unsafe}</b> of ${s.runs_per_policy}. Property checks failed: ${s.properties_failed}.</div>
     <div class="small">Source: ${esc(coverageData._source_file)}. Core ${esc(coverageData.core_version)}. Generated ${esc(coverageData.generated_utc)}. Seed ${esc(coverageData.seed)}.</div>`;
  ["baseline", "advisor"].forEach((p) => { $("grid-" + p).innerHTML = gridHtml(coverageData, p); });
  document.querySelectorAll("td.cell").forEach((td) => td.addEventListener("click", () => openCase(td.dataset.case)));
}
function gridHtml(cov, policy) {
  const conds = cov.conditions.map((c) => c.id);
  const byKey = {};
  cov.cases.forEach((c) => { byKey[c.faults.join("+") + "|" + c.condition] = c; });
  const combos = [];
  cov.cases.forEach((c) => { const k = c.faults.join("+"); if (!combos.includes(k)) combos.push(k); });
  let h = `<table class="grid"><tr><th></th>${conds.map((c) => `<th>${esc(c.replace("_", " "))}</th>`).join("")}</tr>`;
  combos.forEach((k) => {
    h += `<tr><th>${esc(k)}</th>`;
    conds.forEach((cid) => {
      const c = byKey[k + "|" + cid];
      const o = c ? c[policy].outcome : "";
      h += `<td class="cell ${o}" data-case="${esc(c ? c.case_id : "")}" title="${esc(k + " / " + cid + ": " + o)}"></td>`;
    });
    h += "</tr>";
  });
  return h + "</table>";
}
function openCase(caseId) {
  const c = coverageData.cases.find((x) => x.case_id === caseId);
  if (!c) return;
  const cond = coverageData.conditions.find((x) => x.id === c.condition);
  setFaults(c.faults.filter((f) => f !== "TEMP_SENSOR_STUCK"));
  stickTemp = c.faults.includes("TEMP_SENSOR_STUCK");
  $("btn-stick").textContent = stickTemp ? "Unstick the temperature sensor" : "Stick the temperature sensor";
  setCondition(cond);
  showTab("advisor");
  runAdvisor(false);
}

// ---------- real data ----------
async function loadRealData() {
  const r = await api("/api/anomaly-demo");
  let h = "";
  if (r.air_fit) {
    const l = r.air_fit.leak_bar_per_min;
    h += `<h3>Brake-air leak fit (compressor-off segments)</h3><p>Pressure decay ${l.nominal.toFixed(4)} bar/min
      (range ${l.min.toFixed(4)} to ${l.max.toFixed(4)}), from ${r.air_fit.n_segments} segments. Status: ${esc(r.air_fit.status)}.</p>`;
  }
  if (r.metrics) {
    const m = r.metrics;
    h += `<h3>Anomaly detector (Isolation Forest), tested on held-out months ${esc(m.test_from)} onwards</h3>
      <p>Trained on February, alarm threshold fixed on March. With the threshold set in advance
      (${esc(m.false_alarm_budget)}): <b>${esc(m.events_detected)}</b> labelled air leaks caught,
      ${esc(m.false_alarm_episodes_per_day)} false alarms per day.
      Median score inside leaks ${esc(m.score_median_inside_failures)} vs ${esc(m.score_median_outside_warning_windows)} in normal running.</p>
      <table id="budget-table"><tr><th>Budget (March quantile)</th><th>Leaks caught (of 4)</th><th>False alarms per day</th><th>Alarm precision</th></tr>
      ${m.budget_table.map((b) => `<tr><td>${b.val_quantile}</td><td>${b.events_detected}</td><td>${b.false_alarm_episodes_per_day}</td><td>${b.alarm_bin_precision ?? "-"}</td></tr>`).join("")}
      </table><p class="small">All budgets were fixed before testing and are all shown. None was chosen on the test months.</p>`;
  }
  if (!r.available && !r.air_fit) h += "<p>Real-data results are not built yet.</p>";
  $("realdata-body").innerHTML = h;
  if (r.demo) drawAnomaly(r.demo);
}
function drawAnomaly(d) {
  const cv = $("chart-anomaly"), ctx = cv.getContext("2d");
  const W = cv.width, H = cv.height, L = 44, R = 10, T = 10, B = 24;
  ctx.clearRect(0, 0, W, H);
  const n = d.score.length; if (!n) return;
  const hi = Math.max(...d.score, d.threshold) * 1.05, lo = Math.min(...d.score, 0);
  const X = (i) => L + (i / (n - 1)) * (W - L - R);
  const Y = (v) => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  ctx.fillStyle = "rgba(210,60,60,0.18)";
  (d.failure_idx || []).forEach(([a, b]) => ctx.fillRect(X(a), T, Math.max(2, X(b) - X(a)), H - T - B));
  ctx.strokeStyle = "#000"; ctx.setLineDash([6, 4]);
  ctx.beginPath(); ctx.moveTo(L, Y(d.threshold)); ctx.lineTo(W - R, Y(d.threshold)); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = COLORS.adv; ctx.lineWidth = 1.5; ctx.beginPath();
  d.score.forEach((v, i) => { i ? ctx.lineTo(X(i), Y(v)) : ctx.moveTo(X(i), Y(v)); });
  ctx.stroke();
  ctx.fillStyle = "#555"; ctx.font = "11px sans-serif";
  ctx.fillText(d.label || "anomaly score (shaded: labelled air-leak failures, dashed: alarm threshold)", L, H - 6);
}

// ---------- assumptions ----------
async function loadAssumptions() {
  const r = await api("/api/config");
  $("assumptions-table").querySelector("tbody").innerHTML = r.assumptions.map((a) =>
    `<tr><td>${esc(a.key)}</td><td><code>${esc(typeof a.value === "object" ? JSON.stringify(a.value) : a.value)}</code></td>
     <td><span class="badge ${esc(a.status)}">${esc(a.status)}</span></td><td>${esc(a.source)}</td></tr>`).join("");
}

// ---------- report ----------
async function loadReport() {
  const r = await fetch("/api/report");
  $("report-status").innerHTML = r.ok ? '<p class="small">Report available.</p>'
    : `<p class="warn">${esc((await r.json()).reason)}</p>`;
  const m = await api("/api/metrics");
  $("metrics-box").textContent = m.metrics ? JSON.stringify(m.metrics, null, 2) : "Classifier not trained yet.";
}

// ---------- init ----------
(async function init() {
  buildFaultPicks();
  const s = await api("/api/status");
  const b = $("core-badge");
  b.textContent = s.stub ? "STUB core " + s.core_version : "core " + s.core_version;
  b.className = "badge " + (s.stub ? "stub" : "real");
})();
