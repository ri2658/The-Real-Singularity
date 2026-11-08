/*
 * Checks for the Allen-Cahn JS simulator. Run from anywhere:
 *     node allen_cahn/js/check_ac.js
 *
 * Checks 1-5 need nothing else: they compare against the notes' Table 1 / Table 2.
 * Checks 6-7 run once Michelle's data/allen_cahn/*.json files are on disk.
 *
 *   1. Energy never increases (random starts), and they end at +hump or -hump.
 *   2. A sin(2x) start stays antisymmetric and settles on the S state.
 *   3. Near the hump, perturbations decay at rate ~8.687 (Table 2: ~6,000x per time unit).
 *   4. Near the S state, a tiny symmetric push grows at rate ~1.529 and the curve
 *      leaves for the hump (S is a hilltop).
 *   5. dt = 0.95 * h^2/2 is stable, dt = 1.05 * h^2/2 blows up (learning-rate limit).
 *   6. Starting exactly on each of Michelle's five equilibria, U barely moves.
 *   7. Michelle's PINN guesses: the hump guess heals into the hump; the S guess
 *      approaches S, then falls off (preview of the week-6 correction demo).
 */
const fs = require("fs");
const path = require("path");
const AC = require("./allen_cahn.js");

// Table 1 of the notes (mu = 6, N = 128).
const TABLE1 = {
  hump: { energy: -2.4036, maxAbs: 0.9825, lambda1: -8.687 },
  S: { energy: -0.3541, maxAbs: 0.6601, lambda1: 1.529 },
};

