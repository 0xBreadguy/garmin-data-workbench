"""Branded, offline rendering of the shared query results."""
from __future__ import annotations

import math
import os
import textwrap
from datetime import date
from pathlib import Path

from .brand import get_brand
from .queries import METRIC_TITLES
from .sleep import STAGES

TITLES = {**METRIC_TITLES, "sleep": "Sleep overview"}
# Shapes and words carry status independently of color. No error bodies are drawn.
STATUSES = {"error": ("x", "Failed refresh [×]"), "empty": ("s", "Empty response [□]"),
            "not_checked": ("|", "Not checked [|]"), "metric_not_returned": ("D", "Metric not returned [◇]"),
            "response_missing": ("+", "Response missing [+]")}
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
# Neutral, not a chart value: unavailable dates must never read as a measurement.
GAP_SHADE = "#F3F5F8"


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


def _duration(hours: float) -> str:
    minutes = round(hours * 60)
    return f"{minutes // 60}h {minutes % 60:02d}m"


def _point_label(value: float, unit: str) -> str:
    if unit == "hours":
        return _duration(value)
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"


def _labeled_indices(values: list, slot: float, label_width: float, sparse_width: float | None = None) -> list[int]:
    """Label every value when all fit; otherwise the latest and the extremes that fit."""
    present = [i for i, value in enumerate(values) if value is not None]
    if not present or slot >= label_width + 2:
        return present
    chosen: list[int] = []
    for i in (present[-1], max(present, key=values.__getitem__), min(present, key=values.__getitem__)):
        if all(abs(i - j) * slot >= (sparse_width or label_width) + 2 for j in chosen):
            chosen.append(i)
    return sorted(chosen)


def _isolated_indices(values: list) -> list[int]:
    """Measurements with no neighbor to connect to, which a line alone would not draw."""
    return [i for i, value in enumerate(values) if value is not None and
            (i == 0 or values[i - 1] is None) and (i == len(values) - 1 or values[i + 1] is None)]


def _date_ticks(count: int, step: int) -> list[int]:
    """Space ticks evenly from the first date, always retaining the final date."""
    ticks = list(range(0, count, step))
    if ticks[-1] != count - 1:
        ticks = [i for i in ticks if i == 0 or count - 1 - i >= step * .6] + [count - 1]
    return ticks


def _date_labels(days: list[str], ticks: list[int], *, weekday: bool) -> list[str]:
    labels, month = [], None
    for i in ticks:
        value = date.fromisoformat(days[i])
        day = str(value.day) if weekday and value.month == month else _day_label(days[i])
        labels.append(f"{WEEKDAYS[value.weekday()]}\n{day}" if weekday else day)
        month = value.month
    return labels


