import { Page, Section, useState, useGrokTheme } from "grok/canvas";
import type { CSSProperties, PointerEvent, ChangeEvent } from "grok/canvas";

type Lane = {
  label: string;
  unit: string;
  mark: "bar" | "line";
  values: (number | null)[];
  statuses: string[];
  coverage: string; // days_with_value/requested_days
  domain?: [number, number]; // Optional fixed scale, such as [0, 100] for a score.
  format?: (value: number) => string; // Optional display format, such as duration.
  step?: number; // Optional tick spacing in source units, such as 7200 for two-hour ticks from seconds.
};
// Seconds as 7h 42m. For minutes, use (v) => duration(v, 1).
const duration = (value: number, perMinute = 60): string => {
  const minutes = Math.round(Math.abs(value) / perMinute);
  return `${value < 0 ? "−" : ""}${Math.floor(minutes / 60)}h${minutes % 60 ? ` ${minutes % 60}m` : ""}`;
};
// CONFIGURATION: replace this block with script-verified query data.
const title = "A week in view";
const provenance = "SAMPLE DATA, REPLACE";
const freshness = "Invented observations · no archive read";
const dates = ["2030-01-01", "2030-01-02", "2030-01-03", "2030-01-04", "2030-01-05", "2030-01-06", "2030-01-07"];
const lanes: Lane[] = [
  { label: "Example volume", unit: "units", mark: "bar", values: [4, 0, null, 8, null, 5, 6],
    statuses: ["ok", "ok", "error", "ok", "empty", "ok", "ok"], coverage: "5/7" },
  { label: "Example level", unit: "points", mark: "line", values: [2, 3, null, 6, null, null, 4],
    statuses: ["ok", "ok", "metric_not_returned", "ok", "not_checked", "response_missing", "ok"], coverage: "4/7" },
];
// END CONFIGURATION. Reusable code follows.
const brand = /*__BRAND_TOKENS__*/ as const;
type Tone = (typeof brand)["light" | "dark"];
const glyphs: Record<string, string> = { error: "×", empty: "□", not_checked: "|", metric_not_returned: "◇", response_missing: "+" };
const names: Record<string, string> = { error: "failed refresh", empty: "empty response", not_checked: "not collected", metric_not_returned: "not returned", response_missing: "response missing" };
const left = 26;
const right = 48;
const bottom = 108;
const x = (i: number): number => dates.length < 2 ? 50 : i / (dates.length - 1) * 100;
// UTC here keeps a calendar date from shifting across a time zone.
const shortDate = (date: string): string => new Date(`${date}T00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "numeric" });
const longDate = (date: string): string => new Date(`${date}T00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", weekday: "short", month: "short", day: "numeric" });
const first = dates[0];
const last = dates[dates.length - 1];
const span = first === last ? "" : first.slice(0, 7) === last.slice(0, 7) ? `–${Number(last.slice(8))}` : ` – ${shortDate(last)}`;
const period = `${shortDate(first)}${span}, ${last.slice(0, 4)}`;
const display = (lane: Lane, value: number | null): string => value === null ? "N/A" : lane.format ? lane.format(value) : value.toLocaleString("en-US");
const tickText = (value: number): string => Math.abs(value) >= 10000 ? `${value / 1000}k` : value.toLocaleString("en-US");
// Bars include zero; lines may focus on their range; ticks are round.
function scaleOf(lane: Lane): { low: number; high: number; steps: number[] } {
  const values = lane.values.filter((v: number | null): v is number => v !== null);
  const base = lane.mark === "bar" ? [0] : [];
  let low = lane.domain ? lane.domain[0] : values.length ? Math.min(...values, ...base) : 0;
  let high = lane.domain ? lane.domain[1] : values.length ? Math.max(...values, ...base) : 1;
  if (high === low) {
    low = low >= 0 ? Math.max(0, low - 1) : low - 1;
    high += 1;
  }
  const power = Math.pow(10, Math.floor(Math.log10(high - low)));
  const ratio = (high - low) / power;
  const step = lane.step ?? power * (ratio > 5 ? 5 : ratio >= 2 ? 1 : 0.5);
  if (!lane.domain) {
    low = Math.floor(low / step) * step;
    high = Math.ceil(high / step) * step;
  }
  const steps: number[] = [];
  for (let t = Math.ceil(low / step); t * step <= high; t++) steps.push(t * step);
  return { low, high, steps };
}
const ticks = Array.from(new Set([0, Math.round((dates.length - 1) / 2), dates.length - 1]));
const gaps = Array.from(new Set(lanes.flatMap((lane: Lane) => lane.statuses.filter((s: string, i: number) => lane.values[i] === null))));
const noSelect: CSSProperties = { userSelect: "none", WebkitUserSelect: "none", touchAction: "pan-y", cursor: "ew-resize" };
function LaneView({ lane, index, shown, p, scrub, motion }: { lane: Lane; index: number; shown: number; p: Tone; scrub: Record<string, unknown>; motion: string }) {
  const { low, high, steps } = scaleOf(lane);
  const y = (v: number): number => bottom - (v - low) / (high - low) * 96;
  const runs: number[][] = [];
  lane.values.forEach((v: number | null, i: number) => {
    if (v === null) return;
    if (i === 0 || lane.values[i - 1] === null) runs.push([]);
    runs[runs.length - 1].push(i);
  });
  const column = (i: number): CSSProperties => ({ position: "absolute", left: `${x(i)}%`, transform: "translateX(-50%)" });
  return <div style={{ borderTop: `1px solid ${p.rule}`, paddingTop: 12, marginTop: 12 }}>
    <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "baseline" }}>
      <div role="heading" aria-level={2} style={{ fontWeight: 650 }}>{lane.label}</div>
      <span style={{ color: p.secondary, fontSize: 11 }}>{lane.unit} · {lane.coverage} days</span>
    </div>
    <div data-lane={index} data-date={dates[shown]} {...scrub} role="img" aria-label={`${lane.label} by date; the slider inspects values.`}
      style={{ ...noSelect, position: "relative", height: 126, marginTop: 8, overflow: "hidden" }}>
      <div data-plot style={{ position: "absolute", left, right, height: 120 }}>
        {steps.map((v: number) => <div key={v}>
          <div style={{ position: "absolute", top: y(v), left: -12, right: -12, height: 1, background: p.rule }} />
          <span data-tick style={{ position: "absolute", top: y(v) - 7, right: -right, color: p.secondary, fontSize: 10, whiteSpace: "nowrap" }}>{lane.format ? lane.format(v) : tickText(v)}</span>
        </div>)}
        <div data-guide style={{ ...column(shown), top: 4, height: bottom, width: 1, background: p.primary, opacity: .45, transition: motion }} />
        {/* EXTEND MARKS HERE: bar or unsmoothed, gap-split line. */}
        {lane.mark === "bar" && lane.values.map((v: number | null, i: number) => v !== null && <div key={i} data-mark="bar" data-index={i} data-value={v}
          style={{ ...column(i), width: `min(22px, ${60 / dates.length}%)`, top: Math.min(y(v), y(0)) - (v === 0 ? 2 : 0), height: Math.max(2, Math.abs(y(0) - y(v))), background: p.primary, borderRadius: "3px 3px 0 0" }} />)}
        {lane.mark === "line" && <svg width="100%" height={120} style={{ position: "absolute", overflow: "visible" }}>
          <svg width="100%" height={120} viewBox="0 0 100 120" preserveAspectRatio="none" style={{ overflow: "visible" }}>
            {runs.filter((run: number[]) => run.length > 1).map((run: number[], j: number) => <path key={j} data-run={run.join(",")}
              d={run.map((i: number, k: number) => `${k ? "L" : "M"}${x(i)},${y(lane.values[i] as number)}`).join(" ")}
              fill="none" stroke={p.primary} strokeWidth={2.5} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />)}
          </svg>
          {runs.filter((run: number[]) => dates.length <= 31 || run.length === 1).flatMap((run: number[]) => run.map((i: number) => <circle key={i}
            data-mark="dot" data-lone={run.length === 1} data-index={i} cx={`${x(i)}%`} cy={y(lane.values[i] as number)} r={3} fill={p.primary} />))}
        </svg>}
        {lane.values.map((v: number | null, i: number) => v === null && <span key={i} data-gap={lane.statuses[i]} data-index={i}
          style={{ ...column(i), top: bottom - 17, fontSize: 15, fontWeight: 650, color: p.secondary }}>{glyphs[lane.statuses[i]] || "—"}</span>)}
      </div>
    </div>
  </div>;
}
function Chart() {
  const theme = useGrokTheme();
  const dark = theme.kind === "dark";
  const p = dark ? brand.dark : brand.light;
  const [selected, setSelected] = useState(dates.length - 1);
  const [preview, setPreview] = useState<number | null>(null);
  const [ring, setRing] = useState(false);
  const shown = preview ?? selected;
  const media = (query: string): boolean => typeof matchMedia === "function" && matchMedia(query).matches;
  const calm = media("(prefers-reduced-motion: reduce)");
  const motion = calm ? "none" : `left ${theme.motion.hover} ${theme.motion.easing}`;
  function select(i: number): void {
    setPreview(null);
    setSelected(i);
  }
  function nearest(e: PointerEvent<HTMLDivElement>): number {
    const box = e.currentTarget.getBoundingClientRect();
    const ratio = (e.clientX - box.left - left) / (box.width - left - right);
    return Math.max(0, Math.min(dates.length - 1, Math.round(ratio * (dates.length - 1))));
  }
  const scrub = {
    onMouseDown: (e: { preventDefault(): void }) => e.preventDefault(),
    onPointerDown: (e: PointerEvent<HTMLDivElement>) => {
      e.currentTarget.setPointerCapture(e.pointerId);
      if (e.pointerType === "mouse") e.currentTarget.ownerDocument.getElementById("day-range")?.focus({ preventScroll: true });
      select(nearest(e));
    },
    onPointerMove: (e: PointerEvent<HTMLDivElement>) => {
      if (e.buttons) select(nearest(e));
      else if (e.pointerType === "mouse") setPreview(nearest(e));
    },
    onPointerLeave: () => setPreview(null),
  };
  return <div data-chart data-committed={dates[selected]} style={{ maxWidth: 800, margin: "0 auto", minWidth: 0, background: theme.bg.base,
    fontFamily: theme.font.family, color: p.ink, fontSize: 14, lineHeight: 1.45, fontVariantNumeric: "tabular-nums", overflowWrap: "anywhere", colorScheme: dark ? "dark" : "light" }}>
    <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "space-between", gap: 8, alignItems: "center", fontSize: 11 }}>
      <span style={{ color: p.secondary }}>{period} · {dates.length} {dates.length === 1 ? "day" : "days"}</span>
      <b data-badge style={{ padding: "4px 8px", borderRadius: 5, background: p.tint, color: p.primary }}>{provenance}</b>
    </div>
    <div style={{ marginTop: 16 }}>
      <div data-selected-date={dates[shown]} style={{ fontSize: 16, fontWeight: 650 }}>{longDate(dates[shown])}</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(115px,1fr))", gap: "10px 16px", marginTop: 10 }}>
        {lanes.map((lane: Lane, i: number) => <div key={i} style={{ minWidth: 0 }}>
          <div style={{ fontSize: 11, color: p.secondary }}>{lane.label}</div>
          <div data-readout={i} style={{ fontSize: 24, letterSpacing: "-.02em", fontWeight: 700 }}>{display(lane, lane.values[shown])}</div>
          <div style={{ color: p.secondary, fontSize: 11 }}>{lane.values[shown] === null ? names[lane.statuses[shown]] || lane.statuses[shown] : lane.unit}</div>
        </div>)}
      </div>
    </div>
    <div data-scrubber {...scrub} style={{ ...noSelect, position: "relative", height: 44, marginTop: 6 }}>
      <div data-track style={{ position: "absolute", left, right, top: 0, height: 44 }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 21, height: 3, borderRadius: 3, background: p.rule }} />
        <div data-thumb style={{ position: "absolute", left: `${x(shown)}%`, top: 12, width: 20, height: 20, borderRadius: "50%", background: p.primary,
          transform: "translateX(-50%)", outline: ring ? `2px solid ${p.primary}` : "none", outlineOffset: 3, transition: motion }} />
        <input id="day-range" type="range" min={0} max={dates.length - 1} step={1} value={shown} aria-label="Selected date; arrow keys move one day" aria-valuetext={longDate(dates[shown])}
          onChange={(e: ChangeEvent<HTMLInputElement>) => select(Number(e.currentTarget.value))}
          onFocus={() => setRing(true)} onBlur={() => setRing(false)}
          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", margin: 0, opacity: 0, pointerEvents: "none" }} />
      </div>
    </div>
    <div style={{ color: p.secondary, fontSize: 11 }}>Drag or tap a chart · arrow keys move the date</div>
    {lanes.map((lane: Lane, index: number) => <LaneView key={index} {...{ lane, index, shown, p, scrub, motion }} />)}
    <div data-date-axis style={{ position: "relative", height: 26, marginLeft: left, marginRight: right, color: p.secondary, fontSize: 10 }}>
      {ticks.map((i: number) => <span key={i} data-date-label style={{ position: "absolute", left: `${x(i)}%`, transform: "translateX(-50%)", whiteSpace: "nowrap" }}>{shortDate(dates[i])}</span>)}
    </div>
    {gaps.length > 0 && <div data-gap-key style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px", marginTop: 6, color: p.secondary, fontSize: 12 }}>
      {gaps.map((status: string) => <span key={status}>{glyphs[status] || "—"} {names[status] || status}</span>)}
    </div>}
    <div style={{ marginTop: 14, color: p.secondary, fontSize: 11 }}>{freshness}</div>
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 14, paddingTop: 12, borderTop: `1px solid ${p.rule}`, fontSize: 12, fontWeight: 650 }}>
      <span style={{ display: "block", padding: "3px 5px", borderRadius: 5, background: dark ? p.stages[2] : p.tint }}>
        <svg data-logo viewBox={brand.logo.viewBox} aria-hidden="true" style={{ display: "block", height: 22, width: "auto" }}>
          {brand.logo.paths.map((path: (typeof brand.logo.paths)[number], i: number) => <path key={i} {...path} />)}
        </svg>
      </span>Garmin Data Workbench
    </div>
  </div>;
}
export default function App() {
  return <Page title={title} width="column"><Section><Chart /></Section></Page>;
}
