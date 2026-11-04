"""Branded, offline rendering of the shared query results."""
from __future__ import annotations

import math
import os
import textwrap
from datetime import UTC, date, datetime
from pathlib import Path

from .brand import get_brand

TITLES = {"steps": "Daily steps", "distance": "Daily distance", "sleep_duration": "Sleep duration",
          "resting_heart_rate": "Resting heart rate", "overnight_hrv": "Overnight HRV"}
# Shapes and words carry status independently of color. No error bodies are drawn.
STATUSES = {"error": ("x", "Failed refresh [×]"), "empty": ("s", "Empty response [□]"),
            "not_checked": ("|", "Not checked [|]"), "metric_not_returned": ("D", "Metric not returned [◇]"),
            "response_missing": ("+", "Response missing [+]")}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _day_label(day: str, *, year: bool = False) -> str:
    value = date.fromisoformat(day)
    return f"{MONTHS[value.month - 1]} {value.day}" + (f", {value.year}" if year else "")


def _period(first: str, last: str) -> str:
    a, b = date.fromisoformat(first), date.fromisoformat(last)
    if a == b:
        return _day_label(first, year=True)
    if a.year != b.year:
        return f"{_day_label(first, year=True)} – {_day_label(last, year=True)}"
    if a.month == b.month:
        return f"{MONTHS[a.month - 1]} {a.day}–{b.day}, {a.year}"
    return f"{_day_label(first)} – {_day_label(last)}, {a.year}"


def _date_groups(days: list[str], *, year: bool) -> str:
    groups = []
    start = previous = days[0]
    for day in days[1:]:
        if (date.fromisoformat(day) - date.fromisoformat(previous)).days == 1:
            previous = day
            continue
        groups.append((start, previous))
        start = previous = day
    groups.append((start, previous))
    return "; ".join(_day_label(a, year=year) if a == b else
                     f"{_day_label(a, year=year)}–{_day_label(b, year=year)}" for a, b in groups)


def _fetch_note(points: list[dict]) -> str:
    stamps = []
    for point in points:
        if point["status"] != "ok" or point["value"] is None or not point.get("fetched_at"):
            continue
        try:
            stamp = datetime.fromisoformat(point["fetched_at"])
            if stamp.tzinfo is not None:
                stamps.append(stamp.astimezone(UTC))
        except ValueError:
            pass
    if not stamps:
        return "Available-value fetch times unknown."
    first, last = min(stamps), max(stamps)
    label = first.strftime("%Y-%m-%d %H:%M")
    if first.strftime("%Y-%m-%d %H:%M") != last.strftime("%Y-%m-%d %H:%M"):
        label += " – " + last.strftime("%Y-%m-%d %H:%M")
    return "Values fetched: " + label + " UTC"


