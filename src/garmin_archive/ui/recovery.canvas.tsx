// Garmin Workbench native Page, renderer v1. Data is a fixed read-only snapshot.
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
type Snapshot = { schema_version: number; report: { from: string; to: string; archive_provenance: { synthetic: boolean | null; freshness_meaning: string }; sleep: { nights: Night[] }; trends: Record<string, { points: (Observation & { day: string })[] }> }; comparison: { metrics: Record<string, Comparison> } | null };
type Row = { day: string; night: Night; values: Record<Metric, Observation>; stages: number[] | null };
type Palette = { text: string; muted: string; surface: string; border: string; accent: string; need: string; stages: string[]; selected: string };
type LaneSpec = { metric: Metric; label: string; unit: string; height: number };
const snapshot = /*__RECOVERY_SNAPSHOT__*/ as Snapshot;
const stageKeys = ["sleep_deep", "sleep_light", "sleep_rem", "sleep_unmeasurable"];
const stageNames = ["Deep", "Light", "REM", "Unclassified"];
const metrics: Metric[] = ["sleep_duration", "sleep_need", "sleep_awake", "sleep_score", "overnight_hrv", "resting_heart_rate", "body_battery_charged"];
const lanes: LaneSpec[] = [
  { metric: "sleep_duration", label: "Sleep + stages", unit: "hours", height: 116 },
  { metric: "overnight_hrv", label: "Overnight HRV", unit: "ms", height: 66 },
  { metric: "resting_heart_rate", label: "Resting heart rate", unit: "bpm", height: 66 },
  { metric: "sleep_score", label: "Sleep score", unit: "/100", height: 66 },
  { metric: "body_battery_charged", label: "Body Battery charge", unit: "points / day", height: 66 },
];
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const duration = (seconds: number): string => {
  const minutes = Math.round(Math.abs(seconds) / 60);
  return `${seconds < 0 ? "−" : ""}${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, "0")}m`;
};
function format(metric: Metric, value: number | null): string {
  if (!finite(value)) return "Unavailable";
  if (metric === "sleep_duration" || metric === "sleep_awake") return duration(value);
  if (metric === "sleep_need") return duration(value * 60);
  return `${Number(value.toFixed(1))}${metric === "overnight_hrv" ? " ms" : metric === "resting_heart_rate" ? " bpm" : metric === "sleep_score" ? " / 100" : " pts"}`;
}
function statusLabel(status: string): string {
  const labels: Record<string, string> = { ok: "Available", error: "Refresh failed", empty: "Empty response", not_checked: "Not collected", response_missing: "Response missing", metric_not_returned: "Not returned or invalid" };
  return labels[status] || "Unavailable";
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
function palette(dark: boolean): Palette {
  return dark ? { text: "#edf2fa", muted: "#a4adbc", surface: "#1c2028", border: "#39414f", accent: "#69a6ff", need: "#e4eaf4", stages: ["#69a6ff", "#64b9dc", "#b2a5f4", "#9ca8ba"], selected: "#21334d" }
    : { text: "#152b4b", muted: "#526079", surface: "#eff3f8", border: "#cbd5e3", accent: "#0863e8", need: "#233d61", stages: ["#0863e8", "#3293be", "#6f59b6", "#8795a8"], selected: "#e7f0ff" };
}
function buttonStyle(p: Palette, active = false): CSSProperties {
  return { font: "inherit", fontSize: 12, minHeight: 40, padding: "8px 12px", border: `1px solid ${active ? p.accent : p.border}`, borderRadius: 8, background: active ? p.selected : p.surface, color: p.text, cursor: "pointer" };
}
function valueAt(row: Row, metric: Metric): number | null {
  const value = row.values[metric].value;
  return value === null ? null : metric === "sleep_duration" ? value / 3600 : metric === "sleep_need" ? value / 60 : value;
}
// Nulls split geometry, including a missing first/last day. Singleton runs have markers.
function segments(data: Row[], metric: Metric): { start: string; end: string; points: { i: number; value: number }[] }[] {
  const result: { start: string; end: string; points: { i: number; value: number }[] }[] = [];
  let run: { start: string; end: string; points: { i: number; value: number }[] } | null = null;
  data.forEach((row: Row, i: number) => {
    const value = valueAt(row, metric);
    if (value === null) { run = null; return; }
    if (!run) { run = { start: row.day, end: row.day, points: [] }; result.push(run); }
    run.end = row.day; run.points.push({ i, value });
  });
  return result;
}
function Lane({ data, selected, spec, p, choose }: { data: Row[]; selected: string; spec: LaneSpec; p: Palette; choose: (day: string) => void }) {
  const isSleep = spec.metric === "sleep_duration";
  const values = data.map((r: Row) => valueAt(r, spec.metric)).filter(finite);
  const maximum = Math.max(0, ...values, ...(isSleep ? data.map((r: Row) => valueAt(r, "sleep_need")).filter(finite) : []));
  const low = isSleep || spec.metric === "sleep_score" || spec.metric === "body_battery_charged" || !values.length ? 0 : Math.max(0, Math.floor(Math.min(...values) / 5) * 5 - 5);
  const high = spec.metric === "sleep_score" ? 100 : isSleep ? Math.max(1, Math.ceil(maximum + 0.5)) : Math.max(low + 10, Math.ceil(maximum / 5) * 5 + 5);
  const x = (i: number): number => data.length === 1 ? 500 : 28 + i * 944 / (data.length - 1);
  const y = (v: number): number => 90 - (v - low) / (high - low) * 80;
  const bar = Math.min(38, 600 / data.length);
  const selectedIndex = data.findIndex((r: Row) => r.day === selected);
  const row = data[selectedIndex];
  function pick(event: PointerEvent<SVGSVGElement>): void {
    const rect = event.currentTarget.getBoundingClientRect();
    if (rect.width <= 0) return;
    const at = (event.clientX - rect.left) / rect.width * 1000;
    const index = data.length === 1 ? 0 : Math.max(0, Math.min(data.length - 1, Math.round((at - 28) / 944 * (data.length - 1))));
    choose(data[index].day);
  }
  function key(event: KeyboardEvent<SVGSVGElement>): void {
    const delta = event.key === "ArrowLeft" ? -1 : event.key === "ArrowRight" ? 1 : 0;
    if (delta || event.key === "Home" || event.key === "End") {
      event.preventDefault();
      choose(data[event.key === "Home" ? 0 : event.key === "End" ? data.length - 1 : Math.max(0, Math.min(data.length - 1, selectedIndex + delta))].day);
    }
  }
  function lines(metric: Metric, color: string, dashed = false) {
    return segments(data, metric).map((run: { start: string; end: string; points: { i: number; value: number }[] }) => <path key={`${metric}-${run.start}`} data-series={metric} data-start-date={run.start} data-end-date={run.end}
      d={run.points.map((point: { i: number; value: number }, j: number) => `${j ? "L" : "M"}${x(point.i)},${y(point.value)}`).join(" ")}
      fill="none" stroke={color} strokeWidth={2} strokeDasharray={dashed ? "4 4" : undefined} vectorEffect="non-scaling-stroke" />);
  }
  return <div style={{ borderTop: `1px solid ${p.border}`, paddingTop: 10, minWidth: 0 }}>
    <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 8, fontSize: 12 }}><strong style={{ fontWeight: 600 }}>{spec.label}</strong><span data-testid={`value-${spec.metric}`} style={{ fontVariantNumeric: "tabular-nums" }}>{row ? format(spec.metric, row.values[spec.metric].value) : "Unavailable"}</span></div>
    <div style={{ display: "grid", gridTemplateColumns: "36px minmax(0,1fr)", gap: 4, marginTop: 4 }}>
      <div aria-hidden="true" style={{ height: spec.height, display: "flex", flexDirection: "column", justifyContent: "space-between", padding: "6px 0 5px", fontSize: 10, color: p.muted }}><span>{high}</span><span>{low}</span></div>
      <svg data-testid={`lane-${spec.metric}`} data-selected-date={selected} role="slider" tabIndex={0} aria-label={`${spec.label}: select night`} aria-valuemin={1} aria-valuemax={data.length} aria-valuenow={selectedIndex + 1} aria-valuetext={`${selected}: ${row ? format(spec.metric, row.values[spec.metric].value) : "Unavailable"}`}
        viewBox="0 0 1000 100" preserveAspectRatio="none" style={{ display: "block", width: "100%", height: spec.height, touchAction: "pan-y", userSelect: "none", cursor: "crosshair" }}
        onPointerDown={(e: PointerEvent<SVGSVGElement>) => { e.preventDefault(); e.currentTarget.focus(); pick(e); }}
        onPointerMove={(e: PointerEvent<SVGSVGElement>) => { if (e.buttons === 1) pick(e); }} onKeyDown={key}>
        <line x1={0} x2={1000} y1={10} y2={10} stroke={p.border} vectorEffect="non-scaling-stroke" /><line x1={0} x2={1000} y1={90} y2={90} stroke={p.border} vectorEffect="non-scaling-stroke" />
        {selectedIndex >= 0 && <rect x={x(selectedIndex) - Math.max(8, bar / 2 + 4)} y={0} width={Math.max(16, bar + 8)} height={100} fill={p.selected} />}
        {isSleep ? data.map((r: Row, i: number) => {
          const total = valueAt(r, "sleep_duration");
          if (total === null) return <line key={r.day} data-missing-day={r.day} x1={x(i)-3} x2={x(i)+3} y1={87} y2={87} stroke={p.muted} vectorEffect="non-scaling-stroke" />;
          if (!r.stages) return <rect key={r.day} data-day={r.day} data-value={total} x={x(i)-bar/2} y={y(total)} width={bar} height={Math.max(1,90-y(total))} fill={p.muted} opacity={0.65} />;
          let cumulative = 0;
          return <g key={r.day} data-day={r.day} data-value={total}>{r.stages.map((seconds: number, k: number) => { const bottom = cumulative; cumulative += seconds / 3600; return <rect key={stageKeys[k]} data-stage={stageKeys[k]} x={x(i)-bar/2} y={y(cumulative)} width={bar} height={Math.max(0,y(bottom)-y(cumulative))} fill={p.stages[k]} opacity={r.day === selected ? 1 : 0.82} />; })}{total === 0 && <line x1={x(i)-bar/2} x2={x(i)+bar/2} y1={90} y2={90} stroke={p.accent} strokeWidth={2} vectorEffect="non-scaling-stroke" />}</g>;
        }) : lines(spec.metric, p.accent)}
        {isSleep && lines("sleep_need", p.need, true)}
        {data.map((r: Row, i: number) => { const metric = isSleep ? "sleep_need" : spec.metric; const v = valueAt(r, metric); return v === null ? (!isSleep && <line key={r.day} data-missing-day={r.day} x1={x(i)-3} x2={x(i)+3} y1={87} y2={87} stroke={p.muted} vectorEffect="non-scaling-stroke" />) : <ellipse key={r.day} data-day={r.day} data-value={v} cx={x(i)} cy={y(v)} rx={r.day === selected ? 5 : 3} ry={r.day === selected ? 4 : 2.5} fill={isSleep ? p.need : p.accent} />; })}
        {selectedIndex >= 0 && <line data-selected-marker={selected} x1={x(selectedIndex)} x2={x(selectedIndex)} y1={0} y2={100} stroke={p.text} opacity={0.5} strokeDasharray="2 3" vectorEffect="non-scaling-stroke" />}
      </svg>
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", gap: 6, fontSize: 10, color: p.muted, padding: "3px 0 7px", flexWrap: "wrap" }}><span>{spec.unit} · {values.length}/{data.length} available</span><span>{data[0].day.slice(5)} — {data[data.length-1].day.slice(5)}</span></div>
    {isSleep && <p style={{ fontSize: 10, color: p.muted, margin: "0 0 8px" }}>Stages {data.filter((r: Row) => r.stages !== null).length}/{data.length} · Estimated need {data.filter((r: Row) => r.values.sleep_need.value !== null).length}/{data.length}</p>}
    {!values.length && <p style={{ margin: "0 0 8px", fontSize: 12, color: p.muted }}>No observations in this range</p>}
  </div>;
}
function StageDetail({ row, p }: { row: Row; p: Palette }) {
  const total = row.values.sleep_duration.value;
  if (!row.stages) return <p data-testid="stage-unavailable" style={{ color: p.muted, fontSize: 12 }}>Stage breakdown unavailable. {total !== null ? "Total sleep is available; missing stages are not filled in." : statusLabel(row.values.sleep_duration.status)}</p>;
  return <div data-testid="stage-detail">
    <div aria-hidden="true" style={{ display: "flex", height: 12, borderRadius: 4, overflow: "hidden", background: p.surface, margin: "14px 0 10px" }}>{row.stages.map((v: number, i: number) => <span key={stageKeys[i]} style={{ width: `${total && total > 0 ? v / total * 100 : 0}%`, background: p.stages[i] }} />)}</div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(110px,1fr))", gap: 10 }}>{row.stages.map((v: number, i: number) => <div key={stageKeys[i]} style={{ fontSize: 12 }}><span style={{ color: p.muted }}><span style={{ color: p.stages[i] }}>● </span>{stageNames[i]}</span><div style={{ marginTop: 3, fontVariantNumeric: "tabular-nums" }}>{duration(v)}</div></div>)}</div>
    <p style={{ fontSize: 11, color: p.muted, margin: "12px 0 0" }}>Garmin-estimated stages. Awake time and naps are separate from total sleep.</p>
  </div>;
}
function ComparisonView({ p }: { p: Palette }) {
  if (!snapshot.comparison) return <p data-testid="comparison-unavailable" style={{ color: p.muted }}>Load at least two dates to compare periods.</p>;
  const first = snapshot.comparison.metrics.sleep_duration;
  return <div data-testid="comparison">
    <p style={{ margin: "12px 0", fontSize: 12, color: p.muted }}>Earlier {first.baseline.from} — {first.baseline.to}<br />Later {first.period.from} — {first.period.to}</p>
    <p style={{ fontSize: 12, color: p.muted }}>Available-day averages. Each metric keeps its own coverage.</p>
    {lanes.map((spec: LaneSpec) => {
      const c = snapshot.comparison!.metrics[spec.metric];
      const delta = c.change.mean_difference;
      return <section key={spec.metric} data-testid={`compare-${spec.metric}`} style={{ borderTop: `1px solid ${p.border}`, padding: "14px 0" }}>
        <strong style={{ fontSize: 13 }}>{spec.label}</strong>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3,minmax(0,1fr))", gap: 8, marginTop: 9, fontSize: 12, fontVariantNumeric: "tabular-nums" }}>
          {(["baseline", "period"] as const).map((key: "baseline" | "period") => <div key={key}><span style={{ color: p.muted, fontSize: 11 }}>{key === "baseline" ? "Earlier" : "Later"}</span><div style={{ margin: "4px 0" }} data-period={key}>{format(spec.metric,c[key].mean_of_available_days)}</div><span style={{ color: p.muted, fontSize: 10 }}>{c[key].coverage.days_with_value}/{c[key].coverage.requested_days} days</span></div>)}
          <div><span style={{ color: p.muted, fontSize: 11 }}>Change</span><div data-change style={{ margin: "4px 0" }}>{finite(delta) ? `${delta > 0 ? "+" : ""}${spec.metric === "sleep_score" ? `${Number(delta.toFixed(1))} pts` : format(spec.metric,delta)}` : "Unavailable"}</div></div>
        </div>
        {c.warnings.length > 0 && <p data-testid="comparison-warning" style={{ fontSize: 11, color: p.muted, marginBottom: 0 }}>{Array.from(new Set(c.warnings.map((warning: string) => warning.endsWith("_incomplete_coverage") ? "Incomplete coverage; compare with care." : warning.endsWith("_includes_today_or_future") ? "Includes today or future dates; observations may still change." : warning === "unequal_period_lengths" ? "The periods contain different numbers of dates." : warning.replaceAll("_", " ")))).join(" ")}</p>}
      </section>;
    })}
    <p style={{ fontSize: 11, color: p.muted }}>The loaded range is split into two periods. Ask for another snapshot to change the dates. Differences do not establish a cause or personal baseline.</p>
  </div>;
}
function Explorer() {
  const theme = useGrokTheme();
  const p = palette(theme.kind === "dark");
  const [selected, setSelected] = useState(rows.length - 1);
  const [view, setView] = useState<View>("trends");
  const [last7, setLast7] = useState(false);
  const start = last7 ? Math.max(0,rows.length-7) : 0;
  const visible = rows.slice(start);
  const row = rows[selected];
  function choose(day: string): void { const i = rows.findIndex((r: Row) => r.day === day); if (i >= 0) setSelected(i); }
  function window(useLast7: boolean): void { setLast7(useLast7); if (useLast7) setSelected(Math.max(selected,rows.length-7)); }
  function tabKey(e: KeyboardEvent<HTMLButtonElement>, index: number): void {
    const delta = e.key === "ArrowLeft" ? -1 : e.key === "ArrowRight" ? 1 : 0;
    if (delta) { e.preventDefault(); const next = (["trends","night","compare"] as View[])[(index+delta+3)%3]; setView(next); e.currentTarget.parentElement?.querySelector<HTMLButtonElement>(`#tab-${next}`)?.focus(); }
  }
  return <div data-testid="explorer" style={{ maxWidth: 840, margin: "0 auto", color: p.text, fontFamily: "system-ui, sans-serif", fontSize: 14, lineHeight: 1.45, minWidth: 0, overflowWrap: "anywhere" }}>
    <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", fontSize: 11, color: p.muted }}><span style={{ border: `1px solid ${p.border}`, borderRadius: 5, padding: "3px 7px", color: p.text }}>{snapshot.report.archive_provenance.synthetic ? "SYNTHETIC DATA" : "LOCAL ARCHIVE · UNMARKED PROVENANCE"}</span><span>{snapshot.report.from} — {snapshot.report.to} · inclusive</span></div>
    <div role="tablist" aria-label="Sleep explorer views" style={{ display: "flex", flexWrap: "wrap", gap: 6, padding: "16px 0 10px", borderBottom: `1px solid ${p.border}` }}>{(["trends","night","compare"] as View[]).map((tab: View, i: number) => <button key={tab} id={`tab-${tab}`} role="tab" tabIndex={view === tab ? 0 : -1} aria-selected={view === tab} aria-controls={`panel-${tab}`} onKeyDown={(e: KeyboardEvent<HTMLButtonElement>) => tabKey(e,i)} onClick={() => setView(tab)} style={buttonStyle(p,view===tab)}>{["Trends","Night detail","Compare"][i]}</button>)}</div>
    {view !== "compare" && <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8, margin: "14px 0 10px" }}><strong data-testid="selected-date" style={{ fontSize: 14, fontVariantNumeric: "tabular-nums" }}>{row.day}</strong><div style={{ display: "flex", gap: 6 }}><button aria-label="Previous night" disabled={selected <= start} onClick={() => setSelected(Math.max(start,selected-1))} style={{ ...buttonStyle(p), opacity: selected <= start ? 0.45 : 1 }}>←</button><button aria-label="Next night" disabled={selected >= rows.length-1} onClick={() => setSelected(Math.min(rows.length-1,selected+1))} style={{ ...buttonStyle(p), opacity: selected >= rows.length-1 ? 0.45 : 1 }}>→</button></div></div>}
    {view === "trends" && <section id="panel-trends" role="tabpanel" aria-labelledby="tab-trends">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", flexWrap: "wrap", marginBottom: 12 }}><div style={{ display: "flex", gap: 5 }}><button onClick={() => window(false)} aria-pressed={!last7} style={buttonStyle(p,!last7)}>All loaded</button><button onClick={() => window(true)} aria-pressed={last7} style={buttonStyle(p,last7)}>Last 7</button></div><span style={{ fontSize: 11, color: p.muted }}>Select or drag any chart</span></div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", color: p.muted, fontSize: 10, marginBottom: 10 }}>{stageNames.map((name: string, i: number) => <span key={name}><span style={{ color: p.stages[i] }}>● </span>{name}</span>)}<span>┄ Estimated need</span></div>
      {lanes.map((spec: LaneSpec) => <Lane key={spec.metric} data={visible} selected={row.day} spec={spec} p={p} choose={choose} />)}
      <label htmlFor="day-range" style={{ display: "block", fontSize: 11, color: p.muted, marginTop: 8 }}>Inspect a night · arrow keys supported</label>
      <input id="day-range" type="range" min={start} max={rows.length-1} step={1} value={selected} aria-valuetext={row.day} onChange={(e: ChangeEvent<HTMLInputElement>) => setSelected(Number(e.currentTarget.value))} style={{ width: "100%", minHeight: 36, accentColor: p.accent }} />
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", fontSize: 12, margin: "10px 0" }}><span>Estimated need <strong>{format("sleep_need",row.values.sleep_need.value)}</strong></span><span>Awake <strong>{format("sleep_awake",row.values.sleep_awake.value)}</strong></span></div>
      <button onClick={() => setView("night")} style={buttonStyle(p)}>Inspect this night →</button>
    </section>}
    {view === "night" && <section id="panel-night" role="tabpanel" aria-labelledby="tab-night">
      <label style={{ fontSize: 12, color: p.muted }}>Associated night date <select aria-label="Associated night date" value={selected} onChange={(e: ChangeEvent<HTMLSelectElement>) => { const i=Number(e.currentTarget.value); setSelected(i); if (i < start) setLast7(false); }} style={{ ...buttonStyle(p), maxWidth: "100%", marginLeft: 8 }}>{rows.map((r: Row,i: number) => <option key={r.day} value={i}>{r.day}</option>)}</select></label>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 14, padding: "22px 0 14px" }}>{(["sleep_duration","sleep_need"] as Metric[]).map((metric: Metric) => <div key={metric}><div style={{ fontSize: 11, color: p.muted }}>{metric === "sleep_duration" ? "Total sleep" : "Estimated need"}</div><div style={{ fontSize: 28, letterSpacing: -0.7, fontVariantNumeric: "tabular-nums", marginTop: 4 }}>{format(metric,row.values[metric].value)}</div></div>)}</div>
      <StageDetail row={row} p={p} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(135px,1fr))", gap: "0 20px", marginTop: 18 }}>{[...lanes.slice(1),{metric:"sleep_awake" as Metric,label:"Awake time",unit:"",height:0}].map((spec: LaneSpec) => <div key={spec.metric} style={{ borderTop: `1px solid ${p.border}`, padding: "13px 0" }}><div style={{ fontSize: 11, color: p.muted }}>{spec.label}</div><div data-testid={`detail-${spec.metric}`} style={{ fontSize: 21, marginTop: 4, fontVariantNumeric: "tabular-nums" }}>{format(spec.metric,row.values[spec.metric].value)}</div><span style={{ fontSize: 10, color: p.muted }}>{statusLabel(row.values[spec.metric].status)}</span></div>)}</div>
      <details style={{ fontSize: 11, color: p.muted, marginTop: 12 }}><summary style={{ cursor: "pointer", minHeight: 30 }}>Source sleep times</summary>{(["start","end"] as const).map((part: "start" | "end") => <p key={part}>{part === "start" ? "Start" : "End"}: {row.night.timing[`${part}_utc`] ? `${row.night.timing[`${part}_utc`]} · UTC` : row.night.timing[`${part}_local`] ? `${row.night.timing[`${part}_local`]} · source-local timestamp as returned` : "Unavailable"}</p>)}</details>
    </section>}
    {view === "compare" && <section id="panel-compare" role="tabpanel" aria-labelledby="tab-compare"><ComparisonView p={p} /></section>}
    {view !== "compare" && <p data-testid="missingness-note" style={{ fontSize: 11, color: p.muted }}>{metrics.filter((m: Metric) => row.values[m].value === null).map((m: Metric) => `${m.replaceAll("_"," ")}: ${statusLabel(row.values[m].status)}`).join(" · ")}</p>}
    <details style={{ borderTop: `1px solid ${p.border}`, fontSize: 11, color: p.muted, marginTop: 18, paddingTop: 12 }}><summary style={{ cursor: "pointer", minHeight: 32 }}>Coverage, source & freshness</summary><p>{snapshot.report.archive_provenance.freshness_meaning}</p>{lanes.map((spec: LaneSpec) => {
      const available = rows.filter((r: Row) => r.values[spec.metric].value !== null);
      const stamps = available.map((r: Row) => r.values[spec.metric].fetched_at).filter((s: string | null): s is string => !!s).sort();
      return <p key={spec.metric}>{spec.label}: {available.length}/{rows.length} dates. Available fetches: {stamps[0] || "none"} — {stamps[stamps.length-1] || "none"}.</p>;
    })}<p>Garmin-associated calendar dates. Failed refreshes stay unavailable. Daily Body Battery charge is not attributed solely to sleep.</p><p>Saved snapshot; selection resets when reopened. Ask for another snapshot to change dates or refresh the saved observations.</p></details>
    <p style={{ color: p.muted, fontSize: 10, borderTop: `1px solid ${p.border}`, paddingTop: 12 }}>Garmin Data Workbench · Sleep stages, score and need are Garmin estimates. Co-movement does not establish a cause.</p>
  </div>;
}
export default function App() {
  return <Page title="Sleep & recovery" width="column"><Section><Explorer /></Section></Page>;
}
