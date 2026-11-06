"""Data-free, editable starting points for experimental agent-authored charts."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .brand import brand_tokens_canvas, brand_tokens_css, get_brand, inline_logo


def write_chart_kit(output: Path, host: str) -> dict:
    if host not in {"grok", "muse"}:
        raise ValueError("Chart kit host must be grok or muse.")
    output = output.expanduser().absolute()
    ui = Path(__file__).with_name("ui")
    starter = "starter.canvas.tsx" if host == "grok" else "starter.html"
    reference, reference_source = (("reference.canvas.tsx", "recovery.canvas.tsx") if host == "grok"
                                   else ("reference.js", "recovery.js"))
    source = (ui / starter).read_text(encoding="utf-8")
    source = source.replace("/*__BRAND_TOKENS__*/", brand_tokens_canvas(series=True)) if host == "grok" else source.replace(
        "/*__BRAND_CSS__*/", brand_tokens_css(series=True)).replace("<!--__LOGO__-->", inline_logo())
    brand = get_brand()
    logo = Path(brand["assets"]["logo_svg"]).read_bytes()
    brand["assets"] = {"logo_svg": "logo.svg"}
    files = {"RULES.md": (ui / "chart_rules.md").read_bytes(), starter: source.encode("utf-8"), reference: (ui / reference_source).read_bytes(),
             "brand.json": (json.dumps(brand, indent=2) + "\n").encode("utf-8"), "logo.svg": logo}
    output.mkdir(mode=0o700, exist_ok=False)
    for name, content in files.items():
        with open(output / name, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
            file.write(content)
    return {"host": host, "output_dir": str(output),
            "paths": {name: str(output / name) for name in files},
            "next_steps": ["Read RULES.md, query explicit dates, and build the chart the question needs.",
                           "Verify embedded data and layout by script against query JSON, then inspect native delivery."]}