def build_trend_figure(result: dict, *, synthetic: bool = False, layout: str = "chat", sleep_report: dict | None = None):
    """Build a figure from a bounded get_trend result, preserving query semantics."""
    if layout not in {"chat", "wide"}:
        raise ValueError("Chart layout must be chat or wide")
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.image import imread
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    from matplotlib.patheffects import withStroke
    from matplotlib.ticker import FuncFormatter, MaxNLocator

    synthetic = synthetic or bool(result.get("archive_provenance", {}).get("synthetic"))
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
    if unit in {"s", "min"}:
        divisor = 3600 if unit == "s" else 60
        values = [v / divisor if v is not None else None for v in values]
        unit = "hours"
    available = [v for v in values if v is not None]
    wide = layout == "wide"
    width = 10 if wide else 5.2
    text_width = 110 if wide else 48
    cross_year = result["from"][:4] != result["to"][:4]
    status_days: dict[str, list[str]] = {}
    for point in points:
        if point["status"] != "ok" or point["value"] is None:
            status_days.setdefault(point["status"], []).append(point["day"])
    notes = []
    for status, days in status_days.items():
        label = STATUSES.get(status, ("+", "Unavailable"))[1]
        notes.extend(textwrap.wrap(f"{label}: {_date_groups(days, year=cross_year)}", text_width))
    if sleep_report:
        for label, days in (
            ("Stages incomplete or inconsistent", [n["day"] for n in sleep_report["nights"]
                if n["values"]["sleep_duration"] is not None and not n["stages_complete"]]),
            ("Sleep score unavailable [○]", [n["day"] for n in sleep_report["nights"]
                if n["values"]["sleep_duration"] is not None and n["values"]["sleep_score"] is None]),
            ("Sleep need unavailable", [n["day"] for n in sleep_report["nights"]
                if n["values"]["sleep_duration"] is not None and n["values"].get("sleep_need") is None]),
        ):
            if days:
                notes.extend(textwrap.wrap(f"{label}: {_date_groups(days, year=cross_year)}", text_width))

    left, right = .45, width - .45
    plot_left, plot_right = left, width - (.86 if max(available, default=0) >= 1000 else .62)
    plot_width = plot_right - plot_left
    total_dates = len(points)
    slot = plot_width * 72 / total_dates  # Points available to each date.
    bar_share = min(.65, .5 * 72 / slot)  # Cap bar width so short ranges keep air between bars.
    bar_points = bar_share * slot
    tick_size = 10 if wide else 10.5
    label_size = 9
    weekday_dates = slot >= 40  # Room for "Fri / Apr 24" on every date.
    chart_height = 2.3 if wide else 2.0
    gaps = [i for i, value in enumerate(values) if value is None]

    nights = sleep_report["nights"] if sleep_report else []
    scores = [night["values"]["sleep_score"] for night in nights]
    needs = [night["values"].get("sleep_need") for night in nights]
    complete = [i for i, night in enumerate(nights) if night["stages_complete"]]
    total_only = [i for i in range(len(nights)) if values[i] is not None and not nights[i]["stages_complete"]]
    score_only_gaps = [i for i, value in enumerate(scores) if value is None and values[i] is not None]
    stages = [(label, colors["sleep_stages"][stage.removeprefix("sleep_")])
              for label, stage in zip(("Deep", "REM", "Light", "Unclassified"), STAGES)]
    stage_heights = [[nights[i]["values"][stage] / 3600 for i in complete] for stage in STAGES]
    handles = [Patch(facecolor=color, label=label) for (label, color), heights in zip(stages, stage_heights)
               if any(heights)] if sleep_report else []
    if total_only:
        handles.append(Patch(facecolor=colors["rule"], label="Total only"))
    if any(value is not None for value in needs):
        handles.append(Line2D([], [], linestyle="none", marker="_", markersize=11, markeredgewidth=1.8,
                              color=colors["ink"], label="Garmin need"))
    legend_rows = (2 if len(handles) > 4 and not wide else 1) if handles else 0

    section_top = 1.98
    if sleep_report:
        chart_top = section_top + .22 + legend_rows * .22 + .28  # Heading, legend, nightly value row.
        score_heading_top = chart_top + chart_height + .22
        score_top = score_heading_top + .36
        score_height = 1.15 if wide else 1.05
        plots_bottom = score_top + score_height + (.16 if score_only_gaps else 0)
    else:
        chart_top = section_top + .27
        plots_bottom = chart_top + chart_height
    strip_top = plots_bottom + .06
    strip_height = .2 if gaps else .01  # The strip only takes space when it has a date to report.
    notes_top = strip_top + strip_height + (.56 if weekday_dates else .38)
    note_leading = .19 if wide else .22
    footer_top = notes_top + len(notes) * note_leading + .1
    height = footer_top + .5

    fig = Figure(figsize=(width, height), facecolor=colors["background"])
    FigureCanvasAgg(fig)
    renderer = fig.canvas.get_renderer()
    halo = [withStroke(linewidth=2.5, foreground=colors["background"])]

    def text(x, top, content, size=11, color=None, **kwargs):
        kwargs.setdefault("va", "top")
        return fig.text(x / width, 1 - top / height, content, fontsize=size,
                        color=color or colors["ink"], fontfamily=brand["font"],
                        parse_math=False, **kwargs)

    def fit(label, inches):
        extent = label.get_window_extent(renderer).width / fig.dpi
        if extent > inches:
            label.set_fontsize(label.get_fontsize() * inches / extent)

    def plot_axes(top, plot_height):
        axis = fig.add_axes([plot_left / width, 1 - (top + plot_height) / height,
                             plot_width / width, plot_height / height])
        axis.set_facecolor(colors["background"])
        axis.yaxis.tick_right()
        axis.tick_params(axis="y", labelsize=tick_size, colors=colors["secondary"], length=0, pad=6)
        axis.set_xticks([])
        axis.set_axisbelow(True)
        axis.grid(axis="y", color=colors["rule"], linewidth=.7)
        for spine in axis.spines.values():
            spine.set_visible(False)
        return axis

    def shade(axis, indices):
        # Date runs share one band through every panel, so a gap never reads as a low value.
        runs: list[list[int]] = []
        for i in indices:
            if runs and runs[-1][1] == i - 1:
                runs[-1][1] = i
            else:
                runs.append([i, i])
        for first, last in runs:
            axis.fill_between([first - .5, last + .5], 0, 1, transform=axis.get_xaxis_transform(),
                              color=GAP_SHADE, linewidth=0, zorder=0)

    def label_width(series, value_unit):
        return max((len(_point_label(v, value_unit)) for v in series if v is not None), default=0) * label_size * .64

    def value_label(axis, i, y, content, *, offset=6, transform="data"):
        half = len(content) * label_size * .32
        align, nudge = "center", 0.
        if (i + .5) * slot < half:
            align, nudge = "left", -.4
        elif (total_dates - i - .5) * slot < half:
            align, nudge = "right", .4
        axis.annotate(content, (i + nudge, y), xycoords=transform, xytext=(0, offset),
                      textcoords="offset points", ha=align, va="bottom", fontsize=label_size,
                      color=colors["ink"], fontfamily=brand["font"], path_effects=halo,
                      annotation_clip=False, parse_math=False)

    fit(text(left, .38, TITLES["sleep"] if sleep_report else TITLES[metric], 21 if wide else 19, weight="bold"),
        right - left)
    text(left, .74, _period(result["from"], result["to"]), 11, colors["secondary"])
    if synthetic:
        text(right - .05, .74, "SYNTHETIC DATA", 8.5, colors["primary"], ha="right", weight="bold",
             bbox={"boxstyle": "round,pad=.35", "facecolor": colors["tint"], "edgecolor": "none"})
    if not available:
        summary = "No values"
    else:
        mean = sum(available) / len(available)
        if unit == "hours":
            summary = _duration(mean)
        elif metric == "steps":
            summary = f"{mean:,.0f}"
        elif metric in {"sleep_score", "sleep_stress"} or metric.startswith("body_battery_"):
            summary = f"{mean:,.1f}"
        else:
            summary = f"{mean:,.1f} {unit}"
    noun = ("night" if metric.startswith("sleep_") else "day") + ("" if len(available) == 1 else "s")
    fit(text(left, 1.06, summary, 34 if wide else 30, weight="bold"), right - left - 1.05)
    text(left, 1.6, f"Average · {len(available)} available {noun}" if available else "No average available",
         11, colors["secondary"])
    text(right, 1.22, f"{len(available)}/{len(points)}", 16, weight="bold", ha="right")
    text(right, 1.6, "Coverage", 11, colors["secondary"], ha="right")

    ax = plot_axes(chart_top, chart_height)
    xs = list(range(total_dates))
    ys = [v if v is not None else math.nan for v in values]
    ax.set_xlim(-.5, total_dates - .5)
    bars = brand["charts"].get(metric, "line") == "bar"
    if sleep_report:
        need_hours = [v / 60 if v is not None else None for v in needs]
        highest = max(available + [v for v in need_hours if v is not None], default=0)
        ax.set_ylim(0, max(highest * 1.06, 1))
        if available:
            # Bar tops already show total sleep. Only nights without a usable stage
            # breakdown draw it separately, as a capped column; stages are never inferred.
            line = ax.plot(xs, ys, linestyle="none", color=colors["ink"], label="Total", zorder=3)[0]
            if total_only:
                ax.vlines(total_only, 0, [values[i] for i in total_only], linewidth=bar_points,
                          color=colors["rule"], zorder=2)
                line.set(marker="_", markersize=bar_points, markeredgewidth=1.6, markevery=total_only)
        offsets = [0.] * len(complete)
        for (label, color), heights in zip(stages, stage_heights):
            if complete:
                ax.bar(complete, heights, bottom=offsets, width=bar_share, color=color,
                       edgecolor=colors["background"], linewidth=.9 if slot >= 12 else 0, zorder=2)
            offsets = [a + b for a, b in zip(offsets, heights)]
        if any(value is not None for value in needs):
            # One target tick per night: need is an estimate for that night, not a continuous curve.
            ax.plot(xs, [v if v is not None else math.nan for v in need_hours], linestyle="none", marker="_",
                    markersize=max(bar_points * 1.3, 3), markeredgewidth=1.8 if slot >= 14 else 1,
                    color=colors["ink"], label="Garmin need", zorder=4,
                    path_effects=[withStroke(linewidth=3.2, foreground=colors["background"])] if slot >= 14 else [])
        if handles:
            ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0, 1 + .27 / chart_height),
                      ncol=math.ceil(len(handles) / legend_rows), frameon=False, labelcolor=colors["secondary"],
                      prop={"family": brand["font"], "size": 9}, handlelength=1, handleheight=.8,
                      handletextpad=.5, columnspacing=1.2, borderpad=0, borderaxespad=0)
        # A row above the bars keeps labels clear of need ticks. Detached from their bars,
        # sparse labels say what they are; "high" and "low" carry no judgment.
        width_each = label_width(values, unit)
        labeled = _labeled_indices(values, slot, width_each, width_each + 7 * label_size * .64)
        latest = max((i for i, value in enumerate(values) if value is not None), default=None)
        for i in labeled:
            kind = "" if len(labeled) == len(available) else ("latest " if i == latest else
                                                              "high " if values[i] == max(available) else "low ")
            value_label(ax, i, 1, kind + _point_label(values[i], unit), offset=3, transform=ax.get_xaxis_transform())
        text(left, section_top, "Sleep by stage · hours", 11, weight="bold")
    elif available:
        if bars:
            ax.bar(xs, ys, width=bar_share, color=colors["primary"], linewidth=0, zorder=3)
            zero_xs = [i for i, v in enumerate(values) if v == 0]
            ax.scatter(zero_xs, [0] * len(zero_xs), marker="o", s=12,
                       color=colors["primary"], clip_on=False, zorder=4)
            ax.set_ylim(0, max(max(available) * 1.15, 1))
        else:
            ax.plot(xs, ys, color=colors["primary"], linewidth=2.2, solid_capstyle="round",
                    solid_joinstyle="round")
            # Mark every measurement when there is room; dense ranges keep isolated and final dots.
            isolated = _isolated_indices(values)
            dots = [i for i, v in enumerate(values) if v is not None and
                    (slot >= 14 or i == len(values) - 1 or i in isolated)]
            ax.scatter(dots, [values[i] for i in dots], s=30, color=colors["primary"],
                       edgecolor=colors["background"], linewidth=1, zorder=4)
            padding = max((max(available) - min(available)) * .2, abs(sum(available) / len(available)) * .04, .5)
            ax.set_ylim(max(0, min(available) - padding), max(available) + padding)
        for i in _labeled_indices(values, slot, label_width(values, unit)):
            value_label(ax, i, values[i], _point_label(values[i], unit), offset=3 if bars else 6)
    if metric in {"sleep_score", "sleep_stress", "body_battery_min", "body_battery_max", "body_battery_first", "body_battery_last"}:
        ax.set_ylim(0, 100)
    if available:
        ax.yaxis.set_major_locator(MaxNLocator(nbins=4, integer=metric == "steps" or bool(sleep_report)))
        if max(available) >= 1000:
            ax.yaxis.set_major_formatter(FuncFormatter(lambda tick, _: f"{tick:,.0f}"))
        if bars or sleep_report:
            ax.spines["bottom"].set(visible=True, color="#B8C2D0", linewidth=.8)
        shade(ax, gaps)
    else:
        if not sleep_report:
            ax.set_ylim(0, 1)
        ax.text(.5, .5, "No recorded values in this period", ha="center", va="center",
                transform=ax.transAxes, fontsize=12, color=colors["secondary"], fontfamily=brand["font"])
        ax.set_yticks([])
    if not sleep_report:
        text(right, chart_top - .24, unit, 10, colors["secondary"], ha="right")

    if sleep_report:
        score = plot_axes(score_top, score_height)
        score.set_xlim(ax.get_xlim())
        score.set_ylim(0, 100)
        score.set_yticks([0, 50, 100])
        recorded = sum(value is not None for value in scores)
        mean_score = sleep_report.get("coverage", {}).get("fields", {}).get("sleep_score", {}).get("mean_of_available_days")
        average = f" · avg {mean_score:.1f}" if recorded and mean_score is not None else ""
        text(left, score_heading_top, f"Sleep score · {recorded}/{len(points)} nights{average}", 11, weight="bold")
        if recorded:
            shade(score, [i for i, value in enumerate(scores) if value is None])
        score.plot(xs, [v if v is not None else math.nan for v in scores], color=colors["primary"],
                   linewidth=2, marker="o", markersize=6 if slot >= 14 else 4, markeredgecolor=colors["background"],
                   markeredgewidth=1 if slot >= 14 else 0, markevery=None if slot >= 14 else _isolated_indices(scores),
                   solid_capstyle="round", solid_joinstyle="round", zorder=3)
        for i in _labeled_indices(scores, slot, label_width(scores, "score")):
            value_label(score, i, scores[i], _point_label(scores[i], "score"), offset=5)
        # A hollow dot in a gutter under the axis: on the 0 gridline it would read as a score of zero.
        score.scatter(score_only_gaps, [-.1] * len(score_only_gaps), transform=score.get_xaxis_transform(),
                      marker="o", facecolor="none", edgecolor=colors["ink"], clip_on=False, s=20, linewidth=1)

    # Status marks share the chart's date positions and sit in the empty column. The
    # dated notes give exact dates in a dense 90-day export; a status never becomes a zero.
    strip = fig.add_axes([plot_left / width, 1 - (strip_top + strip_height) / height,
                          plot_width / width, strip_height / height])
    strip.set_xlim(ax.get_xlim())
    strip.set_ylim(-1, 1)
    strip.set_yticks([])
    for spine in strip.spines.values():
        spine.set_visible(False)
    for i in gaps:
        strip.plot(i, 0, marker=STATUSES.get(points[i]["status"], ("+", "Unavailable"))[0], markersize=6,
                   color=colors["ink"], markerfacecolor="none", markeredgewidth=1)
    strip.tick_params(axis="x", labelsize=tick_size, colors=colors["secondary"], length=0, pad=5)
    # Prefer every date with its weekday. Otherwise use the densest even step whose rendered
    # labels keep a clear gutter, always retaining both inclusive endpoints.
    days = [point["day"] for point in points]
    plans = [(1, True)] if weekday_dates else []
    plans += [(step, False) for step in (1, 2, 3, 7, 14, 30)] + [(max(total_dates - 1, 1), False)]
    for step, weekday in plans:
        ticks = _date_ticks(total_dates, step)
        strip.set_xticks(ticks, _date_labels(days, ticks, weekday=weekday), linespacing=1.25)
        labels = strip.get_xticklabels()
        if not weekday and len(labels) > 1:
            labels[0].set_ha("left")
            labels[-1].set_ha("right")
        bounds = [label.get_window_extent(renderer) for label in labels]
        clear = all(b.x0 - a.x1 >= 10.5 * fig.dpi / 72 for a, b in zip(bounds, bounds[1:]))
        if clear and (weekday or len(ticks) <= 8):
            break
    for i, line in enumerate(notes):
        text(left, notes_top + i * note_leading, line, 9 if wide else 10, colors["secondary"])

    # Reuse the supplied icon PNG, cropping only its white canvas padding while
    # composing the chart. The authored logo geometry and colors stay intact.
    image = imread(brand["assets"]["icon_png"])
    nonwhite = (image[:, :, :3] < .98).any(axis=2)
    rows, cols = nonwhite.nonzero()
    image = image[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
    logo = fig.add_axes([left / width, (height - footer_top - .28) / height, .4 / width, .28 / height])
    logo.imshow(image)
    logo.axis("off")
    text(left + .48, footer_top + .14, brand["name"], 9, va="center")
    return fig


def build_sleep_figure(result: dict, *, synthetic: bool = False, layout: str = "chat"):
    points = [{"day": n["day"], "value": n["values"]["sleep_duration"], "fetched_at": n["fetched_at"],
               "status": n["status"] if n["status"] != "ok" else
                   ("ok" if n["values"]["sleep_duration"] is not None else "metric_not_returned")}
              for n in result["nights"]]
    trend = {"archive_provenance": result.get("archive_provenance", {}), "metric": "sleep_duration", "unit": "s", "points": points, "from": result["from"], "to": result["to"]}
    return build_trend_figure(trend, synthetic=synthetic, layout=layout, sleep_report=result)


def render_png(result: dict, *, synthetic: bool = False, layout: str = "chat") -> tuple[bytes, dict]:
    """Render in memory for CLI and MCP, with bounded dimensions and PNG bytes."""
    from io import BytesIO
    from .chart_delivery import chart_metadata
    metadata = chart_metadata(result, synthetic=synthetic, layout=layout)
    sleep = result.get("dataset") == "sleep" and "nights" in result
    fig = (build_sleep_figure(result, synthetic=metadata['synthetic'], layout=layout) if sleep else
           build_trend_figure(result, synthetic=metadata['synthetic'], layout=layout))
    width, height = fig.get_size_inches()
    dpi = min(160, 1600 / width, 4096 / height)
    output = BytesIO()
    try:
        fig.savefig(output, format="png", dpi=dpi, metadata={
            "Title": metadata['title'], "Description": metadata['caption'],
            "Software": "Garmin Data Workbench"})
        if output.tell() > 4 * 1024 * 1024:
            raise ValueError('Chart exceeds the 4 MiB PNG limit; request a shorter range')
        return output.getvalue(), metadata
    finally:
        fig.clear()


def render_trend(result: dict, output: Path, *, synthetic: bool = False, layout: str = "chat") -> None:
    if output.suffix.lower() != ".png":
        raise ValueError("Chart output must have a .png extension")
    data, _ = render_png(result, synthetic=synthetic, layout=layout)
    # Exclusive creation and private permissions protect existing outputs/archives.
    with open(output, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as target:
        target.write(data)