let failures = 0;
function report(label, ok, detail) {
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${label}${detail ? "   " + detail : ""}`);
}
const close = (a, b, tol) => Math.abs(a - b) <= tol;

// Least-squares slope of log(y) against t.
function logSlope(ts, ys) {
  const n = ts.length;
  const ls = ys.map(Math.log);
  const tm = ts.reduce((s, v) => s + v, 0) / n;
  const lm = ls.reduce((s, v) => s + v, 0) / n;
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) {
    num += (ts[i] - tm) * (ls[i] - lm);
    den += (ts[i] - tm) ** 2;
  }
  return num / den;
}

const { x, h } = AC.makeGrid();
const mu = AC.AC_DEFAULTS.mu;

// ---------------- Check 1: energy decreases, random start -> +-hump ----------------
console.log("Check 1: random starts (t = 0 -> 10), energy checked after every step");
let hump = null;
for (let seed = 0; seed < 5; seed++) {
  const sim = AC.createSimulator();
  sim.set(AC.initialCurve("random", x, { amp: 0.5, seed }));
  let E = sim.energy(), worstRise = 0;
  const total = Math.round(10 / sim.dt);
  for (let k = 0; k < total; k++) {
    sim.advance(1);
    const En = sim.energy();
    worstRise = Math.max(worstRise, En - E);
    E = En;
  }
  const sign = Math.sign(sim.U[Math.floor(x.length / 2)]);
  if (sign > 0 && !hump) hump = Float64Array.from(sim.U);
  const ok = worstRise <= 1e-12 && close(E, TABLE1.hump.energy, 5e-5)
    && close(AC.maxAbs(sim.U), TABLE1.hump.maxAbs, 5e-5);
  report(`seed ${seed}: ends at ${sign > 0 ? "+" : "-"}hump`, ok,
    `E = ${E.toFixed(4)} (Table 1: ${TABLE1.hump.energy}), max|U| = ${AC.maxAbs(sim.U).toFixed(4)}, ` +
    `largest energy rise = ${worstRise.toExponential(1)}, residual = ${sim.residual().toExponential(1)}`);
}
if (!hump) hump = AC.simulate(AC.initialCurve("hump-like", x), [10]).snaps[0];

// ---------------- Check 2: sin(2x) start -> S state ----------------
console.log("\nCheck 2: start 0.5 sin(2x), run to t = 8");
const sRun = AC.simulate(AC.initialCurve("S-like", x, { amp: 0.5 }), [8]);
const S = sRun.snaps[0];
let asym = 0;
for (let i = 0; i < x.length; i++) asym = Math.max(asym, Math.abs(S[i] + S[x.length - 1 - i]));
report("settles on the S state", close(sRun.energies[0], TABLE1.S.energy, 5e-5)
  && close(AC.maxAbs(S), TABLE1.S.maxAbs, 5e-5),
  `E = ${sRun.energies[0].toFixed(4)} (Table 1: ${TABLE1.S.energy}), max|U| = ${AC.maxAbs(S).toFixed(4)}, ` +
  `antisymmetry error = ${asym.toExponential(1)}, residual = ${AC.residual(S, mu, h).toExponential(1)}`);

// ---------------- Check 3: decay rate near the hump ----------------
console.log("\nCheck 3: hump + 1e-3 * sin(x), distance to the hump over t in [0.5, 1.5]");
{
  const sim = AC.createSimulator();
  const U0 = Float64Array.from(hump);
  for (let i = 0; i < x.length; i++) U0[i] += 1e-3 * Math.sin(x[i]);
  sim.set(U0);
  const ts = [], ds = [];
  for (let k = 0; k <= 20; k++) {
    sim.advanceTo(0.5 + 0.05 * k);
    ts.push(sim.t);
    ds.push(AC.maxAbsDiff(sim.U, hump));
  }
  const rate = logSlope(ts, ds);
  report("decays at the hump's top eigenvalue", close(rate, TABLE1.hump.lambda1, 0.02),
    `rate = ${rate.toFixed(3)} (Table 1: ${TABLE1.hump.lambda1}), ` +
    `shrinks ${Math.exp(-rate).toFixed(0)}x per time unit (Table 2: ~6,000x)`);
}

// ---------------- Check 4: escape from the S state ----------------
console.log("\nCheck 4: S + 1e-8 * sin(x), growth rate and where it ends");
{
  const sim = AC.createSimulator();
  const U0 = Float64Array.from(S);
  for (let i = 0; i < x.length; i++) U0[i] += 1e-8 * Math.sin(x[i]);
  sim.set(U0);
  const ts = [], ds = [];
  for (let k = 0; k <= 20; k++) {
    sim.advanceTo(1 + 0.1 * k);
    ts.push(sim.t);
    ds.push(AC.maxAbsDiff(sim.U, S));
  }
  const rate = logSlope(ts, ds);
  report("grows at the S state's unstable eigenvalue", close(rate, TABLE1.S.lambda1, 0.02),
    `rate = ${rate.toFixed(3)} (Table 1: ${TABLE1.S.lambda1})`);
  sim.advanceTo(25);
  report("leaves S and ends at the hump", close(sim.energy(), TABLE1.hump.energy, 5e-5),
    `E(t = 25) = ${sim.energy().toFixed(4)}`);
}

// ---------------- Check 5: learning-rate limit ----------------
console.log("\nCheck 5: dt just below / just above h^2 / 2 (start 0.5 sin(x), 5,000 steps)");
for (const f of [0.95, 1.05]) {
  const sim = AC.createSimulator({ dtFactor: f * 0.5 });
  sim.set(AC.initialCurve("hump-like", x));
  sim.advance(5000);
  const blew = sim.blewUp();
  report(`dt = ${f} * h^2/2 ${f < 1 ? "stays stable" : "blows up"}`, blew === (f > 1),
    `max|U| after 5,000 steps = ${AC.maxAbs(sim.U).toExponential(2)}`);
}

// ---------------- Check 6: Michelle's equilibria.json ----------------
console.log("\nCheck 6: Michelle's equilibria (data/allen_cahn/equilibria.json)");
const eqPath = path.resolve(__dirname, "..", "..", "data", "allen_cahn", "equilibria.json");
if (!fs.existsSync(eqPath)) {
  console.log("  SKIP  file not here yet (pull it from origin/michelleZhao when she pushes)");
} else {
  const eq = JSON.parse(fs.readFileSync(eqPath, "utf8"));
  // Accept both layouts: { hump: [...] } and Michelle's { states: { hump: { U: [...] } } }.
  const stateOf = (name) => (eq.states && eq.states[name] ? eq.states[name].U : eq[name]);
  for (const name of ["zero", "hump", "minus_hump", "S", "minus_S"]) {
    if (!stateOf(name)) { report(`${name}: present in file`, false); continue; }
    const U0 = Float64Array.from(stateOf(name));
    const sim = AC.createSimulator();
    sim.set(U0);
    sim.advanceTo(1);
    const drift = AC.maxAbsDiff(sim.U, U0);
    // Unstable states (S, zero) drift once round-off grows, but only slightly by t = 1.
    report(`${name}: stays put for t = 1`, drift < 1e-8,
      `max drift = ${drift.toExponential(1)}, E = ${AC.energy(U0, mu, h).toFixed(4)}`);
  }
  // The same states should match what the simulator itself converged to (checks 1-2).
  if (stateOf("hump") && stateOf("S")) {
    const dh = AC.maxAbsDiff(Float64Array.from(stateOf("hump")), hump);
    const dS = AC.maxAbsDiff(Float64Array.from(stateOf("S")), S);
    report("Newton states match the simulator's own steady states", dh < 1e-9 && dS < 1e-8,
      `hump diff = ${dh.toExponential(1)}, S diff = ${dS.toExponential(1)}`);
  }
}

// ---------------- Check 7: Michelle's PINN guesses (correction demo preview) ----------------
console.log("\nCheck 7: PINN guesses (data/allen_cahn/pinn_guesses.json) fed into the simulator");
const gPath = path.resolve(__dirname, "..", "..", "data", "allen_cahn", "pinn_guesses.json");
if (!fs.existsSync(gPath)) {
  console.log("  SKIP  file not here yet");
} else {
  const g = JSON.parse(fs.readFileSync(gPath, "utf8"));
  // Hump guess: should heal into the hump (stable state).
  {
    const U0 = Float64Array.from(g.hump_guess);
    const ref = U0[63] > 0 ? hump : hump.map((v) => -v);
    const out = AC.simulate(U0, [1, 3]);
    const d0 = AC.maxAbsDiff(U0, ref), d1 = AC.maxAbsDiff(out.snaps[0], ref), d3 = AC.maxAbsDiff(out.snaps[1], ref);
    report("hump guess heals into the hump", d3 < 1e-8,
      `distance to hump: ${d0.toExponential(1)} (t = 0) -> ${d1.toExponential(1)} (t = 1) -> ${d3.toExponential(1)} (t = 3)`);
  }
  // S guess: first slides toward S (its stable directions decay), then the one
  // unstable direction (rate 1.529) takes over and it falls off the hilltop into a hump.
  {
    const U0 = Float64Array.from(g.S_guess);
    const sim = AC.createSimulator();
    sim.set(U0);
    let closest = AC.maxAbsDiff(U0, S), tClosest = 0;
    const sNeg = S.map((v) => -v);
    for (let k = 1; k <= 400; k++) {
      sim.advanceTo(0.05 * k);
      const d = Math.min(AC.maxAbsDiff(sim.U, S), AC.maxAbsDiff(sim.U, sNeg));
      if (d < closest) { closest = d; tClosest = sim.t; }
    }
    report("S guess falls off the hilltop into a hump", close(sim.energy(), TABLE1.hump.energy, 5e-5),
      `start ${AC.maxAbsDiff(U0, S).toExponential(1)} from S, closest ${closest.toExponential(1)} at t = ${tClosest.toFixed(2)}, ` +
      `E(t = 20) = ${sim.energy().toFixed(4)}`);
  }
}

console.log(failures ? `\n${failures} check(s) failed` : "\nall checks passed");
process.exitCode = failures ? 1 : 0;
