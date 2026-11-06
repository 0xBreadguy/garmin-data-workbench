/* Shared recovery renderer: MCP Apps bridge or bounded native-widget snapshot. */
(() => {
  'use strict';
  const root = document.getElementById('demo');
  const $ = selector => root.querySelector(selector);
  const $$ = selector => Array.from(root.querySelectorAll(selector));
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const duration = v => !finite(v) ? 'Unavailable' : `${Math.floor(Math.round(v) / 60)}h ${String(Math.round(v) % 60).padStart(2, '0')}m`;
  const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const DAYS = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
  const dateParts = value => value.split('-').map(Number);
  const shortDate = value => { const [, m, d] = dateParts(value); return `${MONTHS[m-1]} ${d}`; };
  // Calendar arithmetic only: an associated date never passes through a time zone.
  const dateLabel = value => {
    const [y, m, d] = dateParts(value);
    const year = report && report.from.slice(0,4) !== report.to.slice(0,4) ? `, ${y}` : '';
    return `${DAYS[new Date(Date.UTC(y,m-1,d)).getUTCDay()]}, ${MONTHS[m-1]} ${d}${year}`;
  };
  // Same wording as the PNG charts' period label.
  const periodLabel = (first, last) => {
    const [ay, am, ad] = dateParts(first), [by, bm, bd] = dateParts(last);
    if (first === last) return `${MONTHS[am-1]} ${ad}, ${ay}`;
    if (ay !== by) return `${MONTHS[am-1]} ${ad}, ${ay} – ${MONTHS[bm-1]} ${bd}, ${by}`;
    if (am === bm) return `${MONTHS[am-1]} ${ad}–${bd}, ${ay}`;
    return `${MONTHS[am-1]} ${ad} – ${MONTHS[bm-1]} ${bd}, ${ay}`;
  };
  // Same stage order and names as the PNG charts.
  const stageKeys = ['deep', 'rem', 'light', 'unmeasurable'];
  const stageNames = ['Deep', 'REM', 'Light', 'Unclassified'];
  const fields = {minutes:'sleep_duration', need:'sleep_need', awake:'sleep_awake', score:'sleep_score', hrv:'overnight_hrv', rhr:'resting_heart_rate', charge:'body_battery_charged'};
  const panels = [
    {key:'minutes', name:'Sleep & stages', unit:'hours', noun:'nights', height:150},
    {key:'hrv', name:'Overnight HRV', unit:'ms', noun:'nights', height:88},
    {key:'rhr', name:'Resting heart rate', unit:'bpm', noun:'days', height:88},
    {key:'score', name:'Sleep score', unit:'of 100', noun:'nights', height:88},
  ];
  // Plot insets shared by every lane and the scrubber. The scale sits on the right, as on the PNG charts.
  const PLOT_LEFT = 20, PLOT_RIGHT = 48, DATE_AXIS = 22;
  root.style.setProperty('--plot-left', `${PLOT_LEFT}px`);
  root.style.setProperty('--plot-right', `${PLOT_RIGHT}px`);
  // Same shapes as the PNG charts, so a gap's status never depends on color. Unlisted statuses use a dash.
  const STATUS_GLYPHS = {error:'×', empty:'□', not_checked:'|', metric_not_returned:'◇', response_missing:'+'};
  const marks = new Map();
  let data = [], report = null, selected = 0, windowSize = 0, tab = 'trends';
  let initialized = false, capabilities = {}, requestId = 0, loadEpoch = 0, compareEpoch = 0;
  const snapshotNode = document.getElementById('recovery-snapshot');
  let nativeStateReady = false, restoringState = false, lastState = '';
  // A host may echo this widget's own writes late; replaying one would pull a drag backward.
  const ECHO_WINDOW_MS = 5000, recentWrites = new Map();
  const stateKey = s => [s.from,s.to,s.selectedDate,s.tab,s.window].join('|');
  const isOwnEcho = s => Date.now()-(recentWrites.get(stateKey(s)) ?? -Infinity) < ECHO_WINDOW_MS;
  function currentState() {
    return {version:1, from:report.from, to:report.to, selectedDate:data[selected].date,
      tab, window:windowSize === data.length ? 'all' : '7'};
  }
  function persistState() {
    if (!nativeStateReady || restoringState || !data.length) return;
    const state = currentState(), encoded = JSON.stringify(state);
    if (encoded === lastState) return;
    lastState = encoded;
    recentWrites.forEach((at,key) => { if (Date.now()-at >= ECHO_WINDOW_MS) recentWrites.delete(key); });
    recentWrites.set(stateKey(state),Date.now());
    try {
      Promise.resolve(window.hatchWidget.setState(state)).catch(() => {
        $('#ask-status').textContent = 'Selection could not be saved. You can still explore this snapshot.';
      });
    } catch (_) { $('#ask-status').textContent = 'Selection could not be saved. You can still explore this snapshot.'; }
  }
  function restoreState(state) {
    if (!state || state.version !== 1 || state.from !== report.from || state.to !== report.to
        || !['trends','night','compare'].includes(state.tab) || !['all','7'].includes(state.window)) return;
    const index = data.findIndex(d => d.date === state.selectedDate);
    if (index < 0) return;
    restoringState = true;
    selected = index; setWindow(state.window); showTab(state.tab);
    lastState = JSON.stringify(currentState()); restoringState = false;
  }
  const pending = new Map();
  const bridge = window.parent;
  const send = message => bridge.postMessage({jsonrpc:'2.0', ...message}, '*');
  const notify = (method, params) => send({method, params});
  function request(method, params) {
    const id = ++requestId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(id); reject(new Error('The assistant connection timed out. Try again.')); }, 20000);
      pending.set(id, {resolve, reject, timer});
      send({id, method, params});
    });
  }
  function error(message) { $('#error').textContent = message; $('#error').hidden = false; }
  function clearError() { $('#error').textContent = ''; $('#error').hidden = true; }
  function theme(context) {
    if (['light','dark'].includes(context?.theme)) document.documentElement.style.colorScheme = context.theme;
    const variables = context?.styles?.variables;
    if (variables && typeof variables === 'object') {
      Object.entries(variables).forEach(([key, value]) => {
        if (/^--[a-zA-Z0-9-]+$/.test(key) && typeof value === 'string' && value.length < 300)
          document.documentElement.style.setProperty(key, value);
      });
    }
  }
  function syncScheme() {
    // Native hosts expose a surface color, not a theme name. Select brand steps from that surface.
    root.style.colorScheme = '';
    const probe = document.createElement('i'); probe.style.color = 'var(--background)'; root.append(probe);
    const color = getComputedStyle(probe).color; probe.remove();
    const context = document.createElement('canvas').getContext('2d');
    if (!context) return;
    context.fillStyle = color; context.fillRect(0,0,1,1);
    const [r, g, b, alpha] = context.getImageData(0,0,1,1).data;
    if (alpha > 127) root.style.colorScheme = .2126*r + .7152*g + .0722*b < 128 ? 'dark' : 'light';
  }
  function unwrap(result) {
    if (result?.isError) throw new Error('The archive query failed. Check the dates and archive availability; previous results are not shown as current.');
    const value = result?.structuredContent;
    if (value?.schema_version === 1) return value;
    for (const item of result?.content || []) {
      if (item.type !== 'text') continue;
      try { const parsed = JSON.parse(item.text); if (parsed.schema_version === 1) return parsed; } catch (_) { /* not structured data */ }
    }
    throw new Error('This result does not match the sleep explorer data contract.');
  }
  async function callTool(name, args) {
    if (!initialized || !capabilities.serverTools) throw new Error('This assistant has not enabled interactive archive queries.');
    return unwrap(await request('tools/call', {name, arguments:args}));
  }
  function parseReport(value) {
    if (value?.view !== 'sleep_recovery' || value.schema_version !== 1 || !Array.isArray(value.sleep?.nights)
        || value.sleep.nights.length < 1 || value.sleep.nights.length > 90) throw new Error('Invalid sleep explorer result.');
    const trends = {};
    for (const metric of ['overnight_hrv','resting_heart_rate','body_battery_charged']) {
      if (!Array.isArray(value.trends?.[metric]?.points)) throw new Error('Missing recovery series.');
      trends[metric] = new Map(value.trends[metric].points.map(p => [p.day,p]));
    }
    return value.sleep.nights.map((night, i) => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(night.day) || !night.values) throw new Error('Invalid dated observation.');
      const d = {i, date:night.day, timing:night.timing, sleepStatus:night.status, statuses:{}, fetched:{}};
      for (const [key, metric] of Object.entries(fields)) {
        const p = trends[metric]?.get(night.day);
        const raw = p ? p.value : night.values[metric];
        d[key] = finite(raw) ? raw / (['minutes','awake'].includes(key) ? 60 : 1) : null;
        d.statuses[key] = p?.status || (night.status === 'ok' && d[key] == null ? 'metric_not_returned' : night.status);
        d.fetched[key] = p ? p.fetched_at : night.fetched_at;
      }
      // All four stages, including unmeasurable, must pass shared-query reconciliation.
      d.stages = night.stages_complete ? stageKeys.map(k => night.values['sleep_'+k] / 60) : null;
      d.complete = night.stages_complete;
      return d;
    });
  }
  const fmt = (d,key) => d[key] == null ? 'Unavailable' : ['minutes','need','awake'].includes(key) ? duration(d[key]) : `${d[key]}${key === 'hrv' ? ' ms' : key === 'rhr' ? ' bpm' : key === 'score' ? ' / 100' : ' points'}`;
  function stagesHTML(d) {
    if (!d.stages) return `<div class="empty">${d.minutes == null ? 'No available sleep duration. No stage proportions are inferred.' : 'Total sleep is available; the stage breakdown is incomplete or inconsistent. No stage proportions are inferred.'}</div>`;
    const described = d.stages.map((v,i) => `${stageNames[i]} ${duration(v)}`).join(', ');
    return `<div class="stage-track" role="img" aria-label="Sleep stage composition: ${described}">${d.stages.map((v,i) => v > 0 ? `<span class="stage-piece" style="flex:${v} 1 0;background:var(--stage-${stageKeys[i]})"></span>` : '').join('')}</div><div class="stage-labels">${d.stages.map((v,i) => `<span><i class="swatch" style="background:var(--stage-${stageKeys[i]})"></i>${stageNames[i]} <b>${duration(v)}</b></span>`).join('')}</div>`;
  }
  const statusName = s => ({error:'failed refresh; retained values masked', empty:'empty response', not_checked:'not collected', response_missing:'response missing', metric_not_returned:'not returned or invalid', ok:'available'}[s] || s || 'unavailable');
  function notes(d) {
    const out = Object.keys(fields).filter(key => d[key] == null).map(key => `${fields[key].replaceAll('_',' ')}: ${statusName(d.statuses[key])}`);
    if (d.minutes != null && !d.stages) out.push('Incomplete or inconsistent stages; total sleep only');
    return out.length ? out.join(' · ') : 'Stages exclude awake time and naps. Daily Body Battery charge is not attributed solely to sleep.';
  }
  function acceptReport(value) {
    const oldDate = data[selected]?.date;
    const parsed = parseReport(value);
    report = value; data = parsed; selected = Math.max(0,data.findIndex(d => d.date === oldDate));
    if (!oldDate) selected = data.length - 1;
    windowSize = data.length; compareEpoch++;
    $('#provenance').textContent = value.archive_provenance?.synthetic === true ? 'SYNTHETIC DATA' : 'LOCAL ARCHIVE · UNMARKED PROVENANCE';
    $('#range-label').dataset.from = value.from;
    $('#range-label').textContent = `${periodLabel(value.from,value.to)} · ${data.length} ${data.length === 1 ? 'day' : 'days'}`;
    $('#connection').classList.add('sr');
    $('#day-range').max = data.length-1;
    $('#workspace').hidden = false;
    if (snapshotNode) {
      $('#connection').textContent = 'Archive snapshot loaded. Explore these dates or ask Muse for another range.';
      $('#ask-hint').hidden = false;
    } else {
      $('#range-from').value = value.from; $('#range-to').value = value.to;
      $('#connection').textContent = 'Archive loaded. Dates and comparisons read stored data only.';
      $('#range-form').hidden = false;
      $('#range-form button').disabled = !capabilities.serverTools;
      $('#ask-night').disabled = !capabilities.message;
      $('#ask-status').textContent = capabilities.message ? '' : 'This host does not support asking from the chart.';
      const middle = Math.floor(data.length / 2);
      $('#base-from').value = value.from;
      $('#base-to').value = data[Math.max(0,middle-1)].date;
      $('#period-from').value = data[Math.min(middle,data.length-1)].date;
      $('#period-to').value = value.to;
    }
    $('#comparison-result').textContent = data.length < 2 ? 'Choose two non-overlapping periods to compare.' : 'Choose periods, then compare their covered averages.';
    clearError(); setWindow('all'); renderFreshness(); showTab(tab);
  }
  function renderFreshness() {
    const p = report.archive_provenance;
    const lines = panels.map(panel => {
      const metric = fields[panel.key];
      const coverage = report.trends[metric]?.coverage || report.sleep.coverage.fields[metric];
      const times = data.filter(d => d[panel.key] != null && d.fetched[panel.key]).map(d => d.fetched[panel.key]).sort();
      return `<li>${escape(panel.name)}: ${coverage.days_with_value}/${coverage.requested_days} days. Available fetches: ${escape(times[0] || 'none')} — ${escape(times.at(-1) || 'none')}.</li>`;
    });
    $('#freshness').innerHTML = `<p>${escape(p.freshness_meaning)}</p><ul>${lines.join('')}</ul><p>Dates are Garmin’s associated calendar dates, and both end dates are included. Historical source wall times retain their original offsets or remain unspecified.</p>`;
  }
  const legendHTML = () => `<div class="legend">${stageNames.map((name,i) => `<span><i class="swatch" style="background:var(--stage-${stageKeys[i]})"></i>${name}</span>`).join('')}<span><i class="dots"></i>Garmin need</span><span class="legend-partial" hidden><i class="swatch" style="background:var(--muted-foreground)"></i>Total only</span></div>`;
  $('#lanes').innerHTML = panels.map(p => `<section class="lane" data-key="${p.key}"><div class="lane-head"><h3>${escape(p.name)}<span class="lane-sub" id="sub-${p.key}"></span></h3><span class="value" id="value-${p.key}"></span></div>${p.key === 'minutes' ? legendHTML() : ''}<svg role="img" aria-label="${escape(p.name)} by calendar date. Use the selected-night slider for keyboard inspection."></svg></section>`).join('');
  const visibleData = () => data.slice(-windowSize);
  const plotScale = width => d3.scalePoint().domain(visibleData().map(d => d.i)).range([PLOT_LEFT,width-PLOT_RIGHT]);
  // Nearest visible night to a pointer; single-night windows have nothing to interpolate.
  function bindScrub(svg, node, x0, x1) {
    const visible = visibleData();
    const pick = e => {
      const px = e.clientX-node.getBoundingClientRect().left;
      const i = visible.length === 1 ? 0 : Math.max(0,Math.min(visible.length-1,Math.round((px-x0)/((x1-x0)/(visible.length-1)))));
      selectDay(visible[i].i,false);
    };
    // Stops a mouse drag from selecting the text around the chart.
    svg.on('mousedown', e => e.preventDefault())
      .on('pointerdown', function(e) { this.setPointerCapture(e.pointerId); pick(e); })
      .on('pointermove', e => { if (e.buttons || e.pointerType === 'mouse') pick(e); });
  }
  const roundedTop = (x,y,w,h,r) => `M${x},${y+h}V${y+r}Q${x},${y} ${x+r},${y}H${x+w-r}Q${x+w},${y} ${x+w},${y+r}V${y+h}Z`;
  function drawLane(p) {
    const lane = $(`.lane[data-key="${p.key}"]`), node = lane.querySelector('svg'), svg = d3.select(node);
    const w = lane.clientWidth, showDates = p === panels.at(-1), h = p.height+(showDates ? DATE_AXIS : 0);
    if (!w || !data.length) return;
    svg.attr('viewBox', `0 0 ${w} ${h}`).attr('height',h); svg.selectAll('*').remove();
    const visible = visibleData(), top = 6, bottom = p.height-4, x0 = PLOT_LEFT, x1 = w-PLOT_RIGHT;
    const x = plotScale(w);
    const values = visible.map(d => d[p.key]).filter(finite), extent = d3.extent(values);
    let domain;
    if (p.key === 'minutes') domain = [0,Math.max(1,Math.ceil(Math.max(0,...values,...visible.map(d => d.need).filter(finite))/60+.4))];
    else if (p.key === 'score') domain = [0,100];
    else domain = values.length ? [Math.max(0,Math.floor(extent[0]/5)*5-5),Math.ceil(extent[1]/5)*5+5] : [0,100];
    const y = d3.scaleLinear().domain(domain).range([bottom,top]);
    const step = visible.length > 1 ? (x1-x0)/(visible.length-1) : x1-x0;
    const bw = Math.min(24,step*.62), dots = visible.length <= 31;
    const line = accessor => d3.line().defined(d => finite(accessor(d))).x(d => x(d.i)).y(d => y(accessor(d)));
    const glyph = d => svg.append('text').attr('class','glyph').attr('x',x(d.i)).attr('y',bottom-3).attr('text-anchor','middle').text(STATUS_GLYPHS[d.statuses[p.key]] || '—');
    const ticks = p.key === 'score' ? [0,50,100] : y.ticks(p.key === 'minutes' ? 3 : 2);
    ticks.forEach(t => {
      svg.append('line').attr('x1',0).attr('x2',w-30).attr('y1',y(t)).attr('y2',y(t)).attr('stroke','var(--border)');
      svg.append('text').attr('x',w).attr('y',y(t)+4).attr('text-anchor','end').text(t);
    });
    const band = svg.append('g'), bandWidth = Math.max(bw+8,16);
    band.append('rect').attr('class','sel-band').attr('x',-bandWidth/2).attr('y',top-2).attr('width',bandWidth).attr('height',bottom-top+2).attr('rx',6);
    if (p.key === 'minutes') {
      const gap = bw >= 6 ? 2 : 0, radius = Math.min(4,bw/2);
      visible.forEach(d => {
        if (d.minutes == null) { glyph(d); return; }
        const left = x(d.i)-bw/2;
        if (d.minutes === 0) { svg.append('rect').attr('x',left).attr('width',bw).attr('y',bottom-1.5).attr('height',1.5).attr('fill','var(--muted-foreground)'); return; }
        if (!d.stages) {
          const height = bottom-y(d.minutes/60);
          svg.append('path').attr('d',roundedTop(left,y(d.minutes/60),bw,height,Math.min(radius,height))).attr('fill','var(--muted-foreground)').attr('opacity',.45);
          return;
        }
        const last = d.stages.reduce((found,v,k) => v > 0 ? k : found,-1);
        let sum = 0;
        d.stages.forEach((v,k) => {
          if (!(v > 0)) return;
          const below = sum > 0 ? gap : 0, yTop = y(sum+v/60), height = Math.max(.75,y(sum)-yTop-below);
          sum += v/60;
          const fill = `var(--stage-${stageKeys[k]})`;
          if (k === last) svg.append('path').attr('d',roundedTop(left,yTop,bw,height,Math.min(radius,height))).attr('fill',fill);
          else svg.append('rect').attr('x',left).attr('y',yTop).attr('width',bw).attr('height',height).attr('fill',fill);
        });
      });
      svg.append('path').datum(visible).attr('d',line(d => d.need == null ? null : d.need/60)).attr('fill','none').attr('stroke','var(--brand-ink)').attr('stroke-width',1.75).attr('stroke-linecap','round').attr('stroke-dasharray','.1 4.5');
    } else {
      svg.append('path').datum(visible).attr('d',line(d => d[p.key])).attr('fill','none').attr('stroke','var(--brand-primary)').attr('stroke-width',2.25).attr('stroke-linecap','round').attr('stroke-linejoin','round');
      visible.forEach(d => {
        if (d[p.key] == null) glyph(d);
        else if (dots) svg.append('circle').attr('cx',x(d.i)).attr('cy',y(d[p.key])).attr('r',2.75).attr('fill','var(--brand-primary)').attr('stroke','var(--background)').attr('stroke-width',1);
      });
    }
    if (!values.length) svg.append('text').attr('x',(x0+x1)/2).attr('y',top+20).attr('text-anchor','middle').attr('class','no-observations').text('No observations');
    const guide = svg.append('g');
    guide.append('line').attr('class','sel-guide').attr('y1',top-2).attr('y2',bottom);
    const dot = p.key === 'minutes' ? null : svg.append('g');
    dot?.append('circle').attr('class','sel-dot').attr('r',5.5);
    if (showDates) {
      const indices = [...new Set([0,Math.round((visible.length-1)/3),Math.round((visible.length-1)*2/3),visible.length-1])];
      indices.forEach(j => svg.append('text').attr('x',x(visible[j].i)).attr('y',h-6).attr('text-anchor','middle').text(shortDate(visible[j].date)));
    }
    svg.append('rect').attr('x',0).attr('y',0).attr('width',w).attr('height',h).attr('fill','transparent');
    bindScrub(svg,node,x0,x1);
    marks.set(p.key,{x,y,band,guide,dot,key:p.key,yValue:d => p.key === 'minutes' ? null : d[p.key]});
    markLane(p.key);
    // Enable glide only after first placement, so a redraw never sweeps in from the origin.
    requestAnimationFrame(() => { band.classed('sel-move',true); guide.classed('sel-move',true); dot?.classed('sel-move',true); });
  }
  function markLane(key) {
    const m = marks.get(key), d = data[selected]; if (!m || !d) return;
    const x = m.x(d.i), shown = x != null;
    [m.band,m.guide].forEach(g => { g.style('display',shown ? null : 'none'); if (shown) g.style('transform',`translate(${x}px,0)`); });
    if (m.dot) {
      const value = m.yValue(d), visible = shown && finite(value);
      m.dot.style('display',visible ? null : 'none');
      if (visible) m.dot.style('transform',`translate(${x}px,${m.y(value)}px)`);
    }
  }
  function placeScrub() {
    const w = $('#lanes').clientWidth, d = data[selected];
    $('#scrub').hidden = windowSize < 2;
    if (!w || !d || windowSize < 2) return;
    const x = plotScale(w)(d.i); if (x == null) return;
    const bubble = $('#scrub-bubble'); bubble.textContent = shortDate(d.date);
    bubble.style.transform = `translateX(${Math.max(0,Math.min(w-bubble.offsetWidth,x-bubble.offsetWidth/2))}px)`;
    $('#scrub-tail').style.transform = `translateX(${x-1}px)`;
  }
  let heroMark = null;
  function drawHero() {
    const node = $('#hero-line'), w = node.clientWidth, h = node.clientHeight;
    if (!w || !h || !data.length) return;
    const svg = d3.select(node); svg.attr('viewBox',`0 0 ${w} ${h}`); svg.selectAll('*').remove();
    const visible = visibleData(), pad = 8, x = d3.scalePoint().domain(visible.map(d => d.i)).range([pad,w-pad]);
    const values = visible.map(d => d.minutes).filter(finite), extent = d3.extent(values);
    const y = d3.scaleLinear().domain(values.length ? extent : [0,1]).range([h-6,8]);
    svg.append('path').datum(visible).attr('class','hero-path').attr('d',d3.line().defined(d => finite(d.minutes)).x(d => x(d.i)).y(d => y(d.minutes)));
    const dot = svg.append('circle').attr('class','hero-dot').attr('r',6);
    svg.append('rect').attr('width',w).attr('height',h).attr('fill','transparent');
    bindScrub(svg,node,pad,w-pad);
    heroMark = {x,y,dot};
    // The unaxed line stays honest by stating the range it spans.
    $('#hero-label').textContent = values.length > 1 ? `Total sleep · range ${duration(extent[0])}–${duration(extent[1])}` : 'Total sleep';
    $('#hero-coverage').textContent = `${values.length}/${visible.length}`;
    markHero();
  }
  function markHero() {
    const d = data[selected]; if (!heroMark || !d) return;
    const x = heroMark.x(d.i), shown = x != null && finite(d.minutes);
    heroMark.dot.style('display',shown ? null : 'none');
    if (shown) heroMark.dot.attr('cx',x).attr('cy',heroMark.y(d.minutes));
  }
  const drawCharts = () => { marks.clear(); panels.forEach(drawLane); placeScrub(); };
  function updateSelection(announce=false) {
    if (!data.length) return;
    const d = data[selected];
    const heading = $('#selected-date'); heading.textContent = dateLabel(d.date); heading.dataset.date = d.date;
    $('#hero-sleep').textContent = fmt(d,'minutes'); $('#hero-sleep').classList.toggle('is-missing',d.minutes == null);
    $('#hero-need').textContent = fmt(d,'need');
    $('#day-range').value = selected;
    $('#day-range').setAttribute('aria-valuetext',`${dateLabel(d.date)}, sleep ${fmt(d,'minutes')}, HRV ${fmt(d,'hrv')}`);
    panels.forEach(p => { $(`#value-${p.key}`).textContent = fmt(d,p.key); markLane(p.key); });
    placeScrub(); markHero();
    if (snapshotNode) $('#ask-hint').textContent = `Ask Muse about ${dateLabel(d.date)} in this conversation.`;
    $('#selection-summary').innerHTML = `<div class="summary-grid">${[['Garmin need','need'],['Awake during sleep window','awake'],['Body Battery charged · day','charge']].map(([label,key]) => `<div class="stat"><div class="stat-label">${label}</div><div class="stat-value num">${fmt(d,key)}</div></div>`).join('')}</div>${stagesHTML(d)}`;
    $('#data-note').textContent = notes(d);
    if (announce) $('#announcement').textContent = `${dateLabel(d.date)}, sleep ${fmt(d,'minutes')}, HRV ${fmt(d,'hrv')}`;
  }
  function selectDay(index, announce=true) {
    if (!data.length || !Number.isInteger(index)) return;
    const next = Math.max(0,Math.min(data.length-1,index));
    if (next === selected && !announce) return;
    selected = next;
    if (selected < data.length-windowSize) setWindow('all');
    updateSelection(announce); if (tab === 'night') renderNight();
    persistState();
  }
  function setWindow(value) {
    windowSize = value === '7' ? Math.min(7,data.length) : data.length;
    selected = Math.max(data.length-windowSize,selected); $('#day-range').min = data.length-windowSize;
    $$('[data-window]').forEach(b => b.setAttribute('aria-pressed',b.dataset.window === value));
    $('[data-window="all"]').textContent = `All ${data.length}`;
    $('.segmented').hidden = data.length <= 7; // Both choices would show the same dates.
    const visible = visibleData();
    $('#window-label').textContent = periodLabel(visible[0].date,visible.at(-1).date).replace(/, \d{4}$/,'');
    panels.forEach(p => { $(`#sub-${p.key}`).textContent = `${p.unit} · ${visible.filter(d => d[p.key] != null).length}/${visible.length} ${p.noun}`; });
    $('.legend-partial').hidden = !visible.some(d => d.minutes != null && d.minutes > 0 && !d.stages);
    const gaps = [...new Set(panels.flatMap(p => visible.filter(d => d[p.key] == null).map(d => d.statuses[p.key])))];
    $('#coverage-line').hidden = !gaps.length;
    $('#coverage-line').textContent = gaps.length ? `Gaps: ${gaps.map(s => `${STATUS_GLYPHS[s] || '—'} ${statusName(s)}`).join(' · ')}` : '';
    drawCharts(); drawHero(); updateSelection(); persistState();
  }
  function renderNight() {
    const d = data[selected], active = document.activeElement;
    const refocus = active?.hasAttribute?.('data-prev') ? '[data-prev]' : active?.hasAttribute?.('data-next') ? '[data-next]' : active?.id === 'night-picker' ? '#night-picker' : null;
    $('#night').innerHTML = `<div class="stepper"><button type="button" class="control" data-prev aria-label="Previous night" ${selected === 0 ? 'disabled' : ''}>←</button><label for="night-picker" class="sr">Associated night date</label><span class="select-wrap"><select class="night-select" id="night-picker">${data.map(v => `<option value="${v.i}" ${v.i === selected ? 'selected' : ''}>${dateLabel(v.date)}</option>`).join('')}</select></span><button type="button" class="control" data-next aria-label="Next night" ${selected === data.length-1 ? 'disabled' : ''}>→</button></div><h3>Sleep composition</h3>${stagesHTML(d)}<p class="help">Awake: ${fmt(d,'awake')}, reported separately from total sleep. Garmin need is an estimate, not a prescribed target.</p><div class="detail-grid">${[
      ['Overnight HRV','hrv','Nightly observation; no personal baseline inferred'],['Resting heart rate','rhr','Daily observation, not the overnight minimum'],['Sleep score','score','Garmin assessment'],['Body Battery charged','charge','Daily charge, not attributed solely to sleep']
    ].map(([name,key,note]) => `<div class="detail-item"><div class="stat-label">${name}</div><div class="stat-value num">${fmt(d,key)}</div><p class="small">${d[key] == null ? escape(statusName(d.statuses[key])) : note}</p></div>`).join('')}</div><p class="notes">${escape(notes(d))}</p><details class="freshness"><summary>Source sleep window</summary>${Object.entries(d.timing || {}).map(([k,v]) => `<p>${escape(k.replaceAll('_',' '))}: ${escape(v || 'not returned')}</p>`).join('')}<p>Wall times without an offset have an unspecified historical zone.</p></details>`;
    $('#night-picker').addEventListener('change', e => selectDay(Number(e.target.value)));
    if (refocus) (($(refocus)?.disabled ? $('#night-picker') : $(refocus)) || $('#night-picker')).focus();
  }
  function showTab(next) {
    tab = next; $$('.view').forEach(e => e.hidden = e.id !== next);
    root.dataset.view = next; $('#hero').hidden = next === 'compare';
    $$('[data-tab]').forEach(b => { b.setAttribute('aria-selected',b.dataset.tab === next); b.tabIndex = b.dataset.tab === next ? 0 : -1; });
    if (!data.length) return;
    drawHero();
    if (next === 'night') renderNight(); else if (next === 'trends') { setWindow(windowSize === data.length ? 'all' : '7'); }
    persistState();
  }
  function renderComparison(value) {
    if (value.view !== 'sleep_recovery_comparison') throw new Error('Invalid comparison result.');
    const names = {sleep_duration:'Sleep duration',overnight_hrv:'Overnight HRV',resting_heart_rate:'Resting heart rate',sleep_score:'Sleep score',body_battery_charged:'Body Battery charged'};
    const first = value.metrics.sleep_duration;
    const textValue = (value,unit) => value == null ? 'Unavailable' : unit === 's' ? duration(value/60) : `${Number(value).toFixed(1)}`;
    const diff = (v,unit) => { if (v == null) return 'Unavailable'; const text = unit === 's' ? `${Math.abs(v/60).toFixed(1)} min` : Math.abs(v).toFixed(1); return `${v > 0 ? '+' : v < 0 ? '−' : ''}${text}`; };
    // Zero-based per metric: equal lengths mean equal values; rows are never scaled to exaggerate a change.
    const bars = r => {
      const a = r.baseline.mean_of_available_days, b = r.period.mean_of_available_days, max = Math.max(a || 0,b || 0);
      if (!(max > 0)) return '';
      const bar = (name,v) => finite(v) && v > 0 ? `<i class="${name}" style="width:${v/max*100}%"></i>` : '';
      return `<span class="mini-bars" aria-hidden="true">${bar('earlier',a)}${bar('later',b)}</span>`;
    };
    const provenance = value.archive_provenance?.synthetic ? 'Synthetic data.' : 'Unmarked archive provenance.';
    $('#comparison-result').innerHTML = `<div class="period-bubbles"><div class="bubble period fill-ink">Earlier<b class="num">${escape(periodLabel(first.baseline.from,first.baseline.to))}</b></div><div class="bubble period fill-blue">Later<b class="num">${escape(periodLabel(first.period.from,first.period.to))}</b></div></div><p class="help">${provenance} Available-day means; later minus earlier. Each metric keeps its own denominator.</p><table class="comparison"><thead><tr><th>Metric</th><th>Earlier</th><th>Later</th><th>Change</th></tr></thead><tbody>${Object.entries(names).map(([key,name]) => {
      const r = value.metrics[key]; if (!r) throw new Error('Incomplete comparison result.');
      return `<tr><td>${name}<span class="coverage">${escape(r.unit === 's' ? 'hours / minutes' : r.unit)}</span>${bars(r)}</td>${['baseline','period'].map(k => `<td>${textValue(r[k].mean_of_available_days,r.unit)}<span class="coverage">${r[k].coverage.days_with_value}/${r[k].coverage.requested_days} days</span></td>`).join('')}<td>${diff(r.change.mean_difference,r.unit)}</td></tr>`;
    }).join('')}</tbody></table><p class="help">${escape([...new Set(Object.values(value.metrics).flatMap(r => r.warnings))].map(w => w.replaceAll('_',' ')).join(' · ') || 'Complete metric coverage for both periods.')}</p><details class="basis"><summary>How this comparison is calculated</summary><p>${escape(first.basis)}</p></details>`;
  }
  async function loadRange(event) {
    event.preventDefault(); const epoch = ++loadEpoch; compareEpoch++;
    $('#workspace').hidden = true; clearError(); $('#connection').classList.remove('sr'); $('#connection').textContent = 'Reading the selected archive dates…';
    try {
      const value = await callTool('explore_sleep_recovery',{start:$('#range-from').value,end:$('#range-to').value});
      if (epoch === loadEpoch) acceptReport(value);
    } catch (e) { if (epoch === loadEpoch) { $('#connection').textContent = 'Dates not loaded.'; error(e.message); } }
  }
  async function loadComparison(event) {
    event.preventDefault(); const epoch = ++compareEpoch;
    $('#comparison-result').textContent = 'Comparing available observations…';
    try {
      const value = await callTool('compare_sleep_recovery',{start:$('#period-from').value,end:$('#period-to').value,baseline_start:$('#base-from').value,baseline_end:$('#base-to').value});
      if (epoch === compareEpoch) renderComparison(value);
    } catch (e) { if (epoch === compareEpoch) $('#comparison-result').textContent = e.message; }
  }
  root.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.window) setWindow(b.dataset.window);
    if (b.dataset.tab) showTab(b.dataset.tab);
    if (b.hasAttribute('data-prev')) selectDay(selected-1);
    if (b.hasAttribute('data-next')) selectDay(selected+1);
  });
  root.addEventListener('keydown', e => {
    if (!e.target.matches('[role="tab"]') || !['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) return;
    e.preventDefault(); const tabs = $$('[role="tab"]'); let i = tabs.indexOf(e.target);
    i = e.key === 'Home' ? 0 : e.key === 'End' ? tabs.length-1 : (i+(e.key === 'ArrowRight' ? 1 : -1)+tabs.length)%tabs.length;
    tabs[i].focus(); showTab(tabs[i].dataset.tab);
  });
  $('#range-form')?.addEventListener('submit',loadRange);
  $('#compare-form')?.addEventListener('submit',loadComparison);
  $('#day-range').addEventListener('input',e => selectDay(Number(e.target.value)));
  // Assistive technology can change a range input without firing input.
  $('#day-range').addEventListener('change',e => { if (Number(e.target.value) !== selected) selectDay(Number(e.target.value)); });
  $('#inspect-night').addEventListener('click',() => { showTab('night'); $('#tab-night').focus(); });
  $('#ask-night')?.addEventListener('click',async () => {
    if (!data.length || !capabilities.message) return;
    const d = data[selected]; $('#ask-night').disabled = true; $('#ask-status').textContent = 'Sending this selected date…';
    try {
      const synthetic = report.archive_provenance?.synthetic === true;
      const result = await request('ui/message',{role:'user',content:[{type:'text',text:`Explain the ${synthetic ? 'synthetic demo' : 'local archive'} sleep and recovery observations for ${d.date}. The explorer showed sleep ${fmt(d,'minutes')}, HRV ${fmt(d,'hrv')}, resting heart rate ${fmt(d,'rhr')}, and sleep score ${fmt(d,'score')}. Check current read-only archive queries and independent coverage. Separate observations, Garmin assessments and hypotheses; do not infer a cause from this comparison. Do not sync.`}]});
      if (result?.isError) throw new Error('The assistant did not accept the question.');
      $('#ask-status').textContent = 'Question sent to the conversation.';
    } catch (e) { $('#ask-status').textContent = e.message; }
    finally { $('#ask-night').disabled = false; }
  });
  new ResizeObserver(() => { if (tab === 'trends') drawCharts(); }).observe($('#lanes'));
  new ResizeObserver(() => drawHero()).observe($('#hero'));
  let lastHeight = 0;
  new ResizeObserver(() => {
    const height = Math.ceil(root.getBoundingClientRect().height)+16;
    if (initialized && height !== lastHeight) { lastHeight = height; notify('ui/notifications/size-changed',{height}); }
  }).observe(root);
  if (snapshotNode) {
    (async () => {
      try {
        const snapshot = JSON.parse(snapshotNode.textContent);
        if (snapshot.schema_version !== 1) throw new Error('Unsupported widget snapshot.');
        syncScheme();
        matchMedia('(prefers-color-scheme: dark)').addEventListener('change',syncScheme);
        acceptReport(snapshot.report);
        if (snapshot.comparison) renderComparison(snapshot.comparison);
        else $('#comparison-result').textContent = 'Load at least two days to compare earlier and later periods.';
        if (window.hatchWidget?.getState && window.hatchWidget?.setState) {
          let receivedState;
          window.addEventListener('hatch-widget-state', event => {
            receivedState = event.detail?.state;
            if (nativeStateReady && receivedState && !isOwnEcho(receivedState)) restoreState(receivedState);
          });
          try {
            const saved = await window.hatchWidget.getState(currentState());
            restoreState(receivedState ?? saved); nativeStateReady = true;
          } catch (_) { $('#ask-status').textContent = 'Saved selection unavailable. You can still explore this snapshot.'; }
        }
      } catch (e) { $('#workspace').hidden = true; error('Could not load the snapshot. Ask Muse to recreate the widget.'); }
    })();
    return; // Native widgets never initialize or query the MCP bridge.
  }
  window.addEventListener('message',event => {
    if (event.source !== bridge || event.data?.jsonrpc !== '2.0') return;
    const message = event.data;
    if (message.id != null && pending.has(message.id) && !message.method) {
      const p = pending.get(message.id); pending.delete(message.id); clearTimeout(p.timer);
      if (message.error) p.reject(new Error('The assistant could not complete this action. Check the connection and try again.'));
      else p.resolve(message.result);
      return;
    }
    if (!initialized) return;
    if (message.method === 'ui/notifications/host-context-changed') theme(message.params);
    if (message.method === 'ui/notifications/tool-result') {
      try { const value = unwrap(message.params); if (value.view === 'sleep_recovery') { ++loadEpoch; acceptReport(value); } }
      catch (e) { $('#workspace').hidden = true; error(e.message); }
    }
    if (message.method === 'ui/notifications/tool-cancelled') { $('#workspace').hidden = true; error('The query was cancelled. Ask the assistant to open the explorer again.'); }
    if (message.method === 'ui/resource-teardown' && message.id != null) {
      pending.forEach(p => { clearTimeout(p.timer); p.reject(new Error('Explorer closed.')); }); pending.clear();
      send({id:message.id,result:{}});
    }
  });
  request('ui/initialize',{appInfo:{name:'garmin-sleep-recovery',version:'1.0.0'},appCapabilities:{},protocolVersion:'2026-01-26'})
    .then(result => {
      if (result?.protocolVersion !== '2026-01-26') throw new Error('This host uses an unsupported MCP Apps version.');
      capabilities = result.hostCapabilities || {}; theme(result.hostContext); initialized = true;
      notify('ui/notifications/initialized',{});
      $('#connection').textContent = 'Connected. Waiting for the archive query…';
      notify('ui/notifications/size-changed',{height:Math.ceil(root.getBoundingClientRect().height)+16});
    }).catch(e => { $('#connection').textContent = 'Interactive connection unavailable.'; error(e.message); });
})();
