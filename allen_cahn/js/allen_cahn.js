/*
 * Allen-Cahn simulator (Beat 2), forward Euler on the notes' grid.
 *
 *   u_t = u_xx + mu (u - u^3),   x in (0, pi),   u(0, t) = u(pi, t) = 0
 *
 * Discretization (same as the notes, Table 1 and Table 2):
 *   N = 128 intervals, h = pi / N, unknowns U_1 .. U_{N-1} (127 interior points),
 *   (L U)_i = (U_{i-1} - 2 U_i + U_{i+1}) / h^2 with U_0 = U_N = 0,
 *   F(U) = L U + mu (U - U^3),
 *   forward Euler: U <- U + dt * F(U), dt = 0.4 h^2 by default.
 *
 * Energy (the quantity forward Euler must never increase when dt is small enough):
 *   E_h(U) = sum_{i=0}^{N-1} h * 0.5 * ((U_{i+1} - U_i) / h)^2
 *          - sum_{i=1}^{N-1} h * mu * (0.5 U_i^2 - 0.25 U_i^4)
 *   F(U) = -(1/h) dE_h/dU, so each Euler step is gradient descent on E_h with
 *   learning rate dt / h. That is the "simulation = gradient descent" link in Beat 2.
 *
 * Stability: the most negative eigenvalue of L is about -4 / h^2, so forward Euler
 * needs dt <= h^2 / 2 (the "learning-rate limit"). dt = 1.05 * h^2 / 2 blows up.
 *
 * Same layout as Michelle's burgers_fv.js: plain functions on Float64Array,
 * buffers allocated once, works in the browser (<script src>) and in Node (require).
 */

const AC_DEFAULTS = { mu: 6, N: 128, dtFactor: 0.4 };

// Interior grid: x_i = i h for i = 1 .. N-1.
function makeGrid(N = AC_DEFAULTS.N) {
  const h = Math.PI / N;
  const x = new Float64Array(N - 1);
  for (let i = 0; i < N - 1; i++) x[i] = (i + 1) * h;
  return { N, h, x };
}

// out = F(U) = L U + mu (U - U^3). Boundary values U_0 = U_N = 0 are implicit.
function rhs(U, mu, h, out) {
  const n = U.length;
  const ih2 = 1 / (h * h);
  for (let i = 0; i < n; i++) {
    const ul = i > 0 ? U[i - 1] : 0;
    const ur = i < n - 1 ? U[i + 1] : 0;
    const u = U[i];
    out[i] = (ul - 2 * u + ur) * ih2 + mu * (u - u * u * u);
  }
  return out;
}

// Discrete energy E_h(U), see the header.
function energy(U, mu, h) {
  const n = U.length;
  let grad = 0;
  let prev = 0;                                   // U_0 = 0
  for (let i = 0; i < n; i++) {
    const d = U[i] - prev;
    grad += d * d;
    prev = U[i];
  }
  grad += prev * prev;                            // last interval, U_N = 0
  let pot = 0;
  for (let i = 0; i < n; i++) {
    const u2 = U[i] * U[i];
    pot += 0.5 * u2 - 0.25 * u2 * u2;
  }
  return 0.5 * grad / h - h * mu * pot;
}

// Max-norm helpers.
function maxAbs(U) {
  let m = 0;
  for (let i = 0; i < U.length; i++) m = Math.max(m, Math.abs(U[i]));
  return m;
}

function maxAbsDiff(a, b) {
  let m = 0;
  for (let i = 0; i < a.length; i++) m = Math.max(m, Math.abs(a[i] - b[i]));
  return m;
}

// Max |F(U)|: zero exactly at an equilibrium, so it measures "how steady" U is.
function residual(U, mu, h) {
  return maxAbs(rhs(U, mu, h, new Float64Array(U.length)));
}

