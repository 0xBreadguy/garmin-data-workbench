"""Render shared archive trends without network access."""
from __future__ import annotations

import os
from pathlib import Path


def render_trend(result: dict, output: Path) -> None:
    if output.suffix.lower() != ".png":
        raise ValueError("Chart output must have a .png extension")
    try:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
    except ImportError as error:
        raise ImportError("Charts require the optional charts extra; see docs/VISUALIZATION.md") from error

    points = result["points"]
    display = result.get("display")
    values = [p["value"] for p in (display["points"] if display else points)]
    unit = display["unit"] if display else result["unit"]
    if result["metric"] == "sleep_duration":
        values = [v / 3600 if v is not None else None for v in values]
        unit = "hours"
    fig = Figure(figsize=(10, 4.8), layout="constrained")
    FigureCanvasAgg(fig)
    ax = fig.subplots()
    x = list(range(len(points)))
    ax.plot(x, values, marker="o", markersize=3, color="#245e80", linewidth=1.6)
    ax.set_title(result["metric"].replace("_", " ").title(), loc="left")
    ax.set_ylabel(unit)
    ticks = sorted(set([0, len(points) // 2, len(points) - 1]))
    ax.set_xticks(ticks, [points[i]["day"] for i in ticks])
    ax.grid(axis="y", alpha=0.25)
    coverage = result["coverage"]
    statuses = ", ".join(f"{name}: {count}" for name, count in sorted(coverage["statuses"].items()))
    ax.set_xlabel(f"{coverage['days_with_value']}/{coverage['requested_days']} days with values · {statuses}\nGaps indicate unavailable values; source: local Garmin archive")
    # Exclusive creation avoids overwriting existing files, including the archive.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as target:
        fig.savefig(target, format="png", dpi=150)
