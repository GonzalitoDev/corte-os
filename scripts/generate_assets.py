#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "src" / "assets"
ICONS = ASSETS / "icons" / "apps"
BACKGROUNDS = ASSETS / "backgrounds"

ACCENTS = {
    "browser": "#22d3ee",
    "files": "#38bdf8",
    "terminal": "#34d399",
    "store": "#a78bfa",
    "settings": "#94a3b8",
    "notes": "#fbbf24",
    "calculator": "#fb7185",
    "monitor": "#22d3ee",
    "media": "#f472b6",
    "security": "#4ade80",
    "installer": "#f59e0b",
    "notifications": "#a78bfa",
    "arcade": "#f97316",
    "welcome": "#22d3ee",
}

GLYPHS = {
    "browser": """
      <circle cx="48" cy="48" r="23"/>
      <ellipse cx="48" cy="48" rx="23" ry="9"/>
      <path d="M48 25v46M25 48h46"/>
    """,
    "files": """
      <path d="M19 31h20l6 7h32v34a4 4 0 0 1-4 4H19a4 4 0 0 1-4-4V35a4 4 0 0 1 4-4z"/>
      <path d="M19 45h54"/>
    """,
    "terminal": """
      <rect x="17" y="22" width="62" height="52" rx="9"/>
      <path d="M29 40l8 8-8 8"/>
      <path d="M45 56h18"/>
    """,
    "store": """
      <path d="M25 35h46l5 44H20z"/>
      <path d="M36 35a12 12 0 0 1 24 0"/>
      <path d="M38 53v5M58 53v5"/>
    """,
    "settings": """
      <circle cx="48" cy="48" r="11"/>
      <path d="M48 18v9M48 69v9M18 48h9M69 48h9M27 27l6 6M63 63l6 6M69 27l-6 6M33 63l-6 6"/>
      <circle cx="48" cy="48" r="23"/>
    """,
    "notes": """
      <rect x="26" y="16" width="44" height="64" rx="7"/>
      <path d="M36 33h24M36 44h24M36 55h16"/>
      <path d="M58 16v12h12"/>
    """,
    "calculator": """
      <rect x="24" y="14" width="48" height="68" rx="9"/>
      <rect x="32" y="24" width="32" height="12" rx="3"/>
      <path d="M34 48h4M46 48h4M58 48h4M34 60h4M46 60h4M58 60h4M34 72h4M46 72h4M58 72h4"/>
    """,
    "monitor": """
      <rect x="16" y="22" width="64" height="42" rx="7"/>
      <path d="M26 52l9-11 7 7 10-15 8 10 10-8"/>
      <path d="M36 76h24M48 64v12"/>
    """,
    "media": """
      <circle cx="48" cy="48" r="24"/>
      <path d="M42 36l17 12-17 12z"/>
    """,
    "security": """
      <path d="M48 16l24 9v19c0 17-10 29-24 36-14-7-24-19-24-36V25z"/>
      <path d="M37 48l8 8 15-17"/>
    """,
    "installer": """
      <path d="M48 18v32M36 38l12 12 12-12"/>
      <path d="M25 58v16a6 6 0 0 0 6 6h34a6 6 0 0 0 6-6V58"/>
    """,
    "notifications": """
      <path d="M30 65h36l-4-8V43a14 14 0 0 0-28 0v14z"/>
      <path d="M42 72a6 6 0 0 0 12 0"/>
      <path d="M48 24V18"/>
    """,
    "arcade": """
      <rect x="17" y="33" width="62" height="36" rx="14"/>
      <path d="M32 45v12M26 51h12"/>
      <circle cx="60" cy="47" r="3"/>
      <circle cx="68" cy="55" r="3"/>
    """,
    "welcome": """
      <path d="M66 32c-5-6-11-9-18-9-14 0-24 11-24 25s10 25 24 25c7 0 13-3 18-9" stroke-width="7"/>
      <circle cx="72" cy="30" r="4" fill="currentColor" stroke="none"/>
    """,
}


def icon(name: str, accent: str) -> str:
    glyph = GLYPHS[name]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" width="96" height="96">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#141b27"/>
      <stop offset="1" stop-color="#080b12"/>
    </linearGradient>
    <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{accent}" stop-opacity="0.95"/>
      <stop offset="1" stop-color="#8b5cf6" stop-opacity="0.45"/>
    </linearGradient>
  </defs>
  <rect x="3" y="3" width="90" height="90" rx="22" fill="url(#bg)" stroke="url(#edge)" stroke-width="2"/>
  <rect x="9" y="9" width="78" height="78" rx="17" fill="none" stroke="#ffffff" stroke-opacity="0.05"/>
  <g fill="none" stroke="{accent}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" color="{accent}">
    {glyph}
  </g>
