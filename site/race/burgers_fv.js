/*
 * Finite-volume solver for the viscous Burgers equation (JavaScript port of burgers_fv.py).
 *
 *   u_t + (u^2 / 2)_x = nu * u_xx,   x in [-1, 1],   u(x, 0) = -sin(pi x),   u(+-1, t) = 0
 *
 * The code mirrors the Python file line by line, so results should agree to ~1e-12.
 * Works in the browser (<script src="burgers_fv.js">) and in Node (require).
 *
 * See burgers_fv.py for the physics and math notes (conservation form, upwinding,
 * CFL condition, ghost cells). Only JS-specific points are explained here.
 */

// Engquist-Osher flux for f(u) = u^2 / 2: right-moving part from the left state,
// left-moving part from the right state (upwinding).
function eoFlux(uL, uR) {
  const p = Math.max(uL, 0);
  const m = Math.min(uR, 0);
  return 0.5 * p * p + 0.5 * m * m;
}

/**
 * Solve and return snapshots at the times in tOut (increasing array).
 * Returns { x: Float64Array(N) cell centres, snaps: Float64Array[] one per time }.
 *
 * Performance notes (CS): Float64Array is a flat block of doubles, much faster than
 * a normal JS array. We allocate every buffer ONCE outside the loop, and swap two
 * buffers (u, un) each step instead of creating new arrays, so the loop never
 * triggers garbage collection.
 */
function solveBurgers(nu, N, tOut, cfl = 0.4) {
  const dx = 2 / N;
  const x = new Float64Array(N);
  let u = new Float64Array(N);                  // current state (old time level)
  let un = new Float64Array(N);                 // next state (new time level)
  const F = new Float64Array(N + 1);            // fluxes at the N + 1 faces
  for (let i = 0; i < N; i++) {
    x[i] = -1 + dx * (i + 0.5);                 // cell centres
    u[i] = -Math.sin(Math.PI * x[i]);           // initial condition
  }

  let t = 0;
  const snaps = [];
  for (const T of tOut) {
    while (t < T - 1e-12) {
      let umax = 0;
      for (let i = 0; i < N; i++) umax = Math.max(umax, Math.abs(u[i]));
      // Explicit Euler is stable only for small dt: advection (dx/|u|) and
      // diffusion (dx^2/(2 nu)) limits combined; last step is cut to land on T.
      const dt = Math.min(cfl / (umax / dx + 2 * nu / (dx * dx)), T - t);

      // Fluxes at interior faces; wall faces carry f(0) = 0 because u = 0 there.
      F[0] = 0;
      F[N] = 0;
      for (let i = 1; i < N; i++) F[i] = eoFlux(u[i - 1], u[i]);

      // Update every cell from OLD values (u) into NEW values (un).
      // Ghost cells: ghost = -(edge cell) makes the wall value exactly 0.
      for (let i = 0; i < N; i++) {
        const ul = i > 0 ? u[i - 1] : -u[0];
        const ur = i < N - 1 ? u[i + 1] : -u[N - 1];
        const visc = nu * (ur - 2 * u[i] + ul) / (dx * dx);
        un[i] = u[i] - dt * (F[i + 1] - F[i]) / dx + dt * visc;
      }
      const tmp = u; u = un; un = tmp;          // swap buffers: new state becomes current
      t += dt;
    }
    snaps.push(Float64Array.from(u));           // copy: u will be overwritten next step
  }
  return { x, snaps };
}

// Relative L2 error ||a - b|| / ||b|| over arrays (or flattened grids).
function relL2(a, b) {
  let num = 0, den = 0;
  for (let i = 0; i < a.length; i++) {
    const d = a[i] - b[i];
    num += d * d;
    den += b[i] * b[i];
  }
  return Math.sqrt(num / den);
}

// Linear interpolation of cell-centre values (xc, u) onto the points xRef (ascending).
// We add the two wall points (u = 0 at x = -1 and x = 1) so the ends are not extrapolated.
function interpToRef(xRef, xc, u) {
  const n = xc.length;
  const xs = new Float64Array(n + 2), us = new Float64Array(n + 2);
  xs[0] = -1; us[0] = 0;
  for (let i = 0; i < n; i++) { xs[i + 1] = xc[i]; us[i + 1] = u[i]; }
  xs[n + 1] = 1; us[n + 1] = 0;

  const out = new Float64Array(xRef.length);
  let j = 0;                                    // both grids ascend, so one sweep is enough
  for (let k = 0; k < xRef.length; k++) {
    const xq = xRef[k];
    while (j < xs.length - 2 && xs[j + 1] < xq) j++;
    const w = (xq - xs[j]) / (xs[j + 1] - xs[j]);
    out[k] = us[j] + w * (us[j + 1] - us[j]);
  }
  return out;
}

if (typeof module !== "undefined") module.exports = { solveBurgers, relL2, interpToRef, eoFlux };