// Small seeded random generator (mulberry32) so "random start" is reproducible.
function makeRng(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Starting curves on the interior grid.
//   "hump-like": amp * sin(x)      (same symmetry as the stable hump)
//   "S-like":    amp * sin(2x)     (same symmetry as the unstable S state)
//   "random":    uniform in [-amp, amp] at each point
function initialCurve(kind, x, { amp = 0.5, seed = 0 } = {}) {
  const U = new Float64Array(x.length);
  if (kind === "hump-like") {
    for (let i = 0; i < x.length; i++) U[i] = amp * Math.sin(x[i]);
  } else if (kind === "S-like") {
    for (let i = 0; i < x.length; i++) U[i] = amp * Math.sin(2 * x[i]);
  } else if (kind === "random") {
    const rng = makeRng(seed);
    for (let i = 0; i < x.length; i++) U[i] = amp * (2 * rng() - 1);
  } else {
    throw new Error(`unknown initial curve: ${kind}`);
  }
  return U;
}

/**
 * A forward-Euler simulator that keeps its own state, for the animated page
 * and for the checks. Usage:
 *     const sim = createSimulator({ mu: 6, N: 128, dtFactor: 0.4 });
 *     sim.set(U0);            // Float64Array of length N - 1
 *     sim.advance(1000);      // 1000 Euler steps
 *     sim.t, sim.U, sim.energy()
 */
function createSimulator({ mu = AC_DEFAULTS.mu, N = AC_DEFAULTS.N, dtFactor = AC_DEFAULTS.dtFactor } = {}) {
  const grid = makeGrid(N);
  const n = N - 1;
  const sim = {
    mu,
    N,
    h: grid.h,
    x: grid.x,
    dt: dtFactor * grid.h * grid.h,
    t: 0,
    steps: 0,
    U: new Float64Array(n),
    F: new Float64Array(n),                       // work buffer for F(U), allocated once

    set(U0) {
      if (U0.length !== n) throw new Error(`expected ${n} values, got ${U0.length}`);
      this.U.set(U0);
      this.t = 0;
      this.steps = 0;
    },

    setDtFactor(f) {
      this.dt = f * this.h * this.h;
    },

    // In-place update is safe: F is computed from the whole old U first.
    advance(nSteps) {
      const U = this.U, F = this.F, dt = this.dt;
      for (let k = 0; k < nSteps; k++) {
        rhs(U, this.mu, this.h, F);
        for (let i = 0; i < n; i++) U[i] += dt * F[i];
      }
      this.steps += nSteps;
      this.t += nSteps * dt;
    },

    // Advance until time T (the last step is shortened to land on T exactly).
    advanceTo(T) {
      const full = Math.floor((T - this.t) / this.dt + 1e-9);
      if (full > 0) this.advance(full);
      const rest = T - this.t;
      if (rest > 1e-15) {
        const keep = this.dt;
        this.dt = rest;
        this.advance(1);
        this.dt = keep;
      }
    },

    energy() { return energy(this.U, this.mu, this.h); },
    residual() { return residual(this.U, this.mu, this.h); },
    blewUp() { return !Number.isFinite(maxAbs(this.U)) || maxAbs(this.U) > 1e6; },
  };
  return sim;
}

// One-shot run: snapshots and energies at the times in tOut (increasing).
function simulate(U0, tOut, opts = {}) {
  const sim = createSimulator(opts);
  sim.set(U0);
  const snaps = [], energies = [];
  for (const T of tOut) {
    sim.advanceTo(T);
    snaps.push(Float64Array.from(sim.U));        // copy: U keeps changing
    energies.push(sim.energy());
  }
  return { x: sim.x, h: sim.h, dt: sim.dt, snaps, energies };
}

const AllenCahn = {
  AC_DEFAULTS, makeGrid, rhs, energy, residual, maxAbs, maxAbsDiff,
  makeRng, initialCurve, createSimulator, simulate,
};
if (typeof module !== "undefined") module.exports = AllenCahn;