def build_trend_figure(result: dict, *, synthetic: bool = False, layout: str = "chat"):
    """Build a figure from a bounded get_trend result, preserving query semantics."""
    if layout not in {"chat", "wide"}:
        raise ValueError("Chart layout must be chat or wide")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.image import imread
    from matplotlib.ticker import MaxNLocator

    brand = get_brand()
    colors = brand["colors"]
    points = result["points"]
    metric = result["metric"]
    display = result.get("display")
    source_points = display["points"] if display else points
    unit = display["unit"] if display else result["unit"]
    values = [p["value"] if p["status"] == "ok" else None for p in points]
    if display:
        values = [s["value"] if v is not None else None for s, v in zip(source_points, values)]
    if metric == "sleep_duration":
        values = [v / 3600 if v is not None else None for v in values]
        unit = "hours"
    available = [v for v in values if v is not None]
    wide = layout == "wide"
    width = 10 if wide else 5.2
    text_width = 94 if wide else 40
    cross_year = result["from"][:4] != result["to"][:4]
    status_days: dict[str, list[str]] = {}
    for point in points:
        if point["status"] != "ok" or point["value"] is None:
            status_days.setdefault(point["status"], []).append(point["day"])
    notes = []
    for status, days in status_days.items():
        label = STATUSES.get(status, ("+", "Unavailable"))[1]
        notes.extend(textwrap.wrap(f"{label}: {_date_groups(days, year=cross_year)}", text_width))
    notes.extend(textwrap.wrap(_fetch_note(points), text_width))
    note_leading = .19 if wide else .25
    height = 6.9 + len(notes) * note_leading
    fig = Figure(figsize=(width, height), facecolor=colors["background"])
    FigureCanvasAgg(fig)

    def text(x, top, content, size=11, color=None, **kwargs):
        return fig.text(x / width, 1 - top / height, content, fontsize=size,
                        color=color or colors["ink"], fontfamily=brand["font"],
                        va="top", parse_math=False, **kwargs)

    left, right = .45, width - .45
    text(left, .26, "DAILY TREND", 9, colors["secondary"], weight="bold")
    if synthetic:
        text(right, .26, "SYNTHETIC DATA", 9, colors["primary"], ha="right", weight="bold",
             bbox={"boxstyle": "round,pad=.35", "facecolor": colors["tint"], "edgecolor": "none"})
    text(left, .67, TITLES[metric], 21 if wide else 19, weight="bold")
    text(left, 1.08, _period(result["from"], result["to"]), 12 if not wide else 11, colors["secondary"])
    if not available:
        summary = "No values"
    else:
        mean = sum(available) / len(available)
        if metric == "sleep_duration":
            minutes = round(mean * 60)
            summary = f"{minutes // 60}h {minutes % 60:02d}m"
        elif metric == "steps":
            summary = f"{mean:,.0f}"
        else:
            summary = f"{mean:,.1f} {unit}"
    noun = "nights" if metric == "sleep_duration" else "days"
    text(left, 1.57, summary, 34 if wide else 30, weight="bold")
    text(left, 2.16, f"Average · {len(available)} available {noun}" if available else "No average available",
         12 if not wide else 11, colors["secondary"])
    text(right, 1.67, f"{len(available)}/{len(points)}", 21, weight="bold", ha="right")
    text(right, 2.16, "Coverage", 12 if not wide else 11, colors["secondary"], ha="right")

    chart_top, chart_height = 2.87, 2.0
    plot_left, plot_right = .57, width - .62
    ax = fig.add_axes([plot_left / width, 1 - (chart_top + chart_height) / height,
                       (plot_right - plot_left) / width, chart_height / height])
    ax.set_facecolor(colors["background"])
    xs = list(range(len(points)))
    ys = [v if v is not None else math.nan for v in values]
    ax.set_xlim(-.5, len(points) - .5)
    bars = brand["charts"][metric] == "bar"
    if available:
        if bars:
            ax.bar(xs, ys, width=.65, color=colors["primary"], linewidth=0, zorder=3)
            zero_xs = [i for i, v in enumerate(values) if v == 0]
            ax.scatter(zero_xs, [0] * len(zero_xs), marker="o", s=12,
                       color=colors["primary"], clip_on=False, zorder=4)
            ax.set_ylim(0, max(max(available) * 1.15, 1))
        else:
            ax.plot(xs, ys, color=colors["primary"], linewidth=2.2, solid_capstyle="round",
                    solid_joinstyle="round")
            # Keep isolated measurements visible without a dot on every sample.
            dots = [i for i, v in enumerate(values) if v is not None and
                    (i == len(values) - 1 or ((i == 0 or values[i - 1] is None) and
                                            (i == len(values) - 1 or values[i + 1] is None)))]
            ax.scatter(dots, [values[i] for i in dots], s=22, color=colors["primary"],
                       edgecolor=colors["background"], linewidth=1, zorder=4)
            padding = max((max(available) - min(available)) * .2, abs(sum(available) / len(available)) * .04, .5)
            ax.set_ylim(max(0, min(available) - padding), max(available) + padding)
    else:
        ax.set_ylim(0, 1)
        ax.text(.5, .5, "No recorded values in this period", ha="center", va="center",
                transform=ax.transAxes, fontsize=12, color=colors["secondary"], fontfamily=brand["font"])
        ax.set_yticks([])
    if available:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=metric == "steps"))
    ax.yaxis.tick_right()
    ax.tick_params(axis="y", labelsize=11 if wide else 12, colors=colors["secondary"], length=0, pad=8)
    ax.set_xticks([])
    ax.set_axisbelow(True)
    ax.grid(axis="y", color=colors["rule"], linewidth=.7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    text(plot_right, chart_top - .28, unit, 10 if wide else 12, colors["secondary"], ha="right")

    # Status marks share the chart's date positions. The dated notes below give
    # exact dates even in a dense 90-day export; status never becomes a zero.
    strip_top = chart_top + chart_height + .12
    strip = fig.add_axes([plot_left / width, 1 - (strip_top + .2) / height,
                          (plot_right - plot_left) / width, .2 / height])
    strip.set_xlim(ax.get_xlim())
    strip.set_ylim(-1, 1)
    strip.set_yticks([])
    for spine in strip.spines.values():
        spine.set_visible(False)
    for i, point in enumerate(points):
        if values[i] is not None:
            strip.plot(i, 0, marker="o", markersize=2.5, color=colors["primary"])
        else:
            marker = STATUSES.get(point["status"], ("+", "Unavailable"))[0]
            strip.plot(i, 0, marker=marker, markersize=5, color=colors["ink"],
                       markerfacecolor="none", markeredgewidth=1)
    ticks = sorted({round(i * (len(points) - 1) / 4) for i in range(5)})
    strip.set_xticks(ticks, [_day_label(points[i]["day"]) for i in ticks])
    strip.tick_params(axis="x", labelsize=10 if wide else 12, colors=colors["secondary"], length=0, pad=8)
    footer_top = strip_top + .76
    text(left, footer_top, f"{len(available)} of {len(points)} {noun} available · Gaps are not zero", 10 if wide else 11,
         colors["secondary"])
    for i, line in enumerate(notes):
        text(left, footer_top + .27 + i * note_leading, line, 9 if wide else 11, colors["secondary"])
    source_top = footer_top + .34 + len(notes) * note_leading
    text(left, source_top, "Source: synthetic demo archive" if synthetic else "Source: local Garmin archive",
         9 if wide else 11, colors["secondary"])

    # Reuse the supplied icon PNG, cropping only its white canvas padding while
    # composing the chart. The authored logo geometry and colors stay intact.
    image = imread(brand["assets"]["icon_png"])
    nonwhite = (image[:, :, :3] < .98).any(axis=2)
    rows, cols = nonwhite.nonzero()
    image = image[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    logo = fig.add_axes([left / width, .16 / height, .43 / width, .31 / height])
    logo.imshow(image)
    logo.axis("off")
    text(left + .55, height - .38, brand["name"], 10, weight="bold")
    return fig


def render_trend(result: dict, output: Path, *, synthetic: bool = False, layout: str = "chat") -> None:
    if output.suffix.lower() != ".png":
        raise ValueError("Chart output must have a .png extension")
    fig = build_trend_figure(result, synthetic=synthetic, layout=layout)
    # Exclusive creation and private permissions protect existing outputs/archives.
    with open(output, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as target:
        fig.savefig(target, format="png", dpi=160, metadata={
            "Title": TITLES[result["metric"]],
            "Description": ("Synthetic data. " if synthetic else "") +
                           f"{result['from']} to {result['to']}; gaps are unavailable values.",
            "Software": "Garmin Data Workbench",
        })
