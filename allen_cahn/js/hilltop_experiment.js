/*
 * Run the hilltop escape-time experiment and save the results.
 *
 *     node allen_cahn/js/hilltop_experiment.js
 *
 * Uses the S state from data/allen_cahn/equilibria.json if present, otherwise
 * finds S with the simulator (start 0.5 sin(2x), run to t = 8).
 * Writes data/allen_cahn/hilltop_escape.json.
 */
const fs = require("fs");
const path = require("path");
const AC = require("./allen_cahn.js");
const H = require("./hilltop.js");

const ROOT = path.resolve(__dirname, "..", "..");
const EXPONENTS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];      // eps = 10^-k
const DELTAS = [0.05, 0.1, 0.3];                               // escape thresholds
const THEORY_LAMBDA = 1.5293821131006693;                      // Table 1 / Newton
const THEORY_SLOPE = Math.log(10) / THEORY_LAMBDA;

function loadS() {
  const p = path.join(ROOT, "data", "allen_cahn", "equilibria.json");
  if (fs.existsSync(p)) {
    const eq = JSON.parse(fs.readFileSync(p, "utf8"));
    const S = eq.states ? eq.states.S.U : eq.S;
    return { S: Float64Array.from(S), source: "equilibria.json (Newton)" };
  }
  const { x } = AC.makeGrid();
  return { S: AC.simulate(AC.initialCurve("S-like", x), [8]).snaps[0], source: "simulator steady state" };
}

const { S, source } = loadS();
const { x, h } = AC.makeGrid();
console.log(`S from ${source}; residual max|F(S)| = ${AC.residual(S, 6, h).toExponential(1)}`);

const mode = H.unstableMode(S);
console.log(`unstable mode: lambda_1 = ${mode.lambda.toFixed(6)} (Table 1: 1.529), ` +
  `eigen-residual ${mode.residual.toExponential(1)}`);
console.log(`theory: slope = ln(10) / lambda_1 = ${THEORY_SLOPE.toFixed(4)} per decade of eps\n`);

const results = { theory_lambda: THEORY_LAMBDA, theory_slope: THEORY_SLOPE,
  measured_lambda: mode.lambda, S_source: source, runs: [] };

for (const delta of DELTAS) {
  for (const sign of [+1, -1]) {
    const rows = [];
    for (const k of EXPONENTS) {
      const eps = sign * 10 ** -k;
      const r = H.escapeTime(S, mode.v, eps, { delta });
      rows.push({ k, eps, T: r.T, endEnergy: r.endEnergy });
    }
    const ok = rows.filter((r) => Number.isFinite(r.T));
    const fit = H.fitLine(ok.map((r) => r.k), ok.map((r) => r.T));
    results.runs.push({ delta, sign, rows, fit });
    console.log(`delta = ${delta}, push ${sign > 0 ? "+" : "-"}v:  ` +
      rows.map((r) => `k=${r.k}: ${r.T.toFixed(3)}`).join("  "));
    console.log(`   fit: slope ${fit.slope.toFixed(4)} per decade (theory ${THEORY_SLOPE.toFixed(4)}), ` +
      `max residual ${fit.maxResidual.toExponential(1)}`);
  }
}

const out = path.join(ROOT, "data", "allen_cahn", "hilltop_escape.json");
fs.writeFileSync(out, JSON.stringify(results, null, 1));
console.log(`\nsaved ${path.relative(ROOT, out)}`);
