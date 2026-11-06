// Garmin Workbench native Page, renderer v2. Data is a fixed read-only snapshot.
// No network, host storage, metric aggregation, or archive access occurs here.
import { Page, Section, useState, useGrokTheme } from "grok/canvas";
import type { CSSProperties, ChangeEvent, PointerEvent, KeyboardEvent } from "grok/canvas";

type Metric = "sleep_duration" | "sleep_need" | "sleep_awake" | "sleep_score" | "overnight_hrv" | "resting_heart_rate" | "body_battery_charged";
type View = "trends" | "night" | "compare";
type Observation = { value: number | null; status: string; fetched_at: string | null };
type Night = { day: string; status: string; values: Record<string, number | null>; stages_complete: boolean; fetched_at: string | null; timing: Record<string, string | null> };
type Coverage = { days_with_value: number; requested_days: number };
type Period = { from: string; to: string; mean_of_available_days: number | null; coverage: Coverage; freshness: { oldest_available_fetch: string | null; newest_available_fetch: string | null } };
type Comparison = { baseline: Period; period: Period; change: { status: string; mean_difference: number | null }; warnings: string[] };
type Snapshot = { schema_version: number; report: { from: string; to: string; archive_provenance: { synthetic: boolean | null; freshness_meaning: string; [key: string]: unknown }; sleep: { nights: Night[] }; trends: Record<string, { points: (Observation & { day: string })[] }> }; comparison: { metrics: Record<string, Comparison> } | null };
type Row = { day: string; night: Night; values: Record<Metric, Observation>; stages: number[] | null };
type Tone = { motion?: string; primary: string; ink: string; inkFill: string; primaryFill: string; background: string; secondary: string; rule: string; tint: string; stages: string[] };
type LogoPath = { d: string; fill: string; stroke?: string; strokeWidth?: string; strokeLinecap?: "round" };
type Run = { start: string; end: string; points: { i: number; value: number }[] };
type Scrub = { onMouseDown: (e: { preventDefault(): void }) => void; onPointerDown: (e: PointerEvent<HTMLDivElement>) => void; onPointerMove: (e: PointerEvent<HTMLDivElement>) => void };
type PanelProps = { row: Row; p: Tone; select: (index: number, announce?: boolean) => void };
type LaneSpec = { metric: Metric; label: string; unit: string; noun: string; height: number };
type TextRef = number | null;
type PackedPeriod = [number, number, number | null, number, number, TextRef, TextRef];
type PackedNight = [number, number, boolean, TextRef, TextRef[], (number | null)[]];
type PackedPoint = [number, number | null, number, TextRef];
type PackedComparison = [PackedPeriod, PackedPeriod, number, number | null, number[]];
type PackedSnapshot = { codec_version: number; schema_version: number; strings: string[]; range: [number, number]; provenance: Snapshot["report"]["archive_provenance"]; nights: PackedNight[]; trends: PackedPoint[][]; comparison: PackedComparison[] | null };
// Codec v1 only restores field names and repeated strings; it calculates no metrics.
function decodeTransport(packet: PackedSnapshot): Snapshot {
  if (packet.codec_version !== 1 || packet.schema_version !== 1) throw new Error("Unsupported recovery transport version.");
  const text = (index: TextRef): string | null => index === null ? null : packet.strings[index];
  const sleep = ["sleep_duration", "sleep_need", "sleep_awake", "sleep_score", "sleep_deep", "sleep_light", "sleep_rem", "sleep_unmeasurable"];
  const trend = ["overnight_hrv", "resting_heart_rate", "body_battery_charged"];
  const comparison = ["sleep_duration", "overnight_hrv", "resting_heart_rate", "sleep_score", "body_battery_charged"];
  const period = (p: PackedPeriod): Period => ({ from: packet.strings[p[0]], to: packet.strings[p[1]], mean_of_available_days: p[2],
    coverage: { days_with_value: p[3], requested_days: p[4] }, freshness: { oldest_available_fetch: text(p[5]), newest_available_fetch: text(p[6]) } });
  return { schema_version: packet.schema_version, report: {
    from: packet.strings[packet.range[0]], to: packet.strings[packet.range[1]], archive_provenance: packet.provenance,
    sleep: { nights: packet.nights.map((n: PackedNight): Night => ({ day: packet.strings[n[0]], status: packet.strings[n[1]], stages_complete: n[2], fetched_at: text(n[3]),
      timing: Object.fromEntries(["start_utc", "end_utc", "start_local", "end_local"].map((key: string, i: number) => [key, text(n[4][i])])),
      values: Object.fromEntries(sleep.map((key: string, i: number) => [key, n[5][i]])) })) },
    trends: Object.fromEntries(trend.map((metric: string, i: number) => [metric, { points: packet.trends[i].map((p: PackedPoint) => ({ day: packet.strings[p[0]], value: p[1], status: packet.strings[p[2]], fetched_at: text(p[3]) })) }])) },
    comparison: packet.comparison === null ? null : { metrics: Object.fromEntries(comparison.map((metric: string, i: number) => { const c = packet.comparison![i];
      return [metric, { baseline: period(c[0]), period: period(c[1]), change: { status: packet.strings[c[2]], mean_difference: c[3] }, warnings: c[4].map((index: number) => packet.strings[index]) }]; })) } };
}
const snapshot = decodeTransport(/*__RECOVERY_SNAPSHOT__*/);
const brand: { light: Tone; dark: Tone; logo: { viewBox: string; paths: LogoPath[] } } = /*__BRAND_TOKENS__*/;
const ON_FILL = "#fff", ON_FILL_SOFT = "rgba(255,255,255,.82)", RING = "#438dff";
const FONT = 'ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue","DejaVu Sans",sans-serif';
// Same stage order and names as the PNG charts; the transport keeps its own field order.
const stageKeys = ["sleep_deep", "sleep_rem", "sleep_light", "sleep_unmeasurable"];
const stageNames = ["Deep", "REM", "Light", "Unclassified"];
const metrics: Metric[] = ["sleep_duration", "sleep_need", "sleep_awake", "sleep_score", "overnight_hrv", "resting_heart_rate", "body_battery_charged"];
const lanes: LaneSpec[] = [
  { metric: "sleep_duration", label: "Sleep & stages", unit: "hours", noun: "nights", height: 150 },
  { metric: "overnight_hrv", label: "Overnight HRV", unit: "ms", noun: "nights", height: 88 },
  { metric: "resting_heart_rate", label: "Resting heart rate", unit: "bpm", noun: "days", height: 88 },
  { metric: "sleep_score", label: "Sleep score", unit: "of 100", noun: "nights", height: 88 },
];
const compared: [Metric, string, string][] = [
  ["sleep_duration", "Sleep duration", "hours / minutes"], ["overnight_hrv", "Overnight HRV", "ms"], ["resting_heart_rate", "Resting heart rate", "bpm"],
  ["sleep_score", "Sleep score", "of 100"], ["body_battery_charged", "Body Battery charged", "points / day"],
];
// Same shapes as the PNG charts, so a gap's status never depends on color. Others use a dash.
const glyphs: Record<string, string> = { error: "×", empty: "□", not_checked: "|", metric_not_returned: "◇", response_missing: "+" };
// Plot insets shared by every lane and the scrubber. The scale sits on the right, as on the PNG charts.
const PLOT_LEFT = 20, PLOT_RIGHT = 48, DATE_AXIS = 22;
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const media = (query: string): boolean => typeof matchMedia === "function" && matchMedia(query).matches;
const coarse = media("(pointer: coarse)"), calm = media("(prefers-reduced-motion: reduce)");
const glide = (p: Tone, ...names: string[]): string => calm ? "none" : names.map((name: string) => `${name} ${p.motion}`).join(",");
const noSelect: CSSProperties = { userSelect: "none", WebkitUserSelect: "none", WebkitTouchCallout: "none", touchAction: "pan-y", cursor: "ew-resize" };
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const duration = (seconds: number): string => {
  const minutes = Math.round(Math.abs(seconds) / 60);
  return `${seconds < 0 ? "−" : ""}${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, "0")}m`;
};
const dateParts = (value: string): number[] => value.split("-").map(Number);
const shortDate = (value: string): string => { const d = dateParts(value); return `${MONTHS[d[1] - 1]} ${d[2]}`; };
// Only an exact UTC instant is reformatted. Anything else stays as the source returned it.
const stamp = (value: string): string => {
  const m = /^(\d{4})-(\d{2}-\d{2})T(\d{2}:\d{2})(:\d{2})?(?:\.\d+)?(?:\+00:00|Z)$/.exec(value);
  return m ? `${shortDate(`${m[1]}-${m[2]}`)}, ${m[1]}, ${m[3]}${m[4] && m[4] !== ":00" ? m[4] : ""} UTC` : value;
};
// Calendar arithmetic only: an associated date never passes through a time zone.
const dateLabel = (value: string): string => {
  const [y, m, d] = dateParts(value);
  const year = snapshot.report.from.slice(0, 4) !== snapshot.report.to.slice(0, 4) ? `, ${y}` : "";
  return `${DAYS[new Date(Date.UTC(y, m - 1, d)).getUTCDay()]}, ${MONTHS[m - 1]} ${d}${year}`;
};
// Same wording as the PNG charts' period label.
const periodLabel = (first: string, last: string): string => {
  const [ay, am, ad] = dateParts(first), [by, bm, bd] = dateParts(last);
  if (first === last) return `${MONTHS[am - 1]} ${ad}, ${ay}`;
  if (ay !== by) return `${MONTHS[am - 1]} ${ad}, ${ay} – ${MONTHS[bm - 1]} ${bd}, ${by}`;
  return am === bm ? `${MONTHS[am - 1]} ${ad}–${bd}, ${ay}` : `${MONTHS[am - 1]} ${ad} – ${MONTHS[bm - 1]} ${bd}, ${ay}`;
};
function format(metric: Metric, value: number | null): string {
  if (!finite(value)) return "Unavailable";
  if (metric === "sleep_duration" || metric === "sleep_awake") return duration(value);
  if (metric === "sleep_need") return duration(value * 60);
  return `${Number(value.toFixed(1))}${metric === "overnight_hrv" ? " ms" : metric === "resting_heart_rate" ? " bpm" : metric === "sleep_score" ? " / 100" : " points"}`;
}
function statusName(status: string): string {
  const names: Record<string, string> = { ok: "available", error: "failed refresh; retained values masked", empty: "empty response", not_checked: "not collected", response_missing: "response missing", metric_not_returned: "not returned or invalid" };
  return names[status] || "unavailable";
}
function projectRows(source: Snapshot): Row[] {
  return source.report.sleep.nights.map((night: Night): Row => {
    const values = {} as Record<Metric, Observation>;
    metrics.forEach((metric: Metric) => {
      const series = source.report.trends[metric];
      const point = series?.points.find((p: Observation & { day: string }) => p.day === night.day);
      const status = series ? (point?.status || "not_checked") : night.status;
      const raw = series ? point?.value : night.values[metric];
      const value = status === "ok" && finite(raw) ? raw : null;
      values[metric] = { value, status: status === "ok" && value === null ? "metric_not_returned" : status, fetched_at: series ? (point?.fetched_at || null) : night.fetched_at };
    });
    const rawStages = stageKeys.map((key: string) => night.values[key]);
    const stages = night.status === "ok" && night.stages_complete === true && rawStages.every((value: number | null) => finite(value) && value >= 0) ? rawStages as number[] : null;
    return { day: night.day, night, values, stages };
  });
}
const rows = projectRows(snapshot);
const fieldNames: Record<Metric, string> = { sleep_duration: "Sleep", sleep_need: "Garmin need", sleep_awake: "Awake", sleep_score: "Sleep score", overnight_hrv: "Overnight HRV", resting_heart_rate: "Resting heart rate", body_battery_charged: "Body Battery" };
// One line per status. `shown` metrics already state their own status beside the value.
function notes(row: Row, shown: Metric[] = []): string {
  const groups = new Map<string, string[]>();
  metrics.filter((m: Metric) => row.values[m].value === null && !shown.includes(m)).forEach((m: Metric) => {
    const status = statusName(row.values[m].status);
    groups.set(status, [...(groups.get(status) || []), fieldNames[m]]);
  });
  const out = Array.from(groups).map(([status, names]: [string, string[]]) => `${names.join(", ")}: ${status}`);
  if (row.values.sleep_duration.value !== null && !row.stages) out.push("Incomplete or inconsistent stages; total sleep only");
  return out.length ? out.join(" · ") : `Stages exclude awake time and naps.${shown.length ? "" : " Daily Body Battery charge is not attributed solely to sleep."}`;
}
function valueAt(row: Row, metric: Metric): number | null {
  const value = row.values[metric].value;
  return value === null ? null : metric === "sleep_duration" ? value / 3600 : metric === "sleep_need" ? value / 60 : value;
}
// Nulls split geometry, including a missing first/last day. Singleton runs keep a marker.
function segments(data: Row[], metric: Metric): Run[] {
  const result: Run[] = [];
  let run: Run | null = null;
  data.forEach((row: Row, i: number) => {
    const value = valueAt(row, metric);
    if (value === null) { run = null; return; }
    if (!run) { run = { start: row.day, end: row.day, points: [] }; result.push(run); }
    run.end = row.day; run.points.push({ i, value });
  });
  return result;
}
// A one-point path paints nothing, so a lone observation gets a zero-length segment with a round cap.
function trace(run: Run, n: number, y: (v: number) => number): string {
  const at = (point: { i: number; value: number }): string => `${share(point.i, n)},${y(point.value)}`;
  return run.points.map((point: { i: number; value: number }, j: number) => `${j ? "L" : "M"}${at(point)}`).join(" ") + (run.points.length === 1 ? ` L${at(run.points[0])}` : "");
}
// Marks never change with the selection, so React can skip them while the overlay moves.
const built = new Map<string, unknown>();
function once<T>(key: string, build: () => T): T {
  if (!built.has(key)) built.set(key, build());
  return built.get(key) as T;
}
const share = (i: number, n: number): number => n < 2 ? 50 : Number((i / (n - 1) * 100).toFixed(3));
const barWidth = (n: number): string => `min(24px, ${Number(((n > 1 ? 100 / (n - 1) : 100) * 0.62).toFixed(3))}%)`;
function niceTicks(low: number, high: number, count: number): number[] {
  const raw = (high - low) / count, power = Math.pow(10, Math.floor(Math.log10(raw))), error = raw / power;
  const step = (error >= 7.07 ? 10 : error >= 3.16 ? 5 : error >= 1.41 ? 2 : 1) * power, out: number[] = [];
  for (let t = Math.ceil(low / step); t * step <= high; t++) out.push(t * step);
  return out;
}
function scale(data: Row[], spec: LaneSpec): { y: (v: number) => number; ticks: number[]; bottom: number; height: number } {
  const isSleep = spec.metric === "sleep_duration", values = data.map((r: Row) => valueAt(r, spec.metric)).filter(finite);
  let low = 0, high = 100;
  if (isSleep) high = Math.max(1, Math.ceil(Math.max(0, ...values, ...data.map((r: Row) => valueAt(r, "sleep_need")).filter(finite)) + 0.4));
  else if (spec.metric !== "sleep_score" && values.length) { low = Math.max(0, Math.floor(Math.min(...values) / 5) * 5 - 5); high = Math.ceil(Math.max(...values) / 5) * 5 + 5; }
  const top = 6, bottom = spec.height - 4;
  return { y: (v: number) => Number((bottom - (v - low) / (high - low) * (bottom - top)).toFixed(2)), bottom, height: spec.height,
    ticks: spec.metric === "sleep_score" ? [0, 50, 100] : niceTicks(low, high, isSleep ? 3 : 2) };
}
const note = (p: Tone): CSSProperties => ({ margin: "10px 0 0", color: p.secondary, fontSize: 12 });
const fold = (p: Tone): CSSProperties => ({ marginTop: 14, color: p.secondary, fontSize: 12 });
const swatch = (color: string) => <i style={{ display: "inline-block", flex: "none", width: 8, height: 8, borderRadius: 2, background: color }} />;
const tail = (left: boolean, color: string) => <span aria-hidden="true" style={{ position: "absolute", bottom: -11, ...(left ? { left: 28 } : { right: 28 }), width: 20, height: 12, background: color, clipPath: left ? "polygon(0 0,100% 0,8% 100%,0 80%)" : "polygon(0 0,100% 0,100% 80%,92% 100%)" }} />;
const control = (p: Tone, extra: CSSProperties = {}): CSSProperties => ({ minHeight: coarse ? 44 : 38, padding: "8px 12px", border: `1px solid ${p.rule}`, borderRadius: 10, background: "transparent", color: p.ink, fontWeight: 550, ...extra });
type ButtonProps = { label: string; style: CSSProperties; hover?: CSSProperties; id?: string; role?: string; tabIndex?: number; disabled?: boolean; onClick: (e: { currentTarget: HTMLButtonElement }) => void; onKeyDown?: (e: KeyboardEvent<HTMLButtonElement>) => void; "aria-label"?: string; "aria-pressed"?: boolean; "aria-selected"?: boolean; "aria-controls"?: string };
function Button({ label, style, hover, ...rest }: ButtonProps) {
  const [over, setOver] = useState(false);
  const [ring, setRing] = useState(false);
  return <button type="button" {...rest} style={{ font: "inherit", cursor: rest.disabled ? "default" : "pointer", opacity: rest.disabled ? 0.5 : 1, ...style, ...(over && !rest.disabled ? hover : {}), ...(ring ? { outline: `2px solid ${RING}`, outlineOffset: 3 } : {}) }}
    onPointerEnter={(e: PointerEvent<HTMLButtonElement>) => { if (e.pointerType === "mouse") setOver(true); }} onPointerLeave={() => setOver(false)}
    onFocus={(e: { currentTarget: HTMLButtonElement }) => setRing(e.currentTarget.matches(":focus-visible"))} onBlur={() => setRing(false)}>{label}</button>;
}
function laneMarks(data: Row[], spec: LaneSpec, p: Tone) {
  const isSleep = spec.metric === "sleep_duration", n = data.length;
  const { y, ticks, bottom, height: plot } = scale(data, spec);
  const showDates = spec === lanes[lanes.length - 1], height = plot + (showDates ? DATE_AXIS : 0);
  const left = (i: number): string => `${share(i, n)}%`;
  const column = (i: number): CSSProperties => ({ position: "absolute", left: left(i), width: barWidth(n), transform: "translateX(-50%)" });
  const glyph = (r: Row, i: number) => <span key={r.day} data-missing-day={r.day} style={{ position: "absolute", left: left(i), top: bottom - 16, transform: "translateX(-50%)", color: p.ink, fontSize: 12, fontWeight: 700, lineHeight: "14px" }}>{glyphs[r.values[spec.metric].status] || "—"}</span>;
  const series = (metric: Metric, stroke: string, width: number, dash?: string) => segments(data, metric).map((run: Run) => <path key={`${metric}-${run.start}`} data-series={metric} data-start-date={run.start} data-end-date={run.end}
    d={trace(run, n, y)}
    fill="none" stroke={stroke} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" strokeDasharray={dash} vectorEffect="non-scaling-stroke" />);
  const dots = isSleep ? [] : segments(data, spec.metric).filter((run: Run) => n <= 31 || run.points.length === 1).flatMap((run: Run) => run.points.map((point: { i: number; value: number }) =>
    <circle key={data[point.i].day} data-day={data[point.i].day} data-value={point.value} cx={left(point.i)} cy={y(point.value)} r={2.75} fill={p.primary} stroke={p.background} strokeWidth={1} />));
  const bars = !isSleep ? data.map((r: Row, i: number) => r.values[spec.metric].value === null ? glyph(r, i) : null) : data.map((r: Row, i: number) => {
    const total = valueAt(r, "sleep_duration");
    if (total === null) return glyph(r, i);
    if (total === 0) return <div key={r.day} data-day={r.day} data-value={0} style={{ ...column(i), top: bottom - 1.5, height: 1.5, background: p.secondary }} />;
    const box: CSSProperties = { ...column(i), top: y(total), height: bottom - y(total), borderRadius: "4px 4px 0 0", overflow: "hidden" };
    if (!r.stages) return <div key={r.day} data-day={r.day} data-value={total} style={{ ...box, background: p.secondary, opacity: 0.45 }} />;
    return <div key={r.day} data-day={r.day} data-value={total} style={{ ...box, display: "flex", flexDirection: "column-reverse", gap: n <= 30 ? 2 : 0 }}>{r.stages.map((seconds: number, k: number) => seconds > 0 ? <div key={stageKeys[k]} data-stage={stageKeys[k]} style={{ flex: `${seconds} 1 0`, minHeight: 1, background: p.stages[k] }} /> : null)}</div>;
  });
  const grid = <div aria-hidden="true" style={{ position: "absolute", inset: 0 }}>{ticks.map((t: number) => <div key={t}><div style={{ position: "absolute", left: -PLOT_LEFT, right: 30 - PLOT_RIGHT, top: y(t), height: 1, background: p.rule }} /><span style={{ position: "absolute", right: -PLOT_RIGHT, top: y(t) - 8, color: p.secondary, fontSize: 11, lineHeight: "16px" }}>{t}</span></div>)}</div>;
  const plotted = <div aria-hidden="true" style={{ position: "absolute", inset: 0 }}>
    {bars}
    <svg width="100%" height={plot} style={{ position: "absolute", left: 0, top: 0, display: "block", overflow: "visible" }}>
      <svg viewBox={`0 0 100 ${plot}`} preserveAspectRatio="none" width="100%" height={plot} style={{ overflow: "visible" }}>{isSleep ? series("sleep_need", p.ink, 1.75, ".1 4.5") : series(spec.metric, p.primary, 2.25)}</svg>
      {dots}
    </svg>
    {!data.some((r: Row) => valueAt(r, spec.metric) !== null) && <span style={{ position: "absolute", left: "50%", top: 18, transform: "translateX(-50%)", color: p.secondary, fontSize: 11, whiteSpace: "nowrap" }}>No observations</span>}
    {showDates && Array.from(new Set([0, Math.round((n - 1) / 3), Math.round((n - 1) * 2 / 3), n - 1])).map((j: number) => <span key={j} style={{ position: "absolute", left: left(j), top: height - 20, transform: "translateX(-50%)", color: p.secondary, fontSize: 11, lineHeight: "16px", whiteSpace: "nowrap" }}>{shortDate(data[j].day)}</span>)}
  </div>;
  return { grid, plotted, y, bottom, height };
}
function Lane({ data, spec, row, p, dark, scrub }: { data: Row[]; spec: LaneSpec; row: Row; p: Tone; dark: boolean; scrub: Scrub }) {
  const isSleep = spec.metric === "sleep_duration", n = data.length;
  const { grid, plotted, y, bottom, height } = once(`${spec.metric}|${data[0].day}|${dark}`, () => laneMarks(data, spec, p));
  const at = `${share(data.findIndex((r: Row) => r.day === row.day), n)}%`, value = isSleep ? null : valueAt(row, spec.metric);
  return <section style={{ marginTop: 10, paddingTop: 10, borderTop: `1px solid ${p.rule}` }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
      <div role="heading" aria-level={3} style={{ color: p.ink, fontSize: 14, fontWeight: 650 }}>{spec.label}<span style={{ display: "block", marginTop: 1, color: p.secondary, fontSize: 11, fontWeight: 400 }}>{spec.unit} · {data.filter((r: Row) => r.values[spec.metric].value !== null).length}/{n} {spec.noun}</span></div>
      <span data-testid={`value-${spec.metric}`} style={{ flex: "none", color: p.ink, fontSize: 16, fontWeight: 700 }}>{format(spec.metric, row.values[spec.metric].value)}</span>
    </div>
    {isSleep && <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", marginTop: 6, color: p.secondary, fontSize: 11 }}>
      {stageNames.map((name: string, i: number) => <span key={name} data-legend-stage={name} style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>{swatch(p.stages[i])}{name}</span>)}
      <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}><svg aria-hidden="true" width={14} height={2} style={{ flex: "none" }}><line x1={1} x2={13} y1={1} y2={1} stroke={p.ink} strokeWidth={2} strokeLinecap="round" strokeDasharray=".1 4.5" /></svg>Garmin need</span>
      {data.some((r: Row) => !!r.values.sleep_duration.value && !r.stages) && <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>{swatch(p.secondary)}Total only</span>}
    </div>}
    <div data-testid={`lane-${spec.metric}`} data-selected-date={row.day} role="img" aria-label={`${spec.label} by calendar date. Use the selected-night slider for keyboard inspection.`} {...scrub} style={{ ...noSelect, position: "relative", marginTop: 6, height }}>
      <div style={{ position: "absolute", top: 0, bottom: 0, left: PLOT_LEFT, right: PLOT_RIGHT }}>
        {grid}
        <div aria-hidden="true" style={{ position: "absolute", left: at, top: 4, height: bottom - 4, width: `calc(${barWidth(n)} + 8px)`, minWidth: 16, transform: "translateX(-50%)", borderRadius: 6, background: p.primary, opacity: 0.12, transition: glide(p, "left") }} />
        {plotted}
        <svg aria-hidden="true" data-selected-marker={row.day} width={1} height={bottom - 4} style={{ position: "absolute", left: at, top: 4, transition: glide(p, "left") }}><line x1={0.5} x2={0.5} y1={0} y2={bottom - 4} stroke={p.ink} strokeOpacity={0.4} /></svg>
        {value !== null && <div aria-hidden="true" style={{ position: "absolute", left: at, top: y(value), width: 11, height: 11, boxSizing: "border-box", transform: "translate(-50%,-50%)", borderRadius: "50%", background: p.primary, border: `2px solid ${p.background}`, transition: glide(p, "left", "top") }} />}
      </div>
    </div>
  </section>;
}
function Scrubber({ data, row, value, low, high, p, scrub, onSelect }: { data: Row[]; row: Row; value: number; low: number; high: number; p: Tone; scrub: Scrub; onSelect: (index: number) => void }) {
  const [ring, setRing] = useState(false);
  const at = share(data.findIndex((r: Row) => r.day === row.day), data.length);
  const span = `calc(${PLOT_LEFT}px + ${at / 100} * (100% - ${PLOT_LEFT + PLOT_RIGHT}px))`;
  return <div data-testid="scrubber" {...scrub} style={{ ...noSelect, position: "relative", paddingTop: 32 }}>
    <span aria-hidden="true" data-testid="scrub-bubble" style={{ position: "absolute", top: 0, left: `clamp(34px, ${span}, calc(100% - 34px))`, transform: "translateX(-50%)", padding: "3px 10px", borderRadius: 9, background: p.inkFill, color: ON_FILL, fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", transition: glide(p, "left") }}>{shortDate(row.day)}</span>
    <i aria-hidden="true" style={{ position: "absolute", top: 24, left: span, marginLeft: -1, width: 10, height: 7, background: p.inkFill, clipPath: "polygon(0 0,100% 0,0 100%)", transition: glide(p, "left") }} />
    <div style={{ position: "relative", height: coarse ? 44 : 26, margin: `0 ${PLOT_RIGHT}px 0 ${PLOT_LEFT}px` }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: "50%", marginTop: -2, height: 4, borderRadius: 4, background: p.rule }} />
      <div data-testid="scrub-thumb" style={{ position: "absolute", left: `${at}%`, top: "50%", width: 22, height: 22, boxSizing: "border-box", transform: "translate(-50%,-50%)", borderRadius: "50%", border: `3px solid ${p.background}`, background: p.primaryFill, boxShadow: ring ? `0 0 0 2px ${RING}` : "none", transition: glide(p, "left") }} />
      <input id="day-range" type="range" min={low} max={high} step={1} value={value} aria-label="Inspect a night. Arrow keys move between dates." aria-valuetext={`${dateLabel(row.day)}, sleep ${format("sleep_duration", row.values.sleep_duration.value)}, HRV ${format("overnight_hrv", row.values.overnight_hrv.value)}`}
        onChange={(e: ChangeEvent<HTMLInputElement>) => onSelect(Number(e.currentTarget.value))} onFocus={(e: { currentTarget: HTMLInputElement }) => setRing(e.currentTarget.matches(":focus-visible"))} onBlur={() => setRing(false)}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%", margin: 0, opacity: 0, pointerEvents: "none" }} />
    </div>
  </div>;
}
function Hero({ data, row, p, dark, scrub, onLeave }: { data: Row[]; row: Row; p: Tone; dark: boolean; scrub: Scrub; onLeave: (e: PointerEvent<HTMLDivElement>) => void }) {
  const line = once(`hero|${data[0].day}|${dark}`, () => {
    const seconds = data.map((r: Row) => r.values.sleep_duration.value).filter(finite), low = Math.min(...seconds), high = Math.max(...seconds), tall = 54;
    const y = (v: number): number => high > low ? Number((tall - 6 - (v - low) / (high - low) * (tall - 14)).toFixed(2)) : tall / 2;
    const runs = segments(data, "sleep_duration"), d = runs.map((run: Run) => trace(run, data.length, (hours: number) => y(hours * 3600))).join(" ");
    return { y, count: seconds.length, range: seconds.length > 1 ? `Total sleep · range ${duration(low)}–${duration(high)}` : "Total sleep",
      svg: <svg aria-hidden="true" width="100%" height={tall} style={{ position: "absolute", inset: 0, display: "block", overflow: "visible" }}>
        <svg viewBox={`0 0 100 ${tall}`} preserveAspectRatio="none" width="100%" height={tall} style={{ overflow: "visible" }}><path data-testid="hero-path" d={d} fill="none" stroke={ON_FILL} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke" /></svg>
        {runs.filter((run: Run) => run.points.length === 1).map((run: Run) => <circle key={run.start} data-lone-night={run.start} cx={`${share(run.points[0].i, data.length)}%`} cy={y(run.points[0].value * 3600)} r={3} fill={ON_FILL} />)}
      </svg> };
  });
  const seconds = row.values.sleep_duration.value, at = `${share(data.findIndex((r: Row) => r.day === row.day), data.length)}%`;
  return <section data-testid="hero" aria-label="Selected night" style={{ position: "relative", isolation: "isolate", margin: "18px 0 6px", padding: "0 22px 44px 0", userSelect: "none", WebkitUserSelect: "none", WebkitTouchCallout: "none" }}>
    <div style={{ position: "absolute", zIndex: -1, top: 30, right: 0, bottom: 12, left: "24%", display: "flex", alignItems: "flex-end", justifyContent: "flex-end", padding: "0 18px 7px", borderRadius: 24, background: p.primaryFill, color: ON_FILL }}>
      <div style={{ fontSize: 12 }}>Garmin need <b data-testid="hero-need" style={{ marginLeft: 4, fontSize: 14, fontWeight: 700 }}>{format("sleep_need", row.values.sleep_need.value)}</b></div>
      {tail(false, p.primaryFill)}
    </div>
    <div style={{ position: "relative", padding: "16px 18px 66px", borderRadius: 24, background: p.inkFill, color: ON_FILL }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div data-testid="selected-date" data-date={row.day} style={{ fontSize: 13, fontWeight: 600 }}>{dateLabel(row.day)}</div>
          <div data-testid="hero-sleep" style={{ margin: "2px 0 0", fontSize: "clamp(40px,13vw,52px)", fontWeight: 700, lineHeight: 1.05, letterSpacing: "-.03em" }}>{seconds === null ? <span style={{ fontSize: 28, letterSpacing: "-.01em" }}>Unavailable</span> : format("sleep_duration", seconds)}</div>
        </div>
        <div style={{ flex: "none", textAlign: "right", color: ON_FILL_SOFT, fontSize: 11 }}><b style={{ display: "block", color: ON_FILL, fontSize: 22, fontWeight: 700, lineHeight: 1.2 }}>{line.count}/{data.length}</b>Coverage</div>
      </div>
      <div style={{ margin: "2px 0 0", color: ON_FILL_SOFT, fontSize: 12 }}>{line.range}</div>
      {tail(true, p.inkFill)}
    </div>
    <div {...scrub} onPointerLeave={onLeave} style={{ ...noSelect, position: "absolute", bottom: 50, left: 26, right: 14, height: 54 }}>
      {line.svg}
      {seconds !== null && <div aria-hidden="true" data-testid="hero-dot" style={{ position: "absolute", left: at, top: line.y(seconds), width: 14, height: 14, transform: "translate(-50%,-50%)", borderRadius: "50%", background: p.primaryFill, transition: glide(p, "left", "top") }}><svg width={14} height={14} style={{ display: "block" }}><circle cx={7} cy={7} r={4} fill={ON_FILL} /></svg></div>}
    </div>
  </section>;
}
function StageDetail({ row, p }: { row: Row; p: Tone }) {
  if (!row.stages) return <div data-testid="stage-unavailable" style={{ marginTop: 12, padding: "12px 14px", borderRadius: 12, background: p.tint, color: p.ink, fontSize: 12 }}>{row.values.sleep_duration.value === null ? "No available sleep duration. No stage proportions are inferred." : "Total sleep is available; the stage breakdown is incomplete or inconsistent. No stage proportions are inferred."}</div>;
  const stages = row.stages;
  return <div data-testid="stage-detail">
    <div role="img" aria-label={`Sleep stage composition: ${stages.map((v: number, i: number) => `${stageNames[i]} ${duration(v)}`).join(", ")}`} style={{ display: "flex", gap: 2, height: 14, margin: "14px 0 10px" }}>{stages.map((v: number, i: number) => v > 0 ? <span key={stageKeys[i]} style={{ flex: `${v} 1 0`, minWidth: 2, borderRadius: 4, background: p.stages[i] }} /> : null)}</div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(145px,1fr))", gap: "6px 18px", fontSize: 12 }}>{stages.map((v: number, i: number) => <span key={stageKeys[i]} style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0, color: p.secondary }}>{swatch(p.stages[i])}{stageNames[i]}<b style={{ color: p.ink, fontWeight: 650, whiteSpace: "nowrap" }}>{duration(v)}</b></span>)}</div>
  </div>;
}
// Row label and shared explanation for a query warning, so one sentence is not repeated per metric.
function warningText(warning: string): [string, string] {
  if (warning.endsWith("_incomplete_coverage")) return ["Incomplete coverage", "Incomplete coverage: compare with care."];
  if (warning.endsWith("_includes_today_or_future")) return ["Includes today or future dates", "Today or future dates: observations may still change."];
  if (warning === "unequal_period_lengths") return ["", "The periods contain different numbers of dates."];
  return [warning.replaceAll("_", " "), ""];
}
function ComparisonView({ p }: { p: Tone }) {
  const help: CSSProperties = { margin: "12px 0", color: p.secondary, fontSize: 12 };
  if (!snapshot.comparison) return <div data-testid="comparison-unavailable" style={help}>Load at least two dates to compare earlier and later periods.</div>;
  const table = snapshot.comparison.metrics, first = table.sleep_duration, period: CSSProperties = { position: "relative", padding: "12px 14px 13px", borderRadius: 24, color: ON_FILL, fontSize: 12 };
  const figure: CSSProperties = { display: "block", marginTop: 1, fontSize: "clamp(13px,4vw,14px)", fontWeight: 700 };
  const row: CSSProperties = { display: "grid", gridTemplateColumns: "minmax(0,36fr) repeat(3,minmax(0,21.33fr))" };
  const heading: CSSProperties = { padding: "8px 4px", color: p.secondary, fontSize: 11, fontWeight: 500, textAlign: "right" };
  const cell: CSSProperties = { padding: "12px 4px", color: p.ink, fontSize: "clamp(12px,3.6vw,13px)", fontWeight: 600, textAlign: "right" };
  const small: CSSProperties = { display: "block", marginTop: 2, color: p.secondary, fontSize: 11, fontWeight: 400 };
  const shared = Array.from(new Set(compared.flatMap(([metric]: [Metric, string, string]) => table[metric].warnings.map((warning: string) => warningText(warning)[1])))).filter(Boolean);
  return <div data-testid="comparison">
    <div style={help}>The loaded dates are split into earlier and later periods. Ask Grok for other dates.</div>
    <div style={{ position: "relative", isolation: "isolate", display: "grid", gridTemplateColumns: "1fr 1fr", margin: "18px 0 24px" }}>
      <div style={{ ...period, background: p.inkFill }}>Earlier<b style={figure}>{periodLabel(first.baseline.from, first.baseline.to)}</b>{tail(true, p.inkFill)}</div>
      <div style={{ ...period, zIndex: -1, margin: "14px 0 0 -18px", paddingLeft: 32, textAlign: "right", background: p.primaryFill }}>Later<b style={figure}>{periodLabel(first.period.from, first.period.to)}</b>{tail(false, p.primaryFill)}</div>
    </div>
    <div style={help}>{snapshot.report.archive_provenance.synthetic ? "Synthetic data." : "Unmarked archive provenance."} Available-day means; later minus earlier. Each metric keeps its own denominator.</div>
    <div role="table" aria-label="Earlier and later period means">
      <div role="row" style={{ ...row, borderBottom: `1px solid ${p.rule}` }}>{["Metric", "Earlier", "Later", "Change"].map((name: string, i: number) => <span key={name} role="columnheader" style={{ ...heading, textAlign: i ? "right" : "left" }}>{name}</span>)}</div>
      {compared.map(([metric, name, unit]: [Metric, string, string]) => {
        const c = table[metric], delta = c.change.mean_difference, a = c.baseline.mean_of_available_days, b = c.period.mean_of_available_days, seconds = metric === "sleep_duration";
        const top = Math.max(a || 0, b || 0);
        const mean = (v: number | null): string => !finite(v) ? "Unavailable" : seconds ? duration(v) : v.toFixed(1);
        const change = !finite(delta) ? "Unavailable" : `${delta > 0 ? "+" : delta < 0 ? "−" : ""}${seconds ? `${Math.abs(delta / 60).toFixed(1)} min` : Math.abs(delta).toFixed(1)}`;
        // Zero-based per metric: equal lengths mean equal values; rows are never scaled to exaggerate a change.
        const bar = (v: number | null, color: string) => finite(v) && v > 0 ? <i style={{ display: "block", height: 4, width: `${v / top * 100}%`, borderRadius: "0 2px 2px 0", background: color }} /> : null;
        const flags = Array.from(new Set(c.warnings.map((warning: string) => warningText(warning)[0]))).filter(Boolean).join(" · ");
        return <div key={metric} data-testid={`compare-${metric}`} role="rowgroup" style={{ borderBottom: `1px solid ${p.rule}` }}>
          <div role="row" style={row}>
            <div role="cell" style={{ ...cell, textAlign: "left" }}>{name}<span style={small}>{unit}</span>{top > 0 && <span aria-hidden="true" data-bars={metric} style={{ display: "grid", gap: 2, marginTop: 7 }}>{bar(a, p.stages[0])}{bar(b, p.stages[1])}</span>}</div>
            {[c.baseline, c.period].map((side: Period, i: number) => <div key={i} role="cell" data-period={i ? "period" : "baseline"} style={cell}>{mean(side.mean_of_available_days)}<span style={small}>{side.coverage.days_with_value}/{side.coverage.requested_days} days</span></div>)}
            <div role="cell" data-change style={{ ...cell, fontWeight: 700, whiteSpace: "nowrap" }}>{change}</div>
          </div>
          {flags && <div data-testid="comparison-warning" style={{ padding: "0 4px 12px", color: p.secondary, fontSize: 11 }}>{flags}</div>}
        </div>;
      })}
    </div>
    <div data-testid="comparison-note" style={help}>{shared.length ? shared.join(" ") : "Complete metric coverage for both periods."} Differences do not establish a cause or personal baseline.</div>
  </div>;
}
function TrendsPanel({ data, row, shown, start, last7, p, dark, scrub, onLeave, select, setWindow, show }: PanelProps & { data: Row[]; shown: number; start: number; last7: boolean; dark: boolean; scrub: (left: number, right: number, hover: boolean) => Scrub; onLeave: (e: PointerEvent<HTMLDivElement>) => void; setWindow: (useLast7: boolean) => void; show: (next: View) => void }) {
  const gaps = Array.from(new Set(lanes.flatMap((spec: LaneSpec) => data.filter((r: Row) => r.values[spec.metric].value === null).map((r: Row) => r.values[spec.metric].status))));
  const stat = (label: string, metric: Metric) => <div key={metric} style={{ display: "flex", flexDirection: "column", justifyContent: "space-between", gap: 3, minWidth: 0 }}><div style={{ color: p.secondary, fontSize: 11 }}>{label}</div><div data-testid={`stat-${metric}`} style={{ color: p.ink, fontSize: 18, fontWeight: 700, letterSpacing: "-.01em" }}>{format(metric, row.values[metric].value)}</div></div>;
  return <section id="panel-trends" role="tabpanel" aria-labelledby="tab-trends">
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10, margin: "16px 0 8px" }}>
      {rows.length > 7 ? <div role="group" aria-label="Visible dates" style={{ display: "inline-flex", gap: 2, padding: 3, borderRadius: 12, background: p.tint }}>{[false, true].map((recent: boolean) => <Button key={String(recent)} label={recent ? "Last 7" : `All ${rows.length}`} aria-pressed={last7 === recent} onClick={() => setWindow(recent)} style={control(p, { minHeight: coarse ? 38 : 32, padding: "5px 12px", border: 0, borderRadius: 9, background: last7 === recent ? p.primaryFill : "transparent", color: last7 === recent ? ON_FILL : p.ink })} />)}</div> : <span />}
      <span data-testid="window-label" style={{ color: p.secondary, fontSize: 12 }}>{periodLabel(data[0].day, data[data.length - 1].day).replace(/, \d{4}$/, "")}</span>
    </div>
    {data.length > 1 && <Scrubber data={data} row={row} value={shown} low={start} high={rows.length - 1} p={p} scrub={scrub(PLOT_LEFT, PLOT_RIGHT, false)} onSelect={(index: number) => select(index, true)} />}
    <div onPointerLeave={onLeave}>{lanes.map((spec: LaneSpec) => <Lane key={spec.metric} data={data} spec={spec} row={row} p={p} dark={dark} scrub={scrub(PLOT_LEFT, PLOT_RIGHT, true)} />)}</div>
    {gaps.length > 0 && <div data-testid="gap-key" style={note(p)}>Gaps: {gaps.map((status: string) => `${glyphs[status] || "—"} ${statusName(status)}`).join(" · ")}</div>}
    <div style={{ marginTop: 14, paddingTop: 14, borderTop: `1px solid ${p.rule}` }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 12 }}>{stat("Garmin need", "sleep_need")}{stat("Awake during sleep window", "sleep_awake")}{stat("Body Battery charged · day", "body_battery_charged")}</div>
      <StageDetail row={row} p={p} />
    </div>
    <div data-testid="missingness-note" style={note(p)}>{notes(row)}</div>
    <Button label="Inspect this night →" onClick={(e: { currentTarget: HTMLButtonElement }) => { show("night"); e.currentTarget.ownerDocument.getElementById("tab-night")?.focus(); }} hover={{ background: p.tint }} style={control(p, { marginTop: 12 })} />
  </section>;
}
function NightPanel({ row, selected, p, select }: PanelProps & { selected: number }) {
  const details: [string, Metric, string][] = [["Overnight HRV", "overnight_hrv", "Nightly observation; no personal baseline inferred"], ["Resting heart rate", "resting_heart_rate", "Daily observation, not the overnight minimum"], ["Sleep score", "sleep_score", "Garmin assessment"], ["Body Battery charged", "body_battery_charged", "Daily charge, not attributed solely to sleep"]];
  const stepper = (label: string, text: string, off: boolean, to: number) => <Button label={text} aria-label={label} disabled={off} onClick={(e: { currentTarget: HTMLButtonElement }) => { select(to, true); if (to === 0 || to === rows.length - 1) e.currentTarget.parentElement?.querySelector("select")?.focus(); }} hover={{ background: p.tint }} style={control(p, { flex: "none", width: 44, padding: "8px 0", fontSize: 16 })} />;
  return <section id="panel-night" role="tabpanel" aria-labelledby="tab-night">
    <div style={{ display: "flex", alignItems: "stretch", gap: 6, margin: "12px 0 18px" }}>
      {stepper("Previous night", "←", selected === 0, selected - 1)}
      <span style={{ position: "relative", flex: "1 1 auto", minWidth: 0 }}>
        <select aria-label="Associated night date" value={selected} onChange={(e: ChangeEvent<HTMLSelectElement>) => select(Number(e.currentTarget.value), true)} style={{ appearance: "none", WebkitAppearance: "none", display: "block", width: "100%", height: "100%", minHeight: coarse ? 44 : 38, padding: "8px 32px 8px 12px", border: `1px solid ${p.rule}`, borderRadius: 10, background: "transparent", color: p.ink, font: "inherit", fontSize: coarse ? 16 : 14, fontWeight: 600 }}>{rows.map((r: Row, i: number) => <option key={r.day} value={i}>{dateLabel(r.day)}</option>)}</select>
        <svg aria-hidden="true" width={12} height={8} style={{ position: "absolute", top: "50%", right: 12, marginTop: -4, pointerEvents: "none" }}><path d="M1.5 1.5L6 6l4.5-4.5" fill="none" stroke={p.ink} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" /></svg>
      </span>
      {stepper("Next night", "→", selected === rows.length - 1, selected + 1)}
    </div>
    <div role="heading" aria-level={3} style={{ color: p.ink, fontSize: 14, fontWeight: 650 }}>Sleep composition</div>
    <StageDetail row={row} p={p} />
    <div style={{ margin: "12px 0", color: p.secondary, fontSize: 12 }}>Awake: {format("sleep_awake", row.values.sleep_awake.value)}, reported separately from total sleep. Garmin need is an estimate, not a prescribed target.</div>
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0 20px", marginTop: 12 }}>{details.map(([name, metric, text]: [string, Metric, string]) => <div key={metric} style={{ minWidth: 0, padding: "12px 0", borderTop: `1px solid ${p.rule}` }}><div style={{ color: p.secondary, fontSize: 11 }}>{name}</div><div data-testid={`detail-${metric}`} style={{ marginTop: 2, color: p.ink, fontSize: 22, fontWeight: 700, letterSpacing: "-.01em" }}>{format(metric, row.values[metric].value)}</div><div style={{ margin: "3px 0 0", color: p.secondary, fontSize: 12 }}>{row.values[metric].value === null ? statusName(row.values[metric].status) : text}</div></div>)}</div>
    <div data-testid="missingness-note" style={note(p)}>{notes(row, details.map((item: [string, Metric, string]) => item[1]))}</div>
    <details style={fold(p)}><summary style={{ minHeight: 24, cursor: "pointer" }}>Source sleep window</summary>{(["start", "end"] as const).map((part: "start" | "end") => <div key={part} style={{ margin: "6px 0" }}>{part === "start" ? "Start" : "End"}: {row.night.timing[`${part}_utc`] ? stamp(row.night.timing[`${part}_utc`] || "") : row.night.timing[`${part}_local`] ? `${row.night.timing[`${part}_local`]} · source-local timestamp as returned` : "not returned"}</div>)}<div style={{ margin: "6px 0" }}>Wall times without an offset have an unspecified historical zone.</div></details>
  </section>;
}
function Footer({ p, dark }: { p: Tone; dark: boolean }) {
  const [x, y, w, h] = brand.logo.viewBox.split(" ").map(Number);
  const covered: [Metric, string][] = [...lanes.map((spec: LaneSpec): [Metric, string] => [spec.metric, spec.label]), ["body_battery_charged", "Body Battery charged"]];
  return <div>
    <details style={fold(p)}><summary style={{ minHeight: 24, cursor: "pointer" }}>Coverage, source &amp; freshness</summary>
      <div style={{ margin: "6px 0" }}>{snapshot.report.archive_provenance.freshness_meaning}</div>
      {covered.map(([metric, label]: [Metric, string]) => {
        const available = rows.filter((r: Row) => r.values[metric].value !== null), stamps = available.map((r: Row) => r.values[metric].fetched_at).filter((s: string | null): s is string => !!s).sort();
        const oldest = stamps[0], newest = stamps[stamps.length - 1], nowrap: CSSProperties = { whiteSpace: "nowrap" };
        return <div key={metric} style={{ margin: "6px 0" }}>{label}: {available.length}/{rows.length} dates · {!oldest ? "no available fetches" : <span>fetched <span style={nowrap}>{stamp(oldest)}</span>{newest !== oldest && <span> to <span style={nowrap}>{stamp(newest)}</span></span>}</span>}</div>;
      })}
      <div style={{ margin: "6px 0" }}>Garmin's associated calendar dates, with both end dates included. Failed refreshes stay unavailable. Selection resets when this Page reopens.</div>
    </details>
    <footer style={{ marginTop: 16, paddingTop: 10, borderTop: `1px solid ${p.rule}`, color: p.secondary, fontSize: 11 }}>
      <div>Saved archive snapshot. Ask Grok to load another date range; this Page never syncs.<br />Sleep stages, score and need are Garmin estimates. Co-movement does not establish a cause.</div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 12, color: p.ink, fontSize: 12, fontWeight: 700 }}>
        {/* The host repaints white plates and the logo's white line dark; a pale box keeps them as drawn. */}
        <span data-testid="logo-plate" style={{ display: "block", flex: "none", borderRadius: 6, background: dark ? p.stages[2] : p.tint }}><svg data-testid="logo" viewBox={`${x - 53} ${y - 36} ${w + 106} ${h + 72}`} aria-hidden="true" style={{ display: "block", width: "auto", height: 22 }}>{brand.logo.paths.map((path: LogoPath, i: number) => <path key={i} {...path} />)}</svg></span>Garmin Data Workbench
      </div>
    </footer>
  </div>;
}
function Explorer() {
  const theme = useGrokTheme(), dark = theme.kind === "dark", tone = dark ? brand.dark : brand.light;
  // Rings cut out against the host's actual surface. Setting it on the root also stops the host's
  // runtime color adapter repainting authored text and SVG; see docs/GROK_CHARTS.md.
  const p: Tone = { ...tone, background: theme.bg?.base || tone.background, motion: `${theme.motion?.hover || "140ms"} ${theme.motion?.easing || "ease"}` };
  const [selected, setSelected] = useState(rows.length - 1);
  // A mouse hover previews a night without selecting it; a press or drag selects.
  const [preview, setPreview] = useState<number | null>(null);
  const [view, setView] = useState<View>("trends");
  const [last7, setLast7] = useState(false);
  const [announced, setAnnounced] = useState("");
  const start = last7 ? Math.max(0, rows.length - 7) : 0, visible = rows.slice(start), shown = preview ?? selected, row = rows[shown];
  const tabs: View[] = ["trends", "night", "compare"];
  function select(index: number, announce = false): void {
    const next = Math.max(0, Math.min(rows.length - 1, index)), night = rows[next];
    setPreview(null); setSelected(next);
    if (next < start) setLast7(false);
    if (announce) setAnnounced(`${dateLabel(night.day)}, sleep ${format("sleep_duration", night.values.sleep_duration.value)}, HRV ${format("overnight_hrv", night.values.overnight_hrv.value)}`);
  }
  function setWindow(useLast7: boolean): void { setPreview(null); setLast7(useLast7); if (useLast7) setSelected(Math.max(selected, rows.length - 7)); }
  function show(next: View): void { setPreview(null); setView(next); }
  // Nearest visible night to a pointer, between the given insets of the event's element.
  function nearest(e: PointerEvent<HTMLDivElement>, left: number, right: number): number {
    const box = e.currentTarget.getBoundingClientRect(), span = box.width - left - right, n = visible.length;
    return start + (n < 2 || span <= 0 ? 0 : Math.max(0, Math.min(n - 1, Math.round((e.clientX - box.left - left) / span * (n - 1)))));
  }
  function scrub(left: number, right: number, hover: boolean): Scrub {
    return {
      // Stops a mouse drag from selecting the text around the chart.
      onMouseDown: (e: { preventDefault(): void }) => e.preventDefault(),
      onPointerDown: (e: PointerEvent<HTMLDivElement>) => {
        try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* A synthetic pointer has nothing to capture. */ }
        // Arrow keys continue from the clicked night. Touch never raises a keyboard.
        if (e.pointerType === "mouse") e.currentTarget.ownerDocument.getElementById("day-range")?.focus({ preventScroll: true });
        select(nearest(e, left, right));
      },
      onPointerMove: (e: PointerEvent<HTMLDivElement>) => { if (e.buttons) select(nearest(e, left, right)); else if (hover && e.pointerType === "mouse") setPreview(nearest(e, left, right)); },
    };
  }
  // Crossing between charts keeps the preview; leaving them restores the selected night.
  const endPreview = (e: PointerEvent<HTMLDivElement>): void => { if (e.pointerType === "mouse") setPreview(null); };
  function tabKey(e: KeyboardEvent<HTMLButtonElement>, index: number): void {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const next = tabs[e.key === "Home" ? 0 : e.key === "End" ? 2 : (index + (e.key === "ArrowRight" ? 1 : 2)) % 3];
    show(next); e.currentTarget.ownerDocument.getElementById(`tab-${next}`)?.focus();
  }
  return <div data-testid="explorer" data-committed-date={rows[selected].day} style={{ maxWidth: 840, margin: "0 auto", minWidth: 0, background: p.background, color: p.ink, colorScheme: dark ? "dark" : "light", fontFamily: theme.font?.family || FONT, fontSize: 14, lineHeight: 1.45, fontVariantNumeric: "tabular-nums", overflowWrap: "anywhere" }}>
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", alignItems: "center", gap: "4px 12px" }}>
      <div data-testid="range-label" style={{ color: p.secondary, fontSize: 13, whiteSpace: "nowrap" }}>{periodLabel(snapshot.report.from, snapshot.report.to)} · {rows.length} {rows.length === 1 ? "day" : "days"}</div>
      <span style={{ padding: "4px 8px", borderRadius: 6, background: p.tint, color: p.primary, fontSize: 11, fontWeight: 700, letterSpacing: ".02em", textAlign: "right" }}>{snapshot.report.archive_provenance.synthetic ? "SYNTHETIC DATA" : "LOCAL ARCHIVE · UNMARKED PROVENANCE"}</span>
    </div>
    <div role="tablist" aria-label="Sleep explorer views" style={{ display: "flex", gap: 2, marginTop: 14, borderBottom: `1px solid ${p.rule}` }}>{tabs.map((tab: View, i: number) => <Button key={tab} id={`tab-${tab}`} role="tab" label={["Trends", "Night detail", "Compare"][i]} tabIndex={view === tab ? 0 : -1} aria-selected={view === tab} aria-controls={`panel-${tab}`} onKeyDown={(e: KeyboardEvent<HTMLButtonElement>) => tabKey(e, i)} onClick={() => show(tab)} hover={{ color: p.ink }}
      style={{ minHeight: coarse ? 44 : 42, marginBottom: -1, padding: "8px 10px", border: 0, borderBottom: `2px solid ${view === tab ? p.primary : "transparent"}`, background: "none", color: view === tab ? p.ink : p.secondary, fontWeight: view === tab ? 650 : 500 }} />)}</div>
    {view !== "compare" && <Hero data={visible} row={row} p={p} dark={dark} scrub={scrub(0, 0, true)} onLeave={endPreview} />}
    {view === "trends" && <TrendsPanel data={visible} row={row} shown={shown} start={start} last7={last7} p={p} dark={dark} scrub={scrub} onLeave={endPreview} select={select} setWindow={setWindow} show={show} />}
    {view === "night" && <NightPanel row={row} selected={selected} p={p} select={select} />}
    {view === "compare" && <section id="panel-compare" role="tabpanel" aria-labelledby="tab-compare"><ComparisonView p={p} /></section>}
    {view !== "compare" && <div data-testid="ask-hint" style={{ display: "inline-block", margin: "16px 0 0", padding: "8px 12px", borderRadius: "14px 14px 14px 4px", background: p.tint, color: p.ink, fontSize: 13 }}>Ask Grok about {dateLabel(row.day)} in this conversation.</div>}
    <Footer p={p} dark={dark} />
    <span aria-live="polite" style={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clipPath: "inset(50%)" }}>{announced}</span>
  </div>;
}
export default function App() {
  return <Page title="Sleep & recovery" width="column"><Section><Explorer /></Section></Page>;
}
