#!/usr/bin/env python3
"""Generate a clean 'most used languages' SVG from real GitHub repo data.

Self-contained: no third-party rendering server, so it never errors at view
time. Run by .github/workflows/languages.yml on a schedule; the resulting
languages.svg is committed and embedded in the profile README.
"""
import json
import os
import urllib.request

USER = "strjonas"
TOP_N = 8
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

# GitHub Linguist colors for the languages we expect; grey fallback.
COLORS = {
    "Swift": "#F05138", "Dart": "#00B4AB", "Python": "#3572A5",
    "JavaScript": "#F1E05A", "TypeScript": "#3178C6", "Kotlin": "#A97BFF",
    "Java": "#B07219", "HTML": "#E34C26", "CSS": "#563D7C", "SCSS": "#C6538C",
    "Rust": "#DEA584", "C++": "#F34B7D", "C#": "#178600", "C": "#555555",
    "Ruby": "#701516", "Shell": "#89E051", "Go": "#00ADD8",
    "Objective-C": "#438EFF", "CMake": "#DA3434", "Dockerfile": "#384D54",
}
OTHER = "#BFC6CE"


def api(path):
    req = urllib.request.Request("https://api.github.com" + path)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def collect():
    totals, page = {}, 1
    while True:
        repos = api(f"/users/{USER}/repos?per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo.get("fork"):
                continue
            for lang, b in api(f"/repos/{USER}/{repo['name']}/languages").items():
                totals[lang] = totals.get(lang, 0) + b
        page += 1
    return totals


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(totals):
    grand = sum(totals.values()) or 1
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:TOP_N]
    other = sum(v for _, v in ranked[TOP_N:])
    items = [(k, v * 100 / grand, COLORS.get(k, OTHER)) for k, v in top]
    if other > 0:
        items.append(("Other", other * 100 / grand, OTHER))

    W, PAD = 500, 18
    bar_y, bar_h, bar_w = 40, 9, W - 2 * PAD
    title_c, text_c, sub_c = "#0969DA", "#3D444D", "#656D76"

    parts = [
        f'<svg width="{W}" height="180" viewBox="0 0 {W} 180" '
        'xmlns="http://www.w3.org/2000/svg" '
        'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        f'<text x="{PAD}" y="24" fill="{title_c}" font-size="15" '
        'font-weight="600">Most used languages</text>',
    ]

    # stacked bar
    x = PAD
    parts.append(f'<clipPath id="r"><rect x="{PAD}" y="{bar_y}" width="{bar_w}" '
                 f'height="{bar_h}" rx="{bar_h/2}"/></clipPath>')
    parts.append(f'<g clip-path="url(#r)">')
    for _, pct, color in items:
        w = bar_w * pct / 100
        parts.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" '
                     f'height="{bar_h}" fill="{color}"/>')
        x += w
    parts.append('</g>')

    # legend: 2 columns
    col_w = bar_w / 2
    row_y0, row_h = 78, 23
    for i, (name, pct, color) in enumerate(items):
        col, row = i % 2, i // 2
        cx = PAD + col * col_w
        cy = row_y0 + row * row_h
        parts.append(f'<circle cx="{cx+5}" cy="{cy-4}" r="5.5" fill="{color}"/>')
        parts.append(f'<text x="{cx+18}" y="{cy}" font-size="13" '
                     f'fill="{text_c}" font-weight="500">{esc(name)} '
                     f'<tspan fill="{sub_c}" font-weight="400">{pct:.1f}%</tspan></text>')

    parts.append('</svg>')
    return "\n".join(parts)


if __name__ == "__main__":
    svg = build(collect())
    with open("languages.svg", "w") as f:
        f.write(svg)
    print("wrote languages.svg")
