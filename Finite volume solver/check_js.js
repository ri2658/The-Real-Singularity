/*
 * Step 4 checks for the JS solver. Run from anywhere:
 *     node "Finite volume solver/check_js.js"
 *
 * Needs data/reference_json/ from export_json.py.
 *   Check 1: JS output == Python output (same nu, N = 1000)      -> translation is correct
 *   Check 2: JS output vs reference, relative L2 for each nu, N  -> the number to report
 */
const fs = require("fs");
const path = require("path");
const { solveBurgers, relL2, interpToRef } = require("./burgers_fv.js");

const DIR = path.resolve(__dirname, "..", "data", "reference_json");
const names = fs.readdirSync(DIR)
  .filter((f) => f.startsWith("ref_") && f.endsWith(".json"))
  .map((f) => f.slice(4, -5))
  .sort();
const load = (f) => JSON.parse(fs.readFileSync(path.join(DIR, f), "utf8"));

// ---------------- Check 1: JS vs Python ----------------
console.log("Check 1: JS vs Python solver (N = 1000), should agree to ~1e-10");
let allPass = true;
for (const name of names) {
  const py = load(`pycheck_${name}.json`);
  const { snaps } = solveBurgers(py.nu, py.N, py.times);
  let maxDiff = 0;
  snaps.forEach((s, k) => s.forEach((v, i) => { maxDiff = Math.max(maxDiff, Math.abs(v - py.u[k][i])); }));
  const ok = maxDiff < 1e-9;
  allPass = allPass && ok;
  console.log(`  ${name.padEnd(10)} max |JS - Python| = ${maxDiff.toExponential(2)}   ${ok ? "PASS" : "FAIL"}`);
}
console.log(allPass ? "  -> translation OK\n" : "  -> translation has a bug, fix before Check 2\n");

// ---------------- Check 2: JS vs reference ----------------
console.log("Check 2: JS solver vs reference (relative L2 over the whole x-t grid)");
const rows = ["file,nu_times_pi,N,rel_l2_all,rel_l2_last_t,js_ms"];
for (const name of names) {
  const ref = load(`ref_${name}.json`);                  // ref.u[ti][xi]
  console.log(`  ${name}  (nu = ${ref.nu.toExponential(4)})`);
  const refFlat = Float64Array.from(ref.u.flat());
  for (const N of [500, 1000, 2000, 4000]) {
    const t0 = performance.now();
    const { x, snaps } = solveBurgers(ref.nu, N, ref.t);
    const ms = performance.now() - t0;                    // solve time only
    const sol = new Float64Array(ref.t.length * ref.x.length);
    snaps.forEach((s, ti) => sol.set(interpToRef(ref.x, x, s), ti * ref.x.length));
    const last = ref.t.length - 1, nx = ref.x.length;
    const errAll = relL2(sol, refFlat);
    const errLast = relL2(sol.subarray(last * nx), refFlat.subarray(last * nx));
    console.log(`    N = ${String(N).padStart(5)}   rel L2 = ${errAll.toExponential(3)}   ` +
                `(t = 1 only: ${errLast.toExponential(3)})   solve time ${ms.toFixed(0)} ms`);
    rows.push([name, (ref.nu * Math.PI).toPrecision(3), N, errAll, errLast, ms.toFixed(1)].join(","));
  }
}
const out = path.resolve(__dirname, "js_vs_reference.csv");
fs.writeFileSync(out, rows.join("\n") + "\n");
console.log(`\nsaved ${out}`);
