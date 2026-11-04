"""Shared brand settings; available without the optional chart dependencies."""
from __future__ import annotations

import json
from pathlib import Path


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