</svg>
"""


def logo() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <defs>
    <linearGradient id="corte" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#22d3ee"/>
      <stop offset="0.55" stop-color="#38bdf8"/>
      <stop offset="1" stop-color="#8b5cf6"/>
    </linearGradient>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#111827"/>
      <stop offset="1" stop-color="#05070c"/>
    </linearGradient>
  </defs>
  <rect x="6" y="6" width="244" height="244" rx="58" fill="url(#bg)" stroke="url(#corte)" stroke-width="3"/>
  <rect x="18" y="18" width="220" height="220" rx="48" fill="none" stroke="#ffffff" stroke-opacity="0.06" stroke-width="2"/>
  <path d="M179 84c-12-16-31-26-52-26-38 0-68 31-68 70s30 70 68 70c21 0 40-10 52-26" fill="none" stroke="url(#corte)" stroke-width="19" stroke-linecap="round"/>
  <circle cx="196" cy="69" r="10" fill="#22d3ee"/>
  <circle cx="196" cy="69" r="17" fill="#22d3ee" opacity="0.18"/>
  <path d="M116 99l-24 29 24 29" fill="none" stroke="#e6edf7" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"/>
</svg>
"""


def wallpaper(variant: int) -> str:
    palettes = [
        ("#22d3ee", "#8b5cf6", "#0b1020", "#05070d"),
        ("#34d399", "#22d3ee", "#081512", "#04080b"),
        ("#f472b6", "#8b5cf6", "#140b18", "#07050b"),
    ]
    a, b, bg1, bg2 = palettes[variant % len(palettes)]
    title = ["AURORA", "CIRCUIT", "NEBULA"][variant % 3]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1920 1080" width="1920" height="1080">
  <defs>
    <radialGradient id="glowA" cx="18%" cy="12%" r="70%">
      <stop offset="0" stop-color="{a}" stop-opacity="0.28"/>
      <stop offset="1" stop-color="{a}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx="88%" cy="78%" r="72%">
      <stop offset="0" stop-color="{b}" stop-opacity="0.30"/>
      <stop offset="1" stop-color="{b}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="base" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{bg1}"/>
      <stop offset="1" stop-color="{bg2}"/>
    </linearGradient>
    <linearGradient id="stroke" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{a}"/>
      <stop offset="1" stop-color="{b}"/>
    </linearGradient>
    <pattern id="grid" width="64" height="64" patternUnits="userSpaceOnUse">
      <path d="M64 0H0V64" fill="none" stroke="#ffffff" stroke-opacity="0.035" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="1920" height="1080" fill="url(#base)"/>
  <rect width="1920" height="1080" fill="url(#grid)"/>
  <rect width="1920" height="1080" fill="url(#glowA)"/>
  <rect width="1920" height="1080" fill="url(#glowB)"/>
  <g opacity="0.10" fill="none" stroke="url(#stroke)" stroke-width="2">
    <circle cx="1520" cy="260" r="210"/>
    <circle cx="1520" cy="260" r="300"/>
    <circle cx="1520" cy="260" r="390"/>
  </g>
  <g transform="translate(1240 250) scale(2.2)" opacity="0.22">
    <path d="M179 84c-12-16-31-26-52-26-38 0-68 31-68 70s30 70 68 70c21 0 40-10 52-26" fill="none" stroke="url(#stroke)" stroke-width="19" stroke-linecap="round"/>
    <circle cx="196" cy="69" r="10" fill="{a}"/>
  </g>
  <g font-family="Inter, DejaVu Sans, sans-serif" fill="#e6edf7">
    <text x="128" y="742" font-size="86" font-weight="800" letter-spacing="18">CORTE</text>
    <text x="132" y="824" font-size="86" font-weight="200" letter-spacing="26" fill="{a}">OS</text>
    <text x="136" y="884" font-size="21" font-weight="500" letter-spacing="9" fill="#8a97ab">SISTEMA OPERATIVO · {title}</text>
  </g>
  <g transform="translate(128 914)" fill="none" stroke="url(#stroke)" stroke-width="3">
    <path d="M0 0h300"/>
  </g>
  <text x="1792" y="1032" text-anchor="end" font-family="Inter, DejaVu Sans, sans-serif" font-size="18" letter-spacing="5" fill="#6b778a">CORTE EDITOR</text>
</svg>
"""


def main() -> None:
    ICONS.mkdir(parents=True, exist_ok=True)
    BACKGROUNDS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "logo.svg").write_text(logo(), encoding="utf-8")
    for name, accent in ACCENTS.items():
        (ICONS / f"corte-{name}.svg").write_text(icon(name, accent), encoding="utf-8")
    for index in range(3):
        (BACKGROUNDS / f"corte-wallpaper-0{index + 1}.svg").write_text(
            wallpaper(index), encoding="utf-8"
        )
    print(f"Generados {len(ACCENTS)} iconos, 3 fondos y el logo en {ASSETS}")


if __name__ == "__main__":
    main()
