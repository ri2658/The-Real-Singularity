"""
Finite-volume solver for the viscous Burgers equation (Step 1 prototype).
 
PHYSICS
    Burgers' equation is a toy model of fluid flow:
 
        u_t + u * u_x = nu * u_xx          (u = velocity, nu = viscosity)
 
    - u * u_x  : nonlinear "advection". Fast fluid catches up with slow fluid,
                 so the profile steepens and can form a SHOCK (a near-jump in u).
    - nu * u_xx: viscosity. It smooths things out and keeps the shock finite.
    The smaller nu is, the thinner and steeper the shock.
 
MATH
    Since u * u_x = (u^2 / 2)_x, we can write the equation in CONSERVATION FORM:
 
        u_t + f(u)_x = nu * u_xx,     f(u) = u^2 / 2     (f is the "flux")
 
    Integrate over a small interval (a "cell") [x_{i-1/2}, x_{i+1/2}]. The change
    of the cell's average value equals (flux in) - (flux out) + diffusion:
 
        d(u_i)/dt = -(F_{i+1/2} - F_{i-1/2}) / dx + nu * (u_{i+1} - 2 u_i + u_{i-1}) / dx^2
 
    This is the finite-volume method. Because every cell's outflow is its
    neighbour's inflow, the total amount of u is conserved by construction.
    That is why this method handles shocks well.
 
PROBLEM SETUP (same benchmark as the PINN)
    x in [-1, 1],  t in [0, 1],  u(x, 0) = -sin(pi x),  u(-1, t) = u(1, t) = 0
"""
 
import time
 
import numpy as np
 
 
def eo_flux(uL, uR):
    """
    Engquist-Osher numerical flux for f(u) = u^2 / 2.
 
    MATH / PHYSICS: the flux F_{i+1/2} must be computed at the face between two
    cells, where we know the value on the left (uL) and on the right (uR).
    Information travels along characteristics with speed u:
        u > 0 -> information comes from the LEFT  (use uL)
        u < 0 -> information comes from the RIGHT (use uR)
    This choice is called UPWINDING, and it is what keeps the scheme stable.
    Engquist-Osher splits f into a right-moving and a left-moving part:
        f(u) = f_plus(u) + f_minus(u),  f_plus = max(u,0)^2/2,  f_minus = min(u,0)^2/2
    and takes f_plus from the left state and f_minus from the right state.
    Works on whole arrays at once (NumPy vectorization).
    """
    return 0.5 * np.maximum(uL, 0.0) ** 2 + 0.5 * np.minimum(uR, 0.0) ** 2
 
 
