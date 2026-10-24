import base64

from ui import theme as t


def as_img(svg: str, css: str = "") -> str:
    """Wraps an SVG drawing as an <img> so Streamlit displays it."""
    if "xmlns" not in svg:
        svg = svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1)
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img src="data:image/svg+xml;base64,{encoded}" style="{css}" alt="">'


def logo_svg(size: int = 34) -> str:
    return f"""<svg width="{size}" height="{size}" viewBox="0 0 34 34">
<rect width="34" height="34" rx="11" fill="{t.APRICOT}"/>
<path d="M8 25 V13 L17 8 L26 13 V25" fill="none" stroke="{t.NAVY}" stroke-width="2.2" stroke-linejoin="round"/>
<path d="M12 25 V16 M17 25 V16 M22 25 V16" stroke="{t.NAVY}" stroke-width="2.2" stroke-linecap="round"/>
</svg>"""


def hero_svg() -> str:
    """Three small businesses linked by AI agent nodes, with a rising growth path."""
    a, at, ground = t.APRICOT, t.APRICOT_TEXT, "#2A3D54"
    return f"""<svg viewBox="0 0 320 200" width="100%">
<path d="M20 176 Q 120 150 160 120 T 300 50" fill="none" stroke="{a}" stroke-width="2" stroke-dasharray="4 6" opacity="0.7"/>
<g fill="none" stroke="{at}" stroke-width="2" stroke-linejoin="round">
  <path d="M30 176 V128 L52 116 V128 L74 116 V128 L96 116 V176 Z"/>
  <rect x="40" y="146" width="12" height="12"/><rect x="62" y="146" width="12" height="12"/><path d="M84 100 V116"/>
  <rect x="132" y="96" width="56" height="80"/><path d="M128 96 L160 78 L192 96"/>
  <rect x="142" y="108" width="9" height="9"/><rect x="155" y="108" width="9" height="9"/><rect x="168" y="108" width="9" height="9"/>
  <rect x="142" y="126" width="9" height="9"/><rect x="155" y="126" width="9" height="9"/><rect x="168" y="126" width="9" height="9"/>
  <rect x="153" y="152" width="14" height="24"/>
  <rect x="226" y="132" width="62" height="40" rx="4"/><path d="M216 176 H298"/><path d="M240 146 H262 M240 156 H274"/>
</g>
<path d="M20 176 H300" stroke="{ground}" stroke-width="2"/>
<path d="M80 63 L153 46 M166 48 L251 102" stroke="{a}" stroke-width="1.5" opacity="0.6"/>
<circle cx="74" cy="66" r="7" fill="{a}"/><circle cx="160" cy="44" r="7" fill="{a}"/><circle cx="257" cy="106" r="7" fill="{a}"/>
</svg>"""


def sector_svg(sector: str, selected: bool) -> str:
    """A small line drawing for each application tile, chosen by sector."""
    n = t.NAVY
    s = sector.lower()
    if "manufactur" in s:
        sun = (158, 28)
        drawing = """<path d="M50 74 V44 L72 32 V44 L94 32 V44 L116 32 V74 Z"/><path d="M104 18 V32"/>
<rect x="62" y="56" width="10" height="10"/><rect x="84" y="56" width="10" height="10"/>"""
    elif "hospitality" in s or "hotel" in s:
        sun = (42, 26)
        drawing = """<rect x="76" y="30" width="48" height="44"/><path d="M72 30 L100 16 L128 30"/>
<rect x="84" y="38" width="8" height="8"/><rect x="96" y="38" width="8" height="8"/><rect x="108" y="38" width="8" height="8"/>
<rect x="94" y="56" width="12" height="18"/><path d="M140 74 V52 M134 58 Q140 44 146 58"/>"""
    elif "tech" in s:
        sun = (168, 22)
        drawing = """<rect x="68" y="32" width="64" height="38" rx="4"/><path d="M58 74 H142"/>
<path d="M80 44 H104 M80 54 H118"/><circle cx="122" cy="44" r="4"/>"""
    else:
        sun = (40, 28)
        drawing = """<rect x="80" y="24" width="40" height="50"/><path d="M88 34 H112 M88 44 H112 M88 54 H112"/>
<rect x="95" y="62" width="10" height="12"/>"""

    background = t.APRICOT if selected else t.APRICOT_SOFT
    sun_colour = t.APRICOT_SOFT if selected else t.APRICOT
    return f"""<svg viewBox="0 0 200 86" preserveAspectRatio="xMidYMid slice">
<rect width="200" height="86" fill="{background}"/>
<circle cx="{sun[0]}" cy="{sun[1]}" r="16" fill="{sun_colour}" opacity="0.5"/>
<g fill="none" stroke="{n}" stroke-width="2" stroke-linejoin="round">{drawing}</g>
<path d="M20 74 H180" stroke="{n}" stroke-width="2"/>
</svg>"""