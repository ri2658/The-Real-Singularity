/*
 * Hilltop escape-time experiment (week 6 success check for Beat 2).
 *
 * The S state is an unstable equilibrium ("hilltop"): its Jacobian
 *     J = L + mu * diag(1 - 3 S^2)
 * has exactly one positive eigenvalue, lambda_1 ~ 1.5294 (Table 1). Start the
 * simulator at S + eps * v, with v the unit eigenvector for lambda_1. While the
 * push is small it grows like eps * exp(lambda_1 t), so the time to leave S is
 *     T(eps) ~ (1 / lambda_1) * ln(delta / eps) + const,
 * and T rises by ln(10) / lambda_1 ~ 1.5056 for every tenfold decrease of eps.
 * Reproducing that slope with the simulator is the success check.
 *
 * Works in the browser (after allen_cahn.js) and in Node (require).
 */

const AC_ = typeof module !== "undefined" ? require("./allen_cahn.js") : AllenCahn;

// y = J x for the Jacobian at state U (same boundary handling as rhs()).
function jacobianTimes(U, x, mu, h, y) {
  const n = U.length, ih2 = 1 / (h * h);
  for (let i = 0; i < n; i++) {
    const xl = i > 0 ? x[i - 1] : 0;
    const xr = i < n - 1 ? x[i + 1] : 0;
    y[i] = (xl - 2 * x[i] + xr) * ih2 + mu * (1 - 3 * U[i] * U[i]) * x[i];
  }
  return y;
}

/**
 * Unstable eigenpair of J at U by power iteration on B = I + dt * J.
 * With dt = 0.4 h^2 every eigenvalue of B lies in (-1, 1 + dt * lambda_1], so the
 * largest one in magnitude is the unstable mode. Returns { lambda, v } with v
 * unit length in max-norm and v[i] > 0 at the first interior point (sign fixed
 * so "+eps" always means the same direction).
 */
function unstableMode(U, { mu = 6, h = Math.PI / 128, dtFactor = 0.4, iters = 40000, start = null } = {}) {
  const n = U.length, dt = dtFactor * h * h;
  let v = new Float64Array(n), w = new Float64Array(n);
  if (start) v.set(start);
  else for (let i = 0; i < n; i++) v[i] = Math.sin((i + 1) * h);  // symmetric start, overlaps the mode
  const Jv = new Float64Array(n);
  for (let k = 0; k < iters; k++) {
    jacobianTimes(U, v, mu, h, Jv);
    let m = 0;
    for (let i = 0; i < n; i++) { w[i] = v[i] + dt * Jv[i]; m = Math.max(m, Math.abs(w[i])); }
    for (let i = 0; i < n; i++) w[i] /= m;
    [v, w] = [w, v];
  }
  if (v[0] < 0) for (let i = 0; i < n; i++) v[i] = -v[i];
  // Rayleigh quotient for the eigenvalue of J.
  jacobianTimes(U, v, mu, h, Jv);
  let num = 0, den = 0;
  for (let i = 0; i < n; i++) { num += v[i] * Jv[i]; den += v[i] * v[i]; }
  // Residual of J v = lambda v, as a check.
  const lambda = num / den;
  let res = 0;
  for (let i = 0; i < n; i++) res = Math.max(res, Math.abs(Jv[i] - lambda * v[i]));
  return { lambda, v, residual: res };
}

/**
 * Time for the simulator to leave S, starting from S + eps * v.
 * "Left" means max |U - S| first exceeds delta. Returns { T, steps, endEnergy } or
 * { T: Infinity } if it has not left by tMax.
 */
function escapeTime(S, v, eps, { delta = 0.1, tMax = 60, dtFactor = 0.4, mu = 6, N = 128 } = {}) {
  const sim = AC_.createSimulator({ mu, N, dtFactor });
  const U0 = new Float64Array(S.length);
  for (let i = 0; i < S.length; i++) U0[i] = S[i] + eps * v[i];
  sim.set(U0);
  const maxSteps = Math.ceil(tMax / sim.dt);
  for (let k = 1; k <= maxSteps; k++) {
    sim.advance(1);
    if (AC_.maxAbsDiff(sim.U, S) > delta) {
      return { T: sim.t, steps: sim.steps, endEnergy: sim.energy() };
    }
  }
  return { T: Infinity, steps: sim.steps };
}

// Least-squares line y = a + b x; returns { slope, intercept, maxResidual }.
function fitLine(xs, ys) {
  const n = xs.length;
  const xm = xs.reduce((s, v) => s + v, 0) / n, ym = ys.reduce((s, v) => s + v, 0) / n;
  let sxy = 0, sxx = 0;
  for (let i = 0; i < n; i++) { sxy += (xs[i] - xm) * (ys[i] - ym); sxx += (xs[i] - xm) ** 2; }
  const slope = sxy / sxx, intercept = ym - slope * xm;
  let maxResidual = 0;
  for (let i = 0; i < n; i++) maxResidual = Math.max(maxResidual, Math.abs(ys[i] - (intercept + slope * xs[i])));
  return { slope, intercept, maxResidual };
}

const Hilltop = { jacobianTimes, unstableMode, escapeTime, fitLine };
if (typeof module !== "undefined") module.exports = Hilltop;
