"""Auto-sync personal developer portfolio and root GitHub Pages hub for radityobw."""

import argparse
import html
import json
import os
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent
GITHUB_USER = "radityobw"
BASE_URL = "https://radityobw.github.io"
GSC_SITE_VERIFICATION = "6y-5Cff0WkeBj7_uWju39rv0nQnqmEgw81an57VJkGg"
PRIORITY_FEATURED = ("SIDIK", "SIDIK-ML", "langkah-kecil", "SIBENGKEL")
IGNORED_REPOS = {GITHUB_USER.lower(), f"{GITHUB_USER.lower()}.github.io"}

PYPI_BADGES: Dict[str, str] = {
    "SIDIK": "https://img.shields.io/pypi/v/sidik?label=PyPI&color=0ea5e9&cacheSeconds=3600",
    "SIDIK-ML": "https://img.shields.io/pypi/v/sidik-ml?label=PyPI&color=f59e0b&cacheSeconds=3600",
}
RELEASE_BADGES: Dict[str, str] = {
    "SIDIK": "https://img.shields.io/github/v/release/radityobw/SIDIK?label=Release&color=0284c7&cacheSeconds=3600",
    "SIDIK-ML": "https://img.shields.io/github/v/release/radityobw/SIDIK-ML?label=Release&color=ea580c&cacheSeconds=3600",
    "langkah-kecil": "https://img.shields.io/github/v/release/radityobw/langkah-kecil?label=Release&color=10b981&cacheSeconds=3600",
    "SIBENGKEL": "https://img.shields.io/github/v/release/radityobw/SIBENGKEL?label=Release&color=ef4444&cacheSeconds=3600",
}

RYOCANTSLEEP_ECOSYSTEM: List[Dict[str, Any]] = [
    {
        "name": "ryocantsleep-mono",
        "stack": "Next.js 16 · Turborepo",
        "status": "Private Repo",
        "accent": "accent-indigo",
        "description": (
            "9-app polymath web monorepo (Core Hub plus Hack, Math, Design, Film, Hear, Play, Read, and Speak personas) "
            "sharing @repo/config, @repo/ui CSS-variable themes, Framer Motion, MDX, and Blender .glb 3D assets via pnpm."
        ),
        "links": [
            ("Core Hub", "https://ryocantsleep.com", True),
            ("Hack", "https://hack.ryocantsleep.com", False),
            ("Math", "https://math.ryocantsleep.com", False),
            ("Play", "https://play.ryocantsleep.com", False),
            ("Speak", "https://speak.ryocantsleep.com", False),
        ],
    },
    {
        "name": "ryocantsleep-edu",
        "stack": "Next.js 16 · Prisma · Postgres",
        "status": "Private Repo",
        "accent": "accent-blue",
        "description": (
            "Full-stack Learning Management System backed by 22 Prisma PostgreSQL models on Supabase, featuring Clerk RBAC, "
            "IP Guard & Upstash Redis rate limiting, Lemon Squeezy checkout with Svix webhooks, shadcn/ui, and PDF/QR certificates."
        ),
        "links": [
            ("Live Platform", "https://edu.ryocantsleep.com", True),
        ],
    },
    {
        "name": "ryocantsleep-api",
        "stack": "Next.js 16 · Supabase · Redis",
        "status": "Private Repo",
        "accent": "accent-amber",
        "description": (
            "Rate-limited (50 req / 10s sliding window via Upstash Redis) 8-domain knowledge facts REST API "
            "(/api/cysecfacts, /api/aifacts, /api/gamedevfacts, and 5 more) paired with a live Recharts latency monitor."
        ),
        "links": [
            ("Live API Monitor", "https://api.ryocantsleep.com", True),
        ],
    },
    {
        "name": "ryocantsleep-labs",
        "stack": "Laravel 12 · Docker · Nginx",
        "status": "Private / Self-Hosted",
        "accent": "accent-red",
        "description": (
            "Dockerized hybrid cyber range isolating frontend_net, backend_net, and sandbox_net behind Nginx with SQLi, IDOR, SSRF, "
            "and RCE sandboxes, dynamic UUID flags, Grafana + Loki logs, and a 6-stage DevSecOps pipeline (Gitleaks, Trivy, OWASP ZAP, k6, Syft SBOM)."
        ),
        "links": [],
    },
]

APPLIED_STACK_GROUPS: List[Dict[str, Any]] = [
    {
        "title": "Languages",
        "items": ["Python", "TypeScript", "JavaScript", "PHP", "C++", "HTML5", "CSS3"],
    },
    {
        "title": "Frameworks & ML",
        "items": ["Next.js 16", "React 19", "Laravel", "Tailwind CSS", "Alpine.js", "Vite", "scikit-learn"],
    },
    {
        "title": "Data & Caching",
        "items": ["PostgreSQL", "Prisma", "Supabase", "Upstash Redis", "MySQL", "SQLite"],
    },
    {
        "title": "DevSecOps & Cloud",
        "items": ["Docker", "Nginx", "Grafana", "GitHub Actions", "Vercel", "Cloudflare", "pnpm", "Git"],
    },
    {
        "title": "Game Dev & 3D",
        "items": ["Godot v4.5", "Blender"],
    },
]