def solve(nu, N, t_out, cfl=0.4):
    """
    Solve Burgers' equation and return snapshots at the times in t_out.
 
    nu    : viscosity
    N     : number of cells (more cells = sharper shock, slower run)
    t_out : increasing list of times at which to save the solution
    cfl   : safety factor (< 1) for the time step, see below
 
    Returns x (cell centres, shape (N,)) and snaps (shape (len(t_out), N)).
    """
    dx = 2.0 / N                                  # cell width; domain length is 2
    x = -1.0 + dx * (np.arange(N) + 0.5)          # cell CENTRES: -1 + dx/2, -1 + 3dx/2, ...
    u = -np.sin(np.pi * x)                        # initial condition: one number per cell
 
    t = 0.0
    snaps = []
    for T in t_out:
        while t < T - 1e-12:
            # --- time step -----------------------------------------------------
            # CS / MATH: we use FORWARD EULER (explicit): new = old + dt * rate.
            # It is only stable if dt is small enough (CFL condition):
            #   advection: information must not cross more than one cell per step,
            #              so dt <~ dx / max|u|
            #   diffusion: dt <~ dx^2 / (2 nu)
            # Dividing by the sum of both rates satisfies both conditions at once.
            # The last min(...) shortens the final step so we land exactly on T.
            dt = min(cfl / (np.abs(u).max() / dx + 2.0 * nu / dx ** 2), T - t)
 
            # --- boundary conditions (GHOST CELLS) --------------------------------
            # We need u_{i-1} and u_{i+1} for the first and last cell, so we pad the
            # array with one fake cell on each side. Setting ghost = -(edge cell)
            # makes the interpolated value on the wall exactly 0, which enforces
            # the Dirichlet condition u(+-1, t) = 0.
            ue = np.concatenate(([-u[0]], u, [-u[-1]]))      # length N + 2
 
            # --- fluxes through all N + 1 faces at once ---------------------------
            # Face j sits between ue[j] and ue[j+1]. The two wall faces carry
            # flux f(0) = 0 because u = 0 on the wall (nothing crosses the wall).
            F = eo_flux(ue[:-1], ue[1:])
            F[0] = 0.0
            F[-1] = 0.0
 
            # --- viscous term: second difference approximates u_xx ----------------
            visc = nu * (ue[2:] - 2.0 * u + ue[:-2]) / dx ** 2
 
            # --- UPDATE EVERY CELL AT ONCE -----------------------------------------
            # F[1:] are the right faces, F[:-1] the left faces of the N cells.
            # (right flux - left flux) / dx is the net outflow, so we subtract it.
            # NumPy computes the right-hand side from the OLD u before assigning,
            # so all cells use the same time level (no half-updated neighbours).
            u = u - dt * (F[1:] - F[:-1]) / dx + dt * visc
            t += dt
        snaps.append(u.copy())
    return x, np.array(snaps)
 
 
def rel_l2(a, b):
    """Relative L2 error ||a - b|| / ||b||: the same metric the PINN team uses."""
    return np.linalg.norm(a - b) / np.linalg.norm(b)
 
 
def inspect_reference(path):
    """Print what is inside a reference .npz so you can see key names and shapes."""
    ref = np.load(path)
    for k in ref.files:
        print(k, ref[k].shape, ref[k].dtype)
 
 
# -----------------------------------------------------------------------------
# Sanity checks you can run without any reference file:   python burgers_fv.py
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    t_out = [0.25, 0.5, 0.75, 1.0]
 
    print("1) Physical sanity checks (N = 1000)")
    for nu_pi in (0.01, 0.003, 0.001):
        nu = nu_pi / np.pi
        t0 = time.perf_counter()
        x, snaps = solve(nu, 1000, t_out)
        ms = 1000 * (time.perf_counter() - t0)
        u = snaps[-1]                                         # solution at t = 1
        # The exact solution is ODD: u(-x) = -u(x). A wrong boundary condition or
        # a one-sided bug would break this symmetry.
        sym = np.abs(u + u[::-1]).max()
        # The shock sits where the slope is steepest; by symmetry that is x = 0.
        slope = np.abs(np.diff(u) / (x[1] - x[0]))
        print(f"  nu = {nu_pi}/pi : {ms:7.0f} ms | symmetry error {sym:.1e} | "
              f"max|u| {np.abs(u).max():.3f} | steepest slope at x = {x[1:][slope.argmax()] - (x[1]-x[0])/2:+.4f}")
 
    print("\n2) Grid convergence at t = 1 (compare with a very fine grid, N = 4000)")
    print("   Error should fall as N grows; at small nu the shock is thinner than a cell,")
    print("   so the error near the shock decays slowly (first-order scheme).")
    for nu_pi in (0.01, 0.003, 0.001):
        nu = nu_pi / np.pi
        _, fine = solve(nu, 4000, [1.0])
        row = []
        for N in (250, 500, 1000, 2000):
            _, s = solve(nu, N, [1.0])
            coarse_ref = fine[0].reshape(N, -1).mean(axis=1)  # average fine cells onto coarse cells
            row.append(f"N={N}: {rel_l2(s[0], coarse_ref):.2e}")
        print(f"  nu = {nu_pi}/pi  " + "   ".join(row))