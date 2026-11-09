"""Assemble the deployable site in site/ from each page's source folder.

Each page keeps living where its owner works on it; this script copies the
current versions into one folder that publish_site.py uploads:

    site/index.html              landing page (hand-written, never overwritten)
    site/shock/                  shock-formation viewer   <- shock viewer/
    site/race/                   finite-volume race        <- Finite volume solver/
    site/pinn/                   live ONNX PINN page       <- web/
    site/loss-vs-truth/          training loss vs. error   <- burgers/js/loss_truth.html
    site/allen-cahn/             Allen-Cahn simulator      <- allen_cahn/js/
    site/viscosity/              PINN vs. exact, three nu  <- burgers/js/viscosity.html
    site/hilltop/                hilltop escape experiment <- allen_cahn/js/hilltop.html
    site/correction/             PINN guesses corrected    <- allen_cahn/js/correction.html
    site/data/reference_json/    Burgers references used by the race
    site/data/allen_cahn/        equilibria and PINN guesses used by the simulator
    site/data/loss_truth/        training histories for the loss-vs-truth page
    site/data/viscosity/         PINN predictions for the viscosity page

Every copied page gets the site-wide navigation bar (see NAV), and the
landing page's bar is refreshed between its <!-- NAV --> markers. Links use explicit
.../index.html paths because CloudFront only serves index.html at the site root.

Run from the repo root after changing any page, then commit site/:
    python scripts/build_site.py
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"

# (source, destination inside site/)
PAGES = {
    "shock": [("shock viewer/index.html", "index.html"),
              ("shock viewer/shock_viewer.js", "shock_viewer.js")],
    "race": [("Finite volume solver/race_solver.html", "index.html"),
             ("Finite volume solver/burgers_fv.js", "burgers_fv.js")],
    "pinn": [("web/index.html", "index.html"),
             ("web/pinn.onnx", "pinn.onnx")],
    "allen-cahn": [("allen_cahn/js/simulator.html", "index.html"),
                   ("allen_cahn/js/allen_cahn.js", "allen_cahn.js")],
    "loss-vs-truth": [("burgers/js/loss_truth.html", "index.html")],
    "viscosity": [("burgers/js/viscosity.html", "index.html")],
    "correction": [("allen_cahn/js/correction.html", "index.html"),
                   ("allen_cahn/js/allen_cahn.js", "allen_cahn.js")],
    "hilltop": [("allen_cahn/js/hilltop.html", "index.html"),
                ("allen_cahn/js/allen_cahn.js", "allen_cahn.js"),
                ("allen_cahn/js/hilltop.js", "hilltop.js")],
}
DATA = {
    "data/reference_json": "ref_nu*.json",      # the race needs only the ref_ files
    "data/allen_cahn": "*.json",
    "data/loss_truth": "runs.json",             # from scripts/export_loss_truth.py
    "data/viscosity": "*.json",                 # from scripts/export_viscosity.py
}

# Site-wide navigation, injected at the top of every page so readers can move
# between demos in order. (page key, short label) grouped by part; None = home.
NAV = [
    ("Part 1", [("shock", "Cliff"), ("race", "Race"), ("pinn", "PINN"), ("viscosity", "Breaking point"),
                ("loss-vs-truth", "Score")]),
    ("Part 2", [("allen-cahn", "Simulator"), ("correction", "Fixing guesses"), ("hilltop", "Hilltop")]),
]
NAV_STYLE = """<style>
.rs-nav{position:sticky;top:0;z-index:50;background:var(--bg,#fbfaf7);border-bottom:1px solid rgba(127,127,127,.25);
  font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}
.rs-nav .rs-in{max-width:980px;margin:0 auto;padding:8px 16px;display:flex;align-items:center;gap:6px 18px;flex-wrap:wrap}
.rs-nav a{color:inherit;text-decoration:none;opacity:.72;padding:3px 9px;border-radius:999px;white-space:nowrap}
.rs-nav a:hover,.rs-nav a:focus-visible{opacity:1;outline:none;background:rgba(127,127,127,.14)}
.rs-nav a.on{opacity:1;font-weight:600;background:rgba(127,127,127,.18)}
.rs-nav .rs-home{font:700 15px Georgia,"Iowan Old Style",serif;opacity:1;padding-left:0}
.rs-nav .rs-links{display:flex;align-items:center;gap:2px;overflow-x:auto;scrollbar-width:none;max-width:100%}
.rs-nav .rs-part{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;opacity:.5;margin:0 4px 0 10px;white-space:nowrap}
.rs-nav .rs-part:first-child{margin-left:0}
</style>"""


def nav_html(current, prefix="../"):
    """Navigation bar; `current` is the page key to highlight, `prefix` the path back to the site root."""
    parts = []
    for part, pages in NAV:
        parts.append(f'<span class="rs-part">{part}</span>')
        for key, label in pages:
            on = ' class="on" aria-current="page"' if key == current else ""
            parts.append(f'<a href="{prefix}{key}/index.html"{on}>{label}</a>')
    return (f'{NAV_STYLE}\n<nav class="rs-nav" aria-label="Demos"><div class="rs-in">'
            f'<a class="rs-home" href="{prefix}index.html">The Real Singularity</a>'
            f'<div class="rs-links">{"".join(parts)}</div></div></nav>')


def add_nav(html: str, current: str) -> str:
    i = html.find("<body")
    if i < 0:
        return html
    j = html.find(">", i) + 1
    return html[:j] + "\n" + nav_html(current) + html[j:]


def refresh_landing_nav():
    """The landing page is hand-written; only the part between the NAV markers is regenerated."""
    landing = SITE / "index.html"
    html = landing.read_text(encoding="utf-8")
    a, b = "<!-- NAV -->", "<!-- /NAV -->"
    if a in html and b in html:
        start, end = html.index(a) + len(a), html.index(b)
        html = html[:start] + "\n" + nav_html(None, prefix="") + "\n" + html[end:]
        landing.write_text(html, encoding="utf-8")


def main():
    SITE.mkdir(exist_ok=True)
    if not (SITE / "index.html").exists():
        raise SystemExit("site/index.html (the landing page) is missing")

    for page, files in PAGES.items():
        out = SITE / page
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        for src, dst in files:
            src_path = ROOT / src
            if not src_path.exists():
                raise SystemExit(f"missing source for {page}: {src}")
            if dst.endswith(".html"):
                (out / dst).write_text(add_nav(src_path.read_text(encoding="utf-8"), page),
                                       encoding="utf-8")
            else:
                shutil.copy2(src_path, out / dst)
            print(f"{src:45s} -> site/{page}/{dst}")

    refresh_landing_nav()

    for folder, pattern in DATA.items():
        out = SITE / folder
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir(parents=True)
        files = sorted((ROOT / folder).glob(pattern))
        if not files:
            raise SystemExit(f"no {pattern} files in {folder}")
        for f in files:
            shutil.copy2(f, out / f.name)
            print(f"{str(f.relative_to(ROOT)):45s} -> site/{folder}/{f.name}")

    total = sum(p.stat().st_size for p in SITE.rglob("*") if p.is_file())
    print(f"\nsite/ is ready: {total / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