def _clean_text(val: Optional[str]) -> str:
    if not val:
        return ""
    return val.replace("\u2014", "-").strip()


def _load_snapshot() -> List[Dict[str, Any]]:
    snap = ROOT_DIR / "repos_snapshot.json"
    if not snap.is_file():
        return []
    data = json.loads(snap.read_text(encoding="utf-8"))
    return [dict(r) for r in data if isinstance(r, dict)]


def _fetch_public_repos(offline: bool = False) -> tuple[List[Dict[str, Any]], str]:
    snapshot = _load_snapshot()
    snap_by_name = {r["name"].lower(): r for r in snapshot if r.get("name")}
    repos: Optional[List[Dict[str, Any]]] = None
    source = "offline_snapshot"

    if not offline:
        headers = {
            "User-Agent": "radityobw-github-pages-builder",
            "Accept": "application/vnd.github+json",
        }
        tok = os.environ.get("GITHUB_TOKEN", "").strip()
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        try:
            url = f"https://api.github.com/users/{GITHUB_USER}/repos?type=owner&sort=updated&per_page=100"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            if isinstance(raw, list) and raw:
                repos = [r for r in raw if isinstance(r, dict) and not r.get("fork")]
                source = "github_api"
        except Exception:
            repos = None

    if repos is None:
        repos = snapshot

    filtered: List[Dict[str, Any]] = []
    for rp in repos:
        name = str(rp.get("name", "")).strip()
        if not name or name.lower() in IGNORED_REPOS or rp.get("fork"):
            continue
        fallback = snap_by_name.get(name.lower(), {})
        desc = _clean_text(rp.get("description")) or _clean_text(fallback.get("description"))
        lang = _clean_text(rp.get("language")) or _clean_text(fallback.get("language")) or "Repository"
        filtered.append({
            "name": name,
            "html_url": str(rp.get("html_url") or f"https://github.com/{GITHUB_USER}/{name}"),
            "description": desc or f"Public repository {name} by {GITHUB_USER}.",
            "language": lang,
            "stargazers_count": int(rp.get("stargazers_count") or 0),
            "has_pages": bool(rp.get("has_pages") or fallback.get("has_pages")),
            "homepage": _clean_text(rp.get("homepage")) or _clean_text(fallback.get("homepage")),
        })

    priority_map = {n.lower(): idx for idx, n in enumerate(PRIORITY_FEATURED)}
    filtered.sort(key=lambda r: (priority_map.get(r["name"].lower(), 999), -int(r["stargazers_count"]), r["name"].lower()))
    return filtered, source


def _render_card(repo: Dict[str, Any], featured: bool) -> str:
    name = repo["name"]
    esc_name = html.escape(name)
    esc_desc = html.escape(repo["description"])
    esc_lang = html.escape(repo["language"])
    esc_repo_url = html.escape(repo["html_url"])
    homepage = repo.get("homepage") or (f"{BASE_URL}/{name}/" if repo.get("has_pages") else "")

    accent_cls = "featured-card" if featured else "repo-card"
    if name == "SIDIK":
        accent_cls += " accent-blue"
    elif name == "SIDIK-ML":
        accent_cls += " accent-amber"
    elif name == "langkah-kecil":
        accent_cls += " accent-green"
    elif name == "SIBENGKEL":
        accent_cls += " accent-red"

    badges_html = ""
    if name in PYPI_BADGES or name in RELEASE_BADGES:
        badge_links: List[str] = []
        if name in PYPI_BADGES:
            pypi_pkg = name.lower()
            badge_links.append(
                f'<a href="https://pypi.org/project/{pypi_pkg}/"><img src="{PYPI_BADGES[name]}" alt="{esc_name} PyPI" /></a>'
            )
        if name in RELEASE_BADGES:
            badge_links.append(
                f'<a href="{esc_repo_url}/releases/latest"><img src="{RELEASE_BADGES[name]}" alt="{esc_name} Release" /></a>'
            )
        badges_html = f'\n          <div class="badges">{"".join(badge_links)}</div>'

    actions = [f'<a class="btn primary" href="{esc_repo_url}">GitHub</a>']
    if homepage:
        lbl = "Documentation" if name in ("SIDIK", "SIDIK-ML", "langkah-kecil", "SIBENGKEL") else "Website"
        actions.insert(0, f'<a class="btn docs" href="{html.escape(homepage)}">{lbl}</a>')
    if name in ("SIDIK", "SIDIK-ML"):
        actions.append(f'<a class="btn" href="https://pypi.org/project/{name.lower()}/">PyPI</a>')

    return (
        f'        <article class="card {accent_cls}">\n'
        f'          <div class="card-top">\n'
        f'            <h3>{esc_name}</h3>\n'
        f'            <span class="lang-pill">{esc_lang}</span>\n'
        f'          </div>\n'
        f'          <p>{esc_desc}</p>{badges_html}\n'
        f'          <div class="links">{"".join(actions)}</div>\n'
        f'        </article>'
    )


