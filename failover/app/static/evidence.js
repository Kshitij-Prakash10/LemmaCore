// Model evidence page. Plain JS and canvas, no external libraries.
"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

function draw(r, i) {
  const cv = $("chart"), c = cv.getContext("2d"), W = cv.width, H = cv.height, L = 10, T = 10, B = 10;
  const n = r.t.length, X = (k) => L + (k / (n - 1)) * (W - 2 * L), Y = (v) => T + (1 - v) * (H - T - B);
  c.clearRect(0, 0, W, H);
  c.fillStyle = "rgba(210,60,60,0.18)";
  r.in_event.forEach((e, k) => { if (e && k <= i) c.fillRect(X(k), T, Math.max(1, W / n), H - T - B); });
  c.strokeStyle = "#000"; c.setLineDash([6, 4]);
  c.beginPath(); c.moveTo(L, Y(r.theta)); c.lineTo(W - L, Y(r.theta)); c.stroke(); c.setLineDash([]);
  const line = (ys, col) => {
    c.strokeStyle = col; c.lineWidth = 1.5; c.beginPath();
    for (let k = 0; k <= i; k++) { k ? c.lineTo(X(k), Y(ys[k])) : c.moveTo(X(k), Y(ys[k])); }
    c.stroke();
  };
  line(r.reservoirs_bar.map((v) => Math.min(1, v / 12)), "#8a8f98");
  line(r.p, "#1f6fd1");
}

async function fireAdvisor(i) {
  const res = await (await fetch("/api/advise", { method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ faults: ["COMPRESSOR_FAIL"], leak_replay_i: i }) })).json();
  if (!res.leak || !res.leak.line) return;
  $("card").hidden = false;
  $("card").textContent = res.leak.line + `. Advisor: ${res.advice.decision.replace(/_/g, " ")}, at least ${res.advice.minutes_left_p5.toFixed(1)} min (example fault: compressor stopped).`;
  $("why").innerHTML = res.leak.explain.map((e) => `<li>${esc(e.feature)} = ${e.value} (${e.z} standard deviations from normal)</li>`).join("");
}

(async function init() {
  const d = await (await fetch("/api/evidence")).json();
  if (d.metrics) {
    const rows = d.metrics.cv_table;
    $("cv").innerHTML = "<tr><th>Model</th><th>Threshold</th><th>Held-out event</th><th>Detected</th><th>Minutes to first alert</th><th>Share of event in alert</th><th>False alarms per day</th></tr>" +
      rows.map((r) => `<tr><td>${esc(r.model)}</td><td>${r.theta}</td><td>${esc(r.held_out_event)}</td><td>${r.detected ? "yes" : "no"}</td><td>${r.minutes_to_first_alert ?? "-"}</td><td>${r.alert_share_of_event == null ? "-" : Math.round(r.alert_share_of_event * 100) + "%"}</td><td>${r.false_alarms_per_day}</td></tr>`).join("");
    $("cv-note").textContent = `Chosen: ${d.metrics.winner}. ${d.metrics.theta_note}. ${d.metrics.false_alarm_note}`;
  } else {
    $("cv").innerHTML = "<tr><td>Model not trained. Run make train.</td></tr>";
  }
  $("external").textContent = !d.external ? "Not run." : d.external.available
    ? `Air leak detected: ${d.external.air_leak_detected ? "yes" : "no"}, first alert at ${d.external.air_leak_minutes_to_first_alert ?? "-"} min. Oil leak alert fraction ${d.external.oil_leak_alert_fraction}. False alarms per day ${d.external.false_alarms_per_day}.`
    : d.external.reason;
  const r = d.replay;
  if (!r) { $("replay").disabled = true; $("status").textContent = "Replay not built."; return; }
  $("replay").addEventListener("click", () => {
    let i = 0, fired = false;
    $("card").hidden = true; $("why").innerHTML = "";
    const timer = setInterval(() => {
      i = Math.min(r.t.length - 1, i + 3);
      draw(r, i);
      $("status").textContent = `${r.t[i]}  score ${r.p[i].toFixed(3)}  ${!r.valid[i] ? "data invalid" : r.alarm[i] ? "ALERT" : "no alert"}`;
      if (r.alarm[i] && !fired) { fired = true; fireAdvisor(i); }
      if (i >= r.t.length - 1) clearInterval(timer);
    }, 40);
  });
})();
