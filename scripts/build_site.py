"""Assemble the deployable site in site/ from each page's source folder.

Each page keeps living where its owner works on it; this script copies the
current versions into one folder that publish_site.py uploads:

    site/index.html              landing page (hand-written, never overwritten)
    site/beat1/, site/beat2/     story page of each beat   <- story/beat1.html, story/beat2.html
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
    site/data/race_pinn/         one PINN per viscosity for the race (ONNX)

Every copied page gets the site-wide navigation bar (home, Beat 1, Beat 2;
see BEATS), and each demo page also gets a previous / next bar at the bottom
that walks through its beat in story order. The landing page's bar is
refreshed between its <!-- NAV --> markers. Links use explicit
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
    "beat1": [("story/beat1.html", "index.html")],
    "beat2": [("story/beat2.html", "index.html")],
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
    "data/race_pinn": "*",                      # from scripts/export_race_onnx.py (.onnx + index.json)
}

# Site-wide navigation. The top bar shows only home and the beats; each beat's
# story page links to its demos, and the demos are chained in story order.
BEATS = [
    ("beat1", "Beat 1", "The wall of brake lights", [
        ("shock", "How the wall forms"), ("pinn", "Our PINN, live"), ("viscosity", "The breaking point"),
        ("loss-vs-truth", "The score that lies"), ("race", "The race")]),
    ("beat2", "Beat 2", "Balls in bowls", [
        ("allen-cahn", "The step-by-step simulator"), ("hilltop", "Falling off a hilltop"),
        ("correction", "Fixing the PINN's guesses")]),
]
NAV_STYLE = """<style>
.rs-nav{position:sticky;top:0;z-index:50;background:var(--bg,#fbfaf7);border-bottom:1px solid rgba(127,127,127,.25);
  font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}
.rs-nav .rs-in{max-width:980px;margin:0 auto;padding:8px 16px;display:flex;align-items:center;gap:6px 18px;flex-wrap:wrap}
.rs-nav a{color:inherit;text-decoration:none;opacity:.72;padding:3px 10px;border-radius:999px;white-space:nowrap}
.rs-nav a:hover,.rs-nav a:focus-visible{opacity:1;outline:none;background:rgba(127,127,127,.14)}
.rs-nav a.on{opacity:1;font-weight:600;background:rgba(127,127,127,.18)}
.rs-nav .rs-home{font:700 15px Georgia,"Iowan Old Style",serif;opacity:1;padding-left:0}
.rs-nav .rs-links{display:flex;align-items:center;gap:4px}
</style>"""
PAGER_STYLE = """<style>
.rs-pager{max-width:980px;margin:24px auto 0;padding:14px 16px 28px;border-top:1px solid rgba(127,127,127,.25);
  display:flex;flex-wrap:wrap;gap:8px 16px;justify-content:space-between;align-items:baseline;
  font:14px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif}
.rs-pager a{color:inherit;text-decoration:none;opacity:.8}
.rs-pager a:hover,.rs-pager a:focus-visible{opacity:1;text-decoration:underline}
.rs-pager .rs-up{opacity:.6}
.rs-pager .rs-next{font-weight:600;margin-left:auto}
</style>"""


def beat_of(page):
    for key, label, title, pages in BEATS:
        if page == key or page in dict(pages):
            return key
    return None


def nav_html(current, prefix="../"):
    """Top bar; `current` is a page key (its beat is highlighted), `prefix` the path back to the site root."""
    on_beat = beat_of(current)
    links = []
    for key, label, title, pages in BEATS:
        on = ' class="on" aria-current="page"' if key == on_beat else ""
        links.append(f'<a href="{prefix}{key}/index.html"{on}>{label}</a>')
    return (f'{NAV_STYLE}\n<nav class="rs-nav" aria-label="Site"><div class="rs-in">'
            f'<a class="rs-home" href="{prefix}index.html">The Real Singularity</a>'
            f'<div class="rs-links">{"".join(links)}</div></div></nav>')


def pager_html(page):
    """Previous / back to the beat / next, for a demo page; empty for pages outside the beats."""
    for b, (key, label, title, pages) in enumerate(BEATS):
        keys = [k for k, _ in pages]
        if page not in keys:
            continue
        i = keys.index(page)
        prev = (f'<a href="../{keys[i - 1]}/index.html">&larr; {pages[i - 1][1]}</a>' if i
                else f'<a href="../{key}/index.html">&larr; {label}: {title}</a>')
        up = f'<a class="rs-up" href="../{key}/index.html">Back to {label}</a>' if i else ""
        if i + 1 < len(keys):
            nxt = f'<a class="rs-next" href="../{keys[i + 1]}/index.html">Next: {pages[i + 1][1]} &rarr;</a>'
        elif b + 1 < len(BEATS):
            nk, nl, nt, _ = BEATS[b + 1]
            nxt = f'<a class="rs-next" href="../{nk}/index.html">Next: {nl}, {nt} &rarr;</a>'
        else:
            nxt = '<a class="rs-next" href="../index.html">Back to the start &rarr;</a>'
        return f'{PAGER_STYLE}\n<nav class="rs-pager" aria-label="{label} pages">{prev}{up}{nxt}</nav>'
    return ""


def add_nav(html: str, current: str) -> str:
    i = html.find("<body")
    if i < 0:
        return html
    j = html.find(">", i) + 1
    html = html[:j] + "\n" + nav_html(current) + html[j:]
    pager = pager_html(current)
    k = html.rfind("</body>")
    if pager and k >= 0:
        html = html[:k] + pager + "\n" + html[k:]
    return html


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