def _render_ecosystem_card(item: Dict[str, Any]) -> str:
    esc_name = html.escape(item["name"])
    esc_stack = html.escape(item["stack"])
    esc_status = html.escape(item["status"])
    esc_desc = html.escape(item["description"])
    accent_cls = html.escape(item["accent"])

    actions: List[str] = []
    for label, href, is_primary in item.get("links", []):
        cls = "btn docs" if is_primary else "btn"
        actions.append(f'<a class="{cls}" href="{html.escape(href)}">{html.escape(label)}</a>')
    if not actions:
        actions.append('<span class="status-note">Isolated Docker / CI Infrastructure</span>')

    return (
        f'        <article class="card featured-card {accent_cls}">\n'
        f'          <div class="card-top">\n'
        f'            <div>\n'
        f'              <h3>{esc_name}</h3>\n'
        f'              <span class="status-pill">{esc_status}</span>\n'
        f'            </div>\n'
        f'            <span class="lang-pill">{esc_stack}</span>\n'
        f'          </div>\n'
        f'          <p>{esc_desc}</p>\n'
        f'          <div class="links">{"".join(actions)}</div>\n'
        f'        </article>'
    )


def _render_stack_groups() -> str:
    blocks: List[str] = []
    for grp in APPLIED_STACK_GROUPS:
        chips = "".join(f'<span class="chip">{html.escape(t)}</span>' for t in grp["items"])
        blocks.append(
            f'        <div class="stack-group">\n'
            f'          <h3>{html.escape(grp["title"])}</h3>\n'
            f'          <div class="chips">{chips}</div>\n'
            f'        </div>'
        )
    return "\n".join(blocks)


