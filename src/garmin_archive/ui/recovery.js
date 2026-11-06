/* Garmin Data Workbench MCP App. All queries go through the parent MCP host. */
(() => {
  'use strict';
  const root = document.getElementById('demo');
  const $ = selector => root.querySelector(selector);
  const $$ = selector => Array.from(root.querySelectorAll(selector));
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const finite = v => typeof v === 'number' && Number.isFinite(v);
  const duration = v => !finite(v) ? 'Unavailable' : `${Math.floor(Math.round(v) / 60)}h ${String(Math.round(v) % 60).padStart(2, '0')}m`;
  const dateLabel = value => value; // Associated calendar date, never today's profile zone.
  const stageKeys = ['deep', 'light', 'rem', 'unmeasurable'];
  const stageNames = ['Deep', 'Light', 'REM', 'Unmeasurable'];
  const fields = {minutes:'sleep_duration', need:'sleep_need', awake:'sleep_awake', score:'sleep_score', hrv:'overnight_hrv', rhr:'resting_heart_rate', charge:'body_battery_charged'};
  const panels = [
    {key:'minutes', name:'Sleep + stages', unit:'hours', height:144},
    {key:'hrv', name:'Overnight HRV', unit:'ms', height:106},
    {key:'rhr', name:'Resting heart rate', unit:'bpm', height:106},
    {key:'score', name:'Sleep score', unit:'/100', height:106},
  ];
  let data = [], report = null, selected = 0, windowSize = 0, tab = 'trends';
  let initialized = false, capabilities = {}, requestId = 0, loadEpoch = 0, compareEpoch = 0;
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
    const total = d3.sum(d.stages);
    return `<div class="stage-track" aria-label="Sleep stage composition">${d.stages.map((v,i) => `<span class="stage-piece" style="width:${total > 0 ? v / total * 100 : 0}%;background:var(--sleep-${stageKeys[i]})"></span>`).join('')}</div><div class="stage-labels">${d.stages.map((v,i) => `<span><i class="swatch" style="background:var(--sleep-${stageKeys[i]})"></i> ${stageNames[i]} <b>${duration(v)}</b></span>`).join('')}</div>`;
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
    $('#range-label').textContent = `${value.from} — ${value.to} · inclusive`;
    $('#range-from').value = value.from; $('#range-to').value = value.to;
    $('#day-range').max = data.length-1;
    $('#workspace').hidden = false;
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
    $('#freshness').innerHTML = `<p>${escape(p.freshness_meaning)}</p><ul>${lines.join('')}</ul><p>Dates are Garmin’s associated calendar dates. Historical source wall times retain their original offsets or remain unspecified.</p>`;
  }
  $('#lanes').innerHTML = panels.map(p => `<section class="lane ${p.key === 'minutes' ? 'sleep' : ''}" data-key="${p.key}"><div class="lane-head"><h3>${p.name}</h3><span class="value" id="value-${p.key}"></span></div><svg role="img" aria-label="${p.name} by calendar date. Use the selected-night slider for keyboard inspection."></svg></section>`).join('');
  function drawLane(p) {
    const lane = $(`.lane[data-key="${p.key}"]`), node = lane.querySelector('svg'), svg = d3.select(node);
    const w = lane.clientWidth, h = p.height;
    if (!w || !data.length) return;
    svg.attr('viewBox', `0 0 ${w} ${h}`); svg.selectAll('*').remove();
    const visible = data.slice(-windowSize), left = 64, right = w-12, top = 14, bottom = h-26;
    const x = d3.scalePoint().domain(visible.map(d => d.i)).range([left+14,right-14]);
    const values = visible.map(d => d[p.key]).filter(finite), extent = d3.extent(values);
    let domain;
    if (p.key === 'minutes') domain = [0,Math.max(1,Math.ceil(Math.max(0,...values,...visible.map(d => d.need).filter(finite))/60+.4))];
    else if (p.key === 'score') domain = [0,100];
    else domain = values.length ? [Math.max(0,Math.floor(extent[0]/5)*5-5),Math.ceil(extent[1]/5)*5+5] : [0,100];
    const y = d3.scaleLinear().domain(domain).range([bottom,top]);
    const step = visible.length > 1 ? (right-left-28)/(visible.length-1) : right-left;
    const bw = Math.min(26,step*.65);
    const line = accessor => d3.line().defined(d => finite(accessor(d))).x(d => x(d.i)).y(d => y(accessor(d)));
    const ticks = p.key === 'score' ? [0,50,100] : y.ticks(2);
    ticks.forEach(t => {
      svg.append('line').attr('x1',left).attr('x2',right).attr('y1',y(t)).attr('y2',y(t)).attr('stroke','var(--border)');
      svg.append('text').attr('x',left-10).attr('y',y(t)+4).attr('text-anchor','end').text(t);
    });
    svg.append('text').attr('x',0).attr('y',11).text(p.unit);
    if (x(selected) != null) svg.append('rect').attr('x',x(selected)-Math.max(bw/2+3,7)).attr('y',top).attr('width',Math.max(bw+6,14)).attr('height',bottom-top).attr('fill','var(--chart-1)').attr('opacity',.08);
    if (p.key === 'minutes') {
      visible.forEach(d => {
        if (d.minutes == null) { svg.append('text').attr('x',x(d.i)).attr('y',bottom-5).attr('text-anchor','middle').text('—'); return; }
        if (!d.stages) { svg.append('rect').attr('x',x(d.i)-bw/2).attr('width',bw).attr('y',y(d.minutes/60)).attr('height',bottom-y(d.minutes/60)).attr('fill','var(--muted-foreground)').attr('opacity',.4); return; }
        let sum = 0;
        d.stages.forEach((v,k) => { const prev = sum; sum += v/60;
          svg.append('rect').attr('x',x(d.i)-bw/2).attr('width',bw).attr('y',y(sum)).attr('height',y(prev)-y(sum)).attr('fill',`var(--sleep-${stageKeys[k]})`).attr('opacity',d.i === selected ? 1 : .72);
        });
      });
      svg.append('path').datum(visible).attr('d',line(d => d.need == null ? null : d.need/60)).attr('fill','none').attr('stroke','var(--foreground)').attr('stroke-width',1.5).attr('stroke-dasharray','3 4').attr('opacity',.65);
    } else {
      svg.append('path').datum(visible).attr('d',line(d => d[p.key])).attr('fill','none').attr('stroke','var(--chart-1)').attr('stroke-width',2);
      visible.forEach(d => {
        if (d[p.key] != null) svg.append('circle').attr('cx',x(d.i)).attr('cy',y(d[p.key])).attr('r',d.i === selected ? 4.5 : 2.5).attr('fill','var(--chart-1)');
        else svg.append('text').attr('x',x(d.i)).attr('y',bottom-3).attr('text-anchor','middle').text('—');
      });
    }
    if (!values.length) svg.append('text').attr('x',(left+right)/2).attr('y',top+20).attr('text-anchor','middle').text('No observations');
    if (x(selected) != null) svg.append('line').attr('x1',x(selected)).attr('x2',x(selected)).attr('y1',top).attr('y2',bottom).attr('stroke','var(--foreground)').attr('stroke-dasharray','2 3').attr('opacity',.5);
    const indices = [...new Set([0,Math.round((visible.length-1)/3),Math.round((visible.length-1)*2/3),visible.length-1])];
    indices.forEach(j => svg.append('text').attr('x',x(visible[j].i)).attr('y',h-7).attr('text-anchor',visible.length === 1 ? 'middle' : j === 0 ? 'start' : j === visible.length-1 ? 'end' : 'middle').text(visible[j].date.slice(5)));
    svg.append('rect').attr('x',left-12).attr('y',0).attr('width',right-left+24).attr('height',h).attr('fill','transparent');
    function pick(e) { const px = e.clientX-node.getBoundingClientRect().left; const i = visible.length === 1 ? 0 : Math.max(0,Math.min(visible.length-1,Math.round((px-left-14)/step))); selectDay(visible[i].i,false); }
    svg.on('pointerdown', function(e) { this.setPointerCapture(e.pointerId); pick(e); }).on('pointermove', e => { if (e.buttons || e.pointerType === 'mouse') pick(e); });
  }
  const drawCharts = () => panels.forEach(drawLane);
  function updateSelection(announce=false) {
    if (!data.length) return;
    const d = data[selected];
    $('#selected-date').textContent = dateLabel(d.date); $('#day-range').value = selected;
    $('#day-range').setAttribute('aria-valuetext',`${d.date}, sleep ${fmt(d,'minutes')}, HRV ${fmt(d,'hrv')}`);
    panels.forEach(p => $(`#value-${p.key}`).textContent = fmt(d,p.key));
    $('#selection-summary').innerHTML = `<div class="summary-grid">${[['Estimated need','need'],['Awake during sleep window','awake'],['Body Battery charged · day','charge']].map(([label,key]) => `<div><div class="stat-label">${label}</div><div class="stat-value">${fmt(d,key)}</div></div>`).join('')}</div>${stagesHTML(d)}`;
    $('#data-note').textContent = notes(d);
    if (announce) $('#announcement').textContent = `${d.date}, sleep ${fmt(d,'minutes')}, HRV ${fmt(d,'hrv')}`;
  }
  function selectDay(index, announce=true) {
    if (!data.length) return;
    selected = Math.max(0,Math.min(data.length-1,index));
    if (selected < data.length-windowSize) windowSize = data.length;
    updateSelection(announce); drawCharts(); if (tab === 'night') renderNight();
  }
  function setWindow(value) {
    windowSize = value === '7' ? Math.min(7,data.length) : data.length;
    selected = Math.max(data.length-windowSize,selected); $('#day-range').min = data.length-windowSize;
    $$('[data-window]').forEach(b => b.setAttribute('aria-pressed',b.dataset.window === value));
    const visible = data.slice(-windowSize);
    $('#window-label').textContent = `${visible[0].date} — ${visible.at(-1).date}`;
    $('#coverage-line').textContent = 'Available: '+panels.map(p => `${p.name} ${visible.filter(d => d[p.key] != null).length}/${visible.length}`).join(' · ');
    updateSelection(); drawCharts();
  }
  function renderNight() {
    const d = data[selected];
    $('#night').innerHTML = `<div class="toolbar"><label for="night-picker" class="small muted">Associated night date</label><select class="night-select" id="night-picker">${data.map(v => `<option value="${v.i}" ${v.i === selected ? 'selected' : ''}>${v.date}</option>`).join('')}</select></div><div class="night-hero"><div><div class="stat-label">Total sleep</div><div class="hero-value num">${fmt(d,'minutes')}</div></div><div><div class="stat-label">Estimated need</div><div class="hero-value num">${fmt(d,'need')}</div><div class="small muted">Garmin estimate, not a prescribed target</div></div></div><h3>Sleep composition</h3>${stagesHTML(d)}<p class="help">Awake: ${fmt(d,'awake')}, reported separately from total sleep.</p><div class="detail-grid">${[
      ['Overnight HRV','hrv','Nightly observation; no personal baseline inferred'],['Resting heart rate','rhr','Daily observation, not the overnight minimum'],['Sleep score','score','Garmin assessment'],['Body Battery charged','charge','Daily charge, not attributed solely to sleep']
    ].map(([name,key,note]) => `<div class="detail-item"><div class="stat-label">${name}</div><div class="stat-value">${fmt(d,key)}</div><p class="small muted">${d[key] == null ? escape(statusName(d.statuses[key])) : note}</p></div>`).join('')}</div><p class="notes">${escape(notes(d))}</p><div class="toolbar"><button class="control" data-prev ${selected === 0 ? 'disabled' : ''}>← Previous night</button><button class="control" data-next ${selected === data.length-1 ? 'disabled' : ''}>Next night →</button></div><details class="freshness"><summary>Source sleep window</summary>${Object.entries(d.timing || {}).map(([k,v]) => `<p>${escape(k.replaceAll('_',' '))}: ${escape(v || 'not returned')}</p>`).join('')}<p>Wall times without an offset have an unspecified historical zone.</p></details>`;
    $('#night-picker').addEventListener('change', e => selectDay(Number(e.target.value)));
  }
  function showTab(next) {
    tab = next; $$('.view').forEach(e => e.hidden = e.id !== next);
    $$('[data-tab]').forEach(b => { b.setAttribute('aria-selected',b.dataset.tab === next); b.tabIndex = b.dataset.tab === next ? 0 : -1; });
    if (!data.length) return;
    if (next === 'night') renderNight(); else if (next === 'trends') { setWindow(windowSize === data.length ? 'all' : '7'); }
  }
  function renderComparison(value) {
    if (value.view !== 'sleep_recovery_comparison') throw new Error('Invalid comparison result.');
    const names = {sleep_duration:'Sleep duration',overnight_hrv:'Overnight HRV',resting_heart_rate:'Resting HR',sleep_score:'Sleep score',body_battery_charged:'BB charged'};
    const first = value.metrics.sleep_duration;
    const textValue = (value,unit) => value == null ? 'Unavailable' : unit === 's' ? duration(value/60) : `${Number(value).toFixed(1)}`;
    const diff = (v,unit) => v == null ? 'Unavailable' : `${v > 0 ? '+' : ''}${unit === 's' ? (v/60).toFixed(1)+' min' : v.toFixed(1)}`;
    const provenance = value.archive_provenance?.synthetic ? 'Synthetic data.' : 'Unmarked archive provenance.';
    $('#comparison-result').innerHTML = `<div class="compare-head"><div class="period">Earlier<b>${escape(first.baseline.from)} — ${escape(first.baseline.to)}</b></div><div class="period">Later<b>${escape(first.period.from)} — ${escape(first.period.to)}</b></div></div><p class="help">${provenance} Available-day means; later minus earlier. Each metric keeps its own denominator.</p><table class="comparison"><thead><tr><th>Metric</th><th>Earlier</th><th>Later</th><th>Change</th></tr></thead><tbody>${Object.entries(names).map(([key,name]) => {
      const r = value.metrics[key]; if (!r) throw new Error('Incomplete comparison result.');
      return `<tr><td>${name}<span class="coverage">${escape(r.unit === 's' ? 'hours / minutes' : r.unit)}</span></td>${['baseline','period'].map(k => `<td>${textValue(r[k].mean_of_available_days,r.unit)}<span class="coverage">${r[k].coverage.days_with_value}/${r[k].coverage.requested_days} days</span></td>`).join('')}<td>${diff(r.change.mean_difference,r.unit)}</td></tr>`;
    }).join('')}</tbody></table><p class="help">${escape([...new Set(Object.values(value.metrics).flatMap(r => r.warnings))].map(w => w.replaceAll('_',' ')).join(' · ') || 'Complete metric coverage for both periods.')}</p><p class="help">${escape(first.basis)}</p>`;
  }
  async function loadRange(event) {
    event.preventDefault(); const epoch = ++loadEpoch; compareEpoch++;
    $('#workspace').hidden = true; clearError(); $('#connection').textContent = 'Reading the selected archive dates…';
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
  $('#range-form').addEventListener('submit',loadRange);
  $('#compare-form').addEventListener('submit',loadComparison);
  $('#day-range').addEventListener('input',e => selectDay(Number(e.target.value)));
  $('#inspect-night').addEventListener('click',() => { showTab('night'); $('#tab-night').focus(); });
  $('#ask-night').addEventListener('click',async () => {
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
  let lastHeight = 0;
  new ResizeObserver(() => {
    const height = Math.ceil(root.getBoundingClientRect().height)+16;
    if (initialized && height !== lastHeight) { lastHeight = height; notify('ui/notifications/size-changed',{height}); }
  }).observe(root);
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
