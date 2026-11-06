"""Shared brand settings; available without the optional chart dependencies."""
from __future__ import annotations

import json
import re
from pathlib import Path


def brand_tokens_css() -> str:
    """Theme-aware CSS properties for interactive views, derived only from brand.json."""
    brand = get_brand()
    light, dark = brand["colors"], brand["dark_colors"]
    tokens = {f"--brand-{name}": (light[name], dark[name])
              for name in ("primary", "ink", "background", "secondary", "rule", "tint")}
    tokens |= {f"--stage-{stage}": (light["sleep_stages"][stage], dark["sleep_stages"][stage])
               for stage in light["sleep_stages"]}
    tokens["--brand-ink-fill"] = (light["ink"], dark["ink_fill"])
    tokens["--brand-primary-fill"] = (light["primary"], light["primary"])
    return ":root{" + ";".join(f"{name}:light-dark({a},{b})" for name, (a, b) in tokens.items()) + "}"


def inline_logo() -> str:
    """The authored logo geometry and colors, decorative beside its adjacent wordmark."""
    source = Path(get_brand()["assets"]["logo_svg"]).read_text(encoding="utf-8")
    view_box = re.search(r'viewBox="([^"]+)"', source).group(1)
    paths = "".join(re.findall(r"<path\b[^>]*/>", source))
    return f'<svg class="logo" viewBox="{view_box}" aria-hidden="true" focusable="false">{paths}</svg>'


def brand_tokens_canvas() -> str:
    """The same tokens and logo as a literal for the native Grok Page, which has no stylesheet."""
    brand = get_brand()
    light, dark = brand["colors"], brand["dark_colors"]

    def tone(colors: dict, ink_fill: str) -> dict:
        stages = colors["sleep_stages"]
        return {"primary": colors["primary"], "ink": colors["ink"], "inkFill": ink_fill,
                "primaryFill": light["primary"], "background": colors["background"],
                "secondary": colors["secondary"], "rule": colors["rule"], "tint": colors["tint"],
                "stages": [stages[name] for name in ("deep", "rem", "light", "unmeasurable")]}

    source = Path(brand["assets"]["logo_svg"]).read_text(encoding="utf-8")
    jsx_names = {"d": "d", "fill": "fill", "stroke": "stroke",
                 "stroke-width": "strokeWidth", "stroke-linecap": "strokeLinecap"}
    paths = [{jsx_names[name]: value for name, value in re.findall(r'([a-z-]+)="([^"]*)"', tag)}
             for tag in re.findall(r"<path\b[^>]*/>", source)]
    logo = {"viewBox": re.search(r'viewBox="([^"]+)"', source).group(1), "paths": paths}
    return json.dumps({"light": tone(light, light["ink"]), "dark": tone(dark, dark["ink_fill"]), "logo": logo},
                      ensure_ascii=True, separators=(",", ":"))


def get_brand() -> dict:
    package = Path(__file__).resolve().parent
    # Wheel assets are copied from the repository's authoritative assets at build
    # time. Editable/source checkouts use those originals directly.
    assets = package / "brand_assets"
    if not assets.is_dir():
        assets = package.parents[1] / "assets"
    result = json.loads((package / "brand.json").read_text(encoding="utf-8"))
    result["assets"] = {name: str((assets / filename).resolve()) for name, filename in
                        (("logo_svg", "logo.svg"), ("icon_svg", "icon.svg"), ("icon_png", "icon.png"))}
    return result