def build_site(out_dir: Path, offline: bool = False, update_root: bool = False) -> None:
    repos, source = _fetch_public_repos(offline=offline)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    featured_names = set(PRIORITY_FEATURED)
    featured = [r for r in repos if r["name"] in featured_names or r["has_pages"] or r["stargazers_count"] > 0]
    others = [r for r in repos if r not in featured]

    pages_repos = [r["name"] for r in repos if r["has_pages"]]
    sitemap_urls = [f"{BASE_URL}/"] + [f"{BASE_URL}/{n}/" for n in pages_repos]
    sitemap_refs = [f"Sitemap: {BASE_URL}/sitemap.xml"] + [f"Sitemap: {BASE_URL}/{n}/sitemap.xml" for n in pages_repos]

    robots_txt = "User-agent: *\nAllow: /\n\n" + "\n".join(sitemap_refs) + "\n"
    sitemap_txt = "\n".join(sitemap_urls) + "\n"

    url_nodes = []
    for idx, u in enumerate(sitemap_urls):
        prio = "1.0" if idx <= 1 else "0.9"
        url_nodes.append(
            f"  <url>\n"
            f"    <loc>{html.escape(u)}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>{prio}</priority>\n"
            f"  </url>"
        )
    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(url_nodes)
        + "\n</urlset>\n"
    )

    ld_items = []
    for idx, rp in enumerate(repos, 1):
        ld_items.append({
            "@type": "ListItem",
            "position": idx,
            "name": rp["name"],
            "url": rp["homepage"] or rp["html_url"],
        })

    json_ld = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": "Radityo Budi Waskito (radityobw)",
                "alternateName": "radityobw GitHub Pages",
                "url": f"{BASE_URL}/",
            },
            {
                "@type": "Person",
                "name": "Radityo Budi Waskito",
                "alternateName": GITHUB_USER,
                "url": f"{BASE_URL}/",
                "affiliation": {
                    "@type": "CollegeOrUniversity",
                    "name": "Universitas Sultan Ageng Tirtayasa",
                },
                "knowsAbout": [
                    "Cybersecurity",
                    "Static Application Security Testing (SAST)",
                    "Software Composition Analysis (SCA)",
                    "Explainable Non-ANN Machine Learning",
                    "Full-Stack Web Development",
                    "Next.js & TypeScript Monorepos",
                    "Laravel & PHP",
                    "Docker & DevSecOps",
                    "Godot Game Development",
                ],
                "sameAs": [
                    f"https://github.com/{GITHUB_USER}",
                    "https://ryocantsleep.com",
                    "https://edu.ryocantsleep.com",
                    "https://api.ryocantsleep.com",
                    "https://linkedin.com/in/radityobw",
                    "https://instagram.com/radityo_bw",
                    "https://twitter.com/radityo_bw",
                    "https://www.youtube.com/@radityobw",
                    "https://pypi.org/project/sidik/",
                    "https://pypi.org/project/sidik-ml/",
                ] + [rp["html_url"] for rp in featured],
            },
            {
                "@type": "ItemList",
                "name": "Public GitHub Repositories by Radityo Budi Waskito",
                "numberOfItems": len(repos),
                "itemListElement": ld_items,
            },
        ],
    }, indent=2)

    featured_html = "\n".join(_render_card(r, featured=True) for r in featured)
    ecosystem_html = "\n".join(_render_ecosystem_card(item) for item in RYOCANTSLEEP_ECOSYSTEM)
    stack_html = _render_stack_groups()
    others_html = "\n".join(_render_card(r, featured=False) for r in others)
    others_section = ""
    if others:
        others_section = (
            f'\n    <section>\n'
            f'      <h2>Other Public Repositories ({len(others)})</h2>\n'
            f'      <div class="grid">\n{others_html}\n      </div>\n'
            f'    </section>'
        )

    index_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Radityo Budi Waskito (radityobw) - Security Tools, RyoCantSleep &amp; Projects</title>
  <meta name="description" content="Official developer portfolio of Radityo Budi Waskito (radityobw): SIDIK polyglot SAST & 8-ecosystem SCA, SIDIK-ML Non-ANN AI, the RyoCantSleep full-stack ecosystem (Next.js 16 monorepo, Prisma LMS, Upstash API, Docker cyber range), Langkah Kecil Godot game, and SIBENGKEL." />
  <meta name="author" content="Radityo Budi Waskito" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{BASE_URL}/" />
  <link rel="icon" href="/favicon.ico" sizes="48x48" />
  <link rel="icon" type="image/png" href="/favicon-48x48.png" sizes="48x48" />
  <link rel="icon" type="image/png" href="/favicon-192x192.png" sizes="192x192" />
  <link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180" />

  <meta name="google-site-verification" content="{GSC_SITE_VERIFICATION}" />

  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="Radityo Budi Waskito (radityobw)" />
  <meta property="og:title" content="Radityo Budi Waskito (radityobw) - Developer Portfolio &amp; RyoCantSleep" />
  <meta property="og:description" content="Cybersecurity tools (SIDIK, SIDIK-ML), RyoCantSleep multi-app ecosystem (Next.js 16, Prisma, Supabase, Redis, Docker), Godot games (Langkah Kecil), and Laravel apps." />
  <meta property="og:url" content="{BASE_URL}/" />
  <meta property="og:image" content="{BASE_URL}/og-banner.png" />
  <meta property="og:image:type" content="image/png" />
  <meta property="og:image:width" content="1280" />
  <meta property="og:image:height" content="640" />
  <meta property="og:image:alt" content="Radityo Budi Waskito (radityobw) - Developer Portfolio &amp; Project Hub" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:creator" content="@radityo_bw" />
  <meta name="twitter:title" content="Radityo Budi Waskito (radityobw) - Portfolio &amp; Projects" />
  <meta name="twitter:description" content="Explore SIDIK, SIDIK-ML, RyoCantSleep multi-app platforms, Langkah Kecil, and open-source repositories by radityobw." />
  <meta name="twitter:image" content="{BASE_URL}/og-banner.png" />

  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
  <script>(function(){{try{{var t=localStorage.getItem('radityobw_theme');document.documentElement.dataset.theme=(t==='light')?'light':'dark';}}catch(e){{document.documentElement.dataset.theme='dark';}}}})();</script>

  <script type="importmap">
  {{
    "imports": {{
      "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
      "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
    }}
  }}
  </script>

  <script type="application/ld+json">
  {json_ld}
  </script>

  <style>
    :root {{
      --bg: #000000;
      --topbar-bg: rgba(0, 0, 0, 0.72);
      --surface: #141416;
      --surface-2: #1c1c1f;
      --hairline: rgba(255, 255, 255, 0.11);
      --card-border: rgba(255, 255, 255, 0.08);
      --text: #f5f5f7;
      --heading: #ffffff;
      --lead: #c7c7cc;
      --body-sub: #a1a1a6;
      --muted: #86868b;
      --crimson: #ff375f;
      --blue: #0a84ff;
      --blue-hover: #2994ff;
      --indigo: #5e5ce6;
      --amber: #ffd60a;
      --green: #30d158;
      --pill-bg: #1d1d1f;
      --btn-bg: rgba(255, 255, 255, 0.08);
      --btn-hover: rgba(255, 255, 255, 0.14);
      --stage-bg: radial-gradient(ellipse 68% 66% at 50% 48%, #3d4454 0%, #20242f 46%, #111319 78%, #090a0d 100%);
      --stage-shadow: 0 24px 56px rgba(0, 0, 0, 0.48);
      --stage-pill: rgba(255, 255, 255, 0.1);
      --mono: "SF Mono", ui-monospace, "JetBrains Mono", Menlo, monospace;
      --display: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Inter", "Helvetica Neue", sans-serif;
      --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Inter", "Helvetica Neue", sans-serif;
    }}
    html[data-theme="light"] {{
      --bg: #ffffff;
      --topbar-bg: rgba(255, 255, 255, 0.78);
      --surface: #f5f5f7;
      --surface-2: #ffffff;
      --hairline: rgba(0, 0, 0, 0.08);
      --card-border: rgba(0, 0, 0, 0.05);
      --text: #1d1d1f;
      --heading: #1d1d1f;
      --lead: #424245;
      --body-sub: #424245;
      --muted: #6e6e73;
      --crimson: #d70015;
      --blue: #0071e3;
      --blue-hover: #0077ed;
      --indigo: #5e5ce6;
      --amber: #c97a00;
      --green: #1d8348;
      --pill-bg: #ffffff;
      --btn-bg: rgba(0, 0, 0, 0.05);
      --btn-hover: rgba(0, 0, 0, 0.09);
      --stage-bg: radial-gradient(circle at 50% 42%, #ffffff 0%, #f1f1f4 72%, #e8e8ed 100%);
      --stage-shadow: 0 20px 50px rgba(0, 0, 0, 0.06);
      --stage-pill: rgba(255, 255, 255, 0.84);
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: var(--sans);
      background: var(--bg);
      color: var(--text);
      line-height: 1.58;
      overflow-x: clip;
      -webkit-font-smoothing: antialiased;
      text-rendering: optimizeLegibility;
      transition: background-color 0.22s ease, color 0.22s ease;
    }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .progress-track {{
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 2px;
      background: transparent;
      z-index: 60;
      pointer-events: none;
    }}
    #scroll-progress-bar {{
      width: 100%;
      height: 100%;
      background: var(--blue);
      transform-origin: left center;
      transform: scaleX(0);
    }}

    .topbar {{
      position: sticky;
      top: 0;
      z-index: 40;
      min-height: 52px;
      background: var(--topbar-bg);
      backdrop-filter: saturate(180%) blur(20px);
      -webkit-backdrop-filter: saturate(180%) blur(20px);
      border-bottom: 1px solid var(--hairline);
    }}
    .topbar-inner {{
      max-width: 1220px;
      min-height: 52px;
      margin: 0 auto;
      padding: 10px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      font-size: 13px;
      color: var(--muted);
    }}
    .brand-mark {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--text);
      font-weight: 600;
      font-size: 14px;
      letter-spacing: -0.01em;
      white-space: nowrap;
    }}
    .brand-mark:hover {{ text-decoration: none; }}
    .brand-dot {{
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--crimson);
      display: inline-block;
      flex-shrink: 0;
    }}
    .topbar-nav {{
      display: flex;
      align-items: center;
      gap: 20px;
    }}
    .topbar-nav a {{
      color: var(--muted);
      font-weight: 500;
      white-space: nowrap;
      transition: color 0.15s ease;
    }}
    .topbar-nav a:hover {{
      color: var(--text);
      text-decoration: none;
    }}
    .theme-btn {{
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: 980px;
      border: 1px solid var(--hairline);
      background: var(--btn-bg);
      color: var(--text);
      cursor: pointer;
      padding: 0;
      flex-shrink: 0;
      transition: background 0.15s ease;
    }}
    .theme-btn:hover {{ background: var(--btn-hover); }}
    .theme-btn svg {{ width: 15px; height: 15px; display: block; }}
    html[data-theme="dark"] .icon-moon {{ display: none; }}
    html[data-theme="light"] .icon-sun {{ display: none; }}

    .wrap {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 56px 28px 84px;
    }}
    .monograph-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.18fr) minmax(350px, 0.82fr);
      gap: 48px;
      align-items: start;
    }}
    .vitrine-col {{
      position: sticky;
      top: 84px;
      order: 2;
      min-width: 0;
    }}
    .chapters-col {{
      order: 1;
      min-width: 0;
      max-width: 100%;
    }}

    #stage-3d {{
      position: relative;
      height: min(560px, calc(100vh - 120px));
      min-height: 400px;
      background: var(--stage-bg);
      border: 1px solid var(--card-border);
      border-radius: 28px;
      box-shadow: var(--stage-shadow);
      overflow: hidden;
      cursor: grab;
      user-select: none;
      touch-action: pan-y;
    }}
    #stage-3d:active {{ cursor: grabbing; }}

    .stage-hud-top {{
      position: absolute;
      top: 20px;
      left: 22px;
      right: 22px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      font-weight: 500;
      color: var(--muted);
      pointer-events: none;
      z-index: 4;
    }}
    #stage-chapter {{
      background: var(--stage-pill);
      backdrop-filter: blur(12px);
      color: var(--text);
      border: 1px solid var(--hairline);
      padding: 4px 12px;
      border-radius: 980px;
      font-weight: 600;
      letter-spacing: -0.005em;
    }}
    .stage-hud-bottom {{
      position: absolute;
      bottom: 18px;
      left: 22px;
      right: 22px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-family: var(--mono);
      font-size: 11px;
      color: var(--muted);
      pointer-events: none;
      z-index: 4;
    }}
    #canvas-3d {{
      position: relative;
      z-index: 2;
      width: 100%;
      height: 100%;
      display: block;
      opacity: 0;
      transition: opacity 0.45s ease;
    }}
    #stage-3d.is-ready #canvas-3d {{ opacity: 1; }}
    .stage-fallback {{
      position: absolute;
      inset: 0;
      margin: auto;
      width: 148px;
      height: 148px;
      object-fit: contain;
      filter: drop-shadow(0 0 1px rgba(255, 255, 255, 0.28)) drop-shadow(0 10px 22px rgba(0, 0, 0, 0.35));
      z-index: 1;
    }}
    html[data-theme="light"] .stage-fallback {{
      filter: drop-shadow(0 10px 22px rgba(0, 0, 0, 0.12));
    }}
    #stage-3d.is-ready .stage-fallback {{ display: none; }}

    .chapter {{
      padding-bottom: 60px;
      margin-bottom: 60px;
      border-bottom: 1px solid var(--hairline);
      min-width: 0;
      max-width: 100%;
    }}
    .chapter:last-child {{
      border-bottom: none;
      margin-bottom: 16px;
      padding-bottom: 16px;
    }}
    .chapter-tag {{
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 12px;
      display: block;
    }}
    h1 {{
      font-family: var(--display);
      margin: 0 0 16px;
      font-size: clamp(32px, 4.2vw, 50px);
      font-weight: 700;
      line-height: 1.06;
      letter-spacing: -0.035em;
      color: var(--heading);
      overflow-wrap: break-word;
    }}
    .handle {{
      font-family: var(--sans);
      font-size: 17px;
      font-weight: 500;
      letter-spacing: -0.01em;
      color: var(--muted);
      display: block;
      margin-top: 8px;
    }}
    .sub {{
      margin: 0 0 28px;
      color: var(--lead);
      font-size: 17px;
      line-height: 1.55;
      max-width: 640px;
    }}
    .metrics-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      border-radius: 20px;
      background: var(--surface);
      border: 1px solid var(--card-border);
      margin-bottom: 28px;
      overflow: hidden;
      min-width: 0;
    }}
    .metric-cell {{
      padding: 16px 18px;
      border-right: 1px solid var(--hairline);
      font-variant-numeric: tabular-nums;
      min-width: 0;
    }}
    .metric-cell:last-child {{ border-right: none; }}
    .metric-val {{
      font-family: var(--display);
      font-size: 24px;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--heading);
      display: block;
    }}
    .metric-lbl {{
      font-size: 12px;
      color: var(--muted);
      font-weight: 500;
    }}
    .hero-actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    h2 {{
      font-family: var(--display);
      font-size: 28px;
      font-weight: 700;
      letter-spacing: -0.025em;
      color: var(--heading);
      margin: 0 0 10px;
      overflow-wrap: break-word;
    }}
    .section-note {{
      margin: 0 0 24px;
      color: var(--muted);
      font-size: 15px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      min-width: 0;
    }}
    .card {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: 24px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 12px;
      min-width: 0;
      max-width: 100%;
      overflow-wrap: break-word;
      transition: transform 0.2s ease, border-color 0.2s ease;
    }}
    .card:hover {{
      transform: translateY(-2px);
      border-color: var(--hairline);
    }}
    .accent-blue {{ border-left: 3px solid var(--blue); }}
    .accent-indigo {{ border-left: 3px solid var(--indigo); }}
    .accent-amber {{ border-left: 3px solid var(--amber); }}
    .accent-green {{ border-left: 3px solid var(--green); }}
    .accent-red {{ border-left: 3px solid var(--crimson); }}
    .card-top {{
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      min-width: 0;
    }}
    .card-top > div {{ min-width: 0; flex: 1 1 130px; }}
    .card-top h3 {{
      font-family: var(--display);
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      letter-spacing: -0.02em;
      color: var(--heading);
      overflow-wrap: anywhere;
    }}
    .lang-pill {{
      flex-shrink: 0;
      font-size: 11px;
      font-weight: 600;
      padding: 3px 10px;
      border-radius: 980px;
      background: var(--pill-bg);
      border: 1px solid var(--hairline);
      color: var(--muted);
      max-width: 100%;
    }}
    .status-pill {{
      display: inline-block;
      margin-top: 6px;
      font-size: 11px;
      font-weight: 500;
      padding: 2px 9px;
      border-radius: 980px;
      background: var(--btn-bg);
      color: var(--muted);
    }}
    .status-note {{
      font-size: 12px;
      color: var(--muted);
    }}
    .card p {{ margin: 0; color: var(--body-sub); font-size: 14px; line-height: 1.55; flex-grow: 1; overflow-wrap: break-word; }}
    :not(pre) > code {{ overflow-wrap: anywhere; word-break: break-word; font-size: 0.9em; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .links {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    .btn {{
      display: inline-flex;
      align-items: center;
      padding: 8px 16px;
      border-radius: 980px;
      font-size: 13px;
      font-weight: 500;
      background: var(--btn-bg);
      color: var(--text);
      border: 1px solid transparent;
      transition: background 0.15s ease;
    }}
    .btn.docs {{
      background: var(--blue);
      color: #ffffff;
      font-weight: 600;
    }}
    .btn:hover {{
      text-decoration: none;
      background: var(--btn-hover);
    }}
    .btn.docs:hover {{
      background: var(--blue-hover);
    }}
    .stack-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      min-width: 0;
    }}
    .stack-group {{
      background: var(--surface);
      border: 1px solid var(--card-border);
      border-radius: 20px;
      padding: 18px;
      min-width: 0;
    }}
    .stack-group h3 {{
      margin: 0 0 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.04em;
    }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{
      font-size: 12px;
      font-weight: 500;
      padding: 4px 10px;
      border-radius: 980px;
      background: var(--pill-bg);
      border: 1px solid var(--hairline);
      color: var(--text);
    }}
    footer {{
      margin-top: 40px;
      padding-top: 24px;
      border-top: 1px solid var(--hairline);
      font-size: 12.5px;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      flex-wrap: wrap;
      gap: 10px;
    }}
    @media (max-width: 960px) {{
      .monograph-grid {{ grid-template-columns: 1fr; gap: 32px; }}
      .vitrine-col {{ position: relative; top: 0; order: 1; }}
      .chapters-col {{ order: 2; }}
      #stage-3d {{ height: 360px; min-height: 300px; }}
      .metrics-strip {{ grid-template-columns: 1fr; }}
      .metric-cell {{ border-right: none; border-bottom: 1px solid var(--hairline); }}
      .metric-cell:last-child {{ border-bottom: none; }}
    }}
    @media (max-width: 640px) {{
      .wrap {{ padding: 32px 18px 64px; }}
      .topbar-inner {{ padding: 10px 16px; gap: 10px; }}
      .topbar-nav {{ gap: 12px; font-size: 12px; }}
      .topbar-nav a:nth-child(n+4) {{ display: none; }}
    }}
  </style>
</head>
<body>
  <div class="progress-track"><div id="scroll-progress-bar"></div></div>

  <nav class="topbar" aria-label="Primary navigation">
    <div class="topbar-inner">
      <a class="brand-mark" href="{BASE_URL}/"><span class="brand-dot"></span>radityobw</a>
      <div class="topbar-nav">
        <a href="#sec-projects">Projects</a>
        <a href="#sec-ecosystem">RyoCantSleep</a>
        <a href="#sec-stack">Stack</a>
        <a href="https://github.com/{GITHUB_USER}">GitHub</a>
        <button id="theme-toggle" class="theme-btn" type="button" aria-label="Toggle light or dark theme" title="Toggle theme">
          <svg class="icon-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"></path></svg>
          <svg class="icon-moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        </button>
      </div>
    </div>
  </nav>

  <div class="wrap">
    <div class="monograph-grid">
      <main class="chapters-col">
        <section class="chapter" data-chapter="profile" id="sec-profile">
          <span class="chapter-tag">Engineering Portfolio</span>
          <h1>Radityo Budi Waskito <span class="handle">@{GITHUB_USER}</span></h1>
          <p class="sub">
            Informatics student at Universitas Sultan Ageng Tirtayasa (UNTIRTA) building offline static security analyzers (<strong>SIDIK</strong>, <strong>SIDIK-ML</strong>), the <strong>RyoCantSleep</strong> full-stack ecosystem (Next.js 16 monorepo, Prisma LMS, Upstash Redis API, and Dockerized cyber range), educational Godot software (<strong>Langkah Kecil</strong>), and Laravel platforms (<strong>SIBENGKEL</strong>).
          </p>
          <div class="metrics-strip">
            <div class="metric-cell">
              <span class="metric-val">{len(repos)}</span>
              <span class="metric-lbl">Public Repositories</span>
            </div>
            <div class="metric-cell">
              <span class="metric-val">{len(pages_repos)}</span>
              <span class="metric-lbl">Live Doc Hubs</span>
            </div>
            <div class="metric-cell">
              <span class="metric-val">4</span>
              <span class="metric-lbl">RyoCantSleep Apps</span>
            </div>
          </div>
          <div class="hero-actions">
            <a class="btn docs" href="https://github.com/{GITHUB_USER}">GitHub</a>
            <a class="btn" href="https://ryocantsleep.com">RyoCantSleep</a>
            <a class="btn" href="https://linkedin.com/in/radityobw">LinkedIn</a>
            <a class="btn" href="https://instagram.com/radityo_bw">Instagram</a>
            <a class="btn" href="https://twitter.com/radityo_bw">X</a>
            <a class="btn" href="https://www.youtube.com/@radityobw">YouTube</a>
            <a class="btn" href="mailto:radityobudiw@gmail.com">Email</a>
            <a class="btn" href="https://jurnal.mediaakademik.com/index.php/jma/article/view/9068/6647">JMA Paper</a>
          </div>
        </section>

        <section class="chapter" data-chapter="opensource" id="sec-projects">
          <span class="chapter-tag">Open Source</span>
          <h2>Pinned &amp; Featured Public Projects ({len(featured)})</h2>
          <p class="section-note">Flagship repositories synchronized via GitHub API with automated release packaging and static documentation sites.</p>
          <div class="grid">
{featured_html}
          </div>
        </section>

        <section class="chapter" data-chapter="ryocantsleep" id="sec-ecosystem">
          <span class="chapter-tag">Private Infrastructure</span>
          <h2>RyoCantSleep Ecosystem</h2>
          <p class="section-note">Private R&amp;D repositories powering production educational platforms, APIs, and isolated security training infrastructure.</p>
          <div class="grid">
{ecosystem_html}
          </div>
        </section>

        <section class="chapter" data-chapter="stack" id="sec-stack">
          <span class="chapter-tag">Capabilities</span>
          <h2>Applied Tech Stack</h2>
          <p class="section-note">Languages, frameworks, data stores, and infrastructure verified across production deployments.</p>
          <div class="stack-grid">
{stack_html}
          </div>
          {others_section}
        </section>
      </main>

      <aside class="vitrine-col" aria-label="Interactive 3D Mascot Stage">
        <div id="stage-3d">
          <div class="stage-hud-top">
            <span id="stage-chapter">01 Profile</span>
            <span>Drag to orbit</span>
          </div>
          <img class="stage-fallback" src="/avatar.png" alt="Radityo Budi Waskito (@{GITHUB_USER})" width="148" height="148" />
          <canvas id="canvas-3d" aria-label="Interactive 3D RadityoBW Mascot"></canvas>
          <div class="stage-hud-bottom">
            <span>radityobw.glb</span>
            <span>Scroll choreography</span>
          </div>
        </div>
      </aside>
    </div>

    <footer>
      <span>Radityo Budi Waskito (@{GITHUB_USER}) · Auto-synced from GitHub API ({today})</span>
      <span><a href="https://github.com/{GITHUB_USER}">GitHub</a> | <a href="https://ryocantsleep.com">RyoCantSleep</a> | <a href="https://linkedin.com/in/radityobw">LinkedIn</a> | <a href="https://instagram.com/radityo_bw">Instagram</a> | <a href="https://twitter.com/radityo_bw">X</a> | <a href="https://www.youtube.com/@radityobw">YouTube</a> | <a href="{BASE_URL}/SIDIK/">SIDIK</a> | <a href="{BASE_URL}/SIDIK-ML/">SIDIK-ML</a> | <a href="{BASE_URL}/SIBENGKEL/">SIBENGKEL</a> | <a href="{BASE_URL}/langkah-kecil/">Langkah Kecil</a> | <a href="/sitemap.xml">Sitemap</a></span>
    </footer>
  </div>

  <script>
    (function(){{
      var btn = document.getElementById('theme-toggle');
      if (!btn) return;
      btn.addEventListener('click', function(){{
        var next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
        document.documentElement.dataset.theme = next;
        try {{ localStorage.setItem('radityobw_theme', next); }} catch(e) {{}}
      }});
    }})();
  </script>
  <script type="module" src="/scene3d.js"></script>
</body>
</html>
"""

    targets = [out_dir]
    if update_root and out_dir.resolve() != ROOT_DIR.resolve():
        targets.append(ROOT_DIR)

    for target in targets:
        if target.resolve() != ROOT_DIR.resolve() and target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        (target / "index.html").write_text(index_html, encoding="utf-8")
        (target / "robots.txt").write_text(robots_txt, encoding="utf-8")
        (target / "sitemap.xml").write_text(sitemap_xml, encoding="utf-8")
        (target / "sitemap.txt").write_text(sitemap_txt, encoding="utf-8")
        if target.resolve() != ROOT_DIR.resolve():
            for asset in (
                ".nojekyll",
                "og-banner.png",
                "avatar.png",
                "scene3d.js",
                "favicon.ico",
                "favicon-48x48.png",
                "favicon-192x192.png",
                "apple-touch-icon.png",
            ):
                src = ROOT_DIR / asset
                if src.is_file():
                    shutil.copy2(src, target / asset)
            glb_src = ROOT_DIR / "models" / "radityobw.glb"
            if glb_src.is_file():
                (target / "models").mkdir(parents=True, exist_ok=True)
                shutil.copy2(glb_src, target / "models" / "radityobw.glb")

    print(f"Built root portfolio ({len(repos)} repos, pages={pages_repos}, source={source}) -> {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build auto-synced root GitHub Pages portfolio for radityobw.")
    parser.add_argument("--out", default="_site", help="Output directory (default: _site)")
    parser.add_argument("--offline", action="store_true", help="Use bundled repos_snapshot.json without network API calls")
    parser.add_argument("--update-root", action="store_true", help="Also write rendered index.html, robots.txt, and sitemaps into repo root")
    args = parser.parse_args()
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT_DIR / out_path
    build_site(out_path, offline=args.offline, update_root=args.update_root)


if __name__ == "__main__":
    main()
