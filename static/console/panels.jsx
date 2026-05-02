// Panels: Orchestrator graph, SLA dashboard, Black Friday sim, Chaos panel
const { useState: uS, useEffect: uE, useMemo: uM, useRef: uR } = React;

// ───────────────────── Orchestrator Graph ─────────────────────
function OrchestratorGraph({ activeAgent, recentRoute, totals }) {
  const stage = uR(null);
  const [packets, setPackets] = uS([]);

  // Node positions in % of stage
  const nodes = [
    { id: 'orchestrator', x: 18, y: 50, color: 'var(--orch)' },
    { id: 'incident',     x: 50, y: 18, color: 'var(--incident)' },
    { id: 'change',       x: 76, y: 28, color: 'var(--change)' },
    { id: 'problem',      x: 84, y: 58, color: 'var(--problem)' },
    { id: 'service',      x: 70, y: 82, color: 'var(--service)' },
    { id: 'sla',          id2: 'sla', x: 44, y: 82, color: 'var(--sla)' },
  ];

  // Animate packet on agent change
  uE(() => {
    if (!recentRoute) return;
    const id = Math.random().toString(36).slice(2);
    setPackets(p => [...p, { id, target: recentRoute, t: 0 }]);
    let raf, start = performance.now();
    const tick = (now) => {
      const t = Math.min(1, (now - start) / 1100);
      setPackets(p => p.map(pk => pk.id === id ? {...pk, t} : pk));
      if (t < 1) raf = requestAnimationFrame(tick);
      else setTimeout(() => setPackets(p => p.filter(pk => pk.id !== id)), 200);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [recentRoute]);

  const orch = nodes[0];
  const stageRect = stage.current?.getBoundingClientRect();

  return (
    <div className="graph-pane">
      <div className="pane-header">
        <span className="pane-title">Orchestrator Graph</span>
        <span className="pane-sub mono">/sdc/graph.py · LangGraph StateGraph</span>
        <span className="pane-chip live">● live routing</span>
        <div className="pane-actions">
          <span className="pane-chip">{totals.totalCalls} routes / 24h</span>
        </div>
      </div>
      <div className="graph-stage" ref={stage}>
        <svg>
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0L10 5L0 10z" fill="var(--line)"/>
            </marker>
            <marker id="arr-live" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
              <path d="M0 0L10 5L0 10z" fill="var(--signal)"/>
            </marker>
          </defs>
          {/* edges from orchestrator → each agent */}
          {nodes.slice(1).map(n => {
            const live = activeAgent === n.id;
            // curved edge
            const x1 = orch.x, y1 = orch.y, x2 = n.x, y2 = n.y;
            const cx = (x1 + x2) / 2 + (y2 < 50 ? 0 : 0);
            return (
              <path key={n.id}
                d={`M ${x1}% ${y1}% Q ${cx}% ${(y1+y2)/2}% ${x2}% ${y2}%`}
                className="graph-edge" data-flow={live}
                markerEnd={live ? 'url(#arr-live)' : 'url(#arr)'}/>
            );
          })}
          {/* Animated packets */}
          {packets.map(pk => {
            const target = nodes.find(n => n.id === pk.target);
            if (!target) return null;
            const x1 = orch.x, y1 = orch.y, x2 = target.x, y2 = target.y;
            const cx = (x1 + x2)/2;
            const cy = (y1 + y2)/2;
            const t = pk.t;
            const px = (1-t)*(1-t)*x1 + 2*(1-t)*t*cx + t*t*x2;
            const py = (1-t)*(1-t)*y1 + 2*(1-t)*t*cy + t*t*y2;
            return <circle key={pk.id} cx={`${px}%`} cy={`${py}%`} r="5" className="flow-packet" />;
          })}
        </svg>
        {nodes.map(n => {
          const A = window.AGENTS.find(a => a.id === n.id);
          const Ic = Icon[n.id] || Icon.orchestrator;
          return (
            <div key={n.id} className="graph-node"
              data-active={activeAgent === n.id || (n.id==='orchestrator' && activeAgent)}
              style={{left:`${n.x}%`, top:`${n.y}%`, ['--node-color']: n.color}}>
              <div className="graph-node-card">
                <div className="graph-node-glyph"><Ic /></div>
                <div className="graph-node-label">{A?.name || n.id}</div>
                <div className="graph-node-sub">{n.id === 'orchestrator' ? 'router' : `${window.AGENT_TOOL_COUNTS[n.id]||0} tools`}</div>
                <div className="graph-node-tools">{totals.byAgent[n.id]||0} calls</div>
              </div>
            </div>
          );
        })}
        <div className="graph-legend">
          <div className="graph-legend-row"><span className="graph-legend-swatch" style={{background:'var(--signal)'}} /> Active route</div>
          <div className="graph-legend-row"><span className="graph-legend-swatch" style={{background:'var(--line)'}} /> Available edge</div>
          <div className="graph-legend-row" style={{color:'var(--fg-3)'}}>tools_condition loop runs N times per agent</div>
        </div>
        <div className="graph-stats">
          <div className="graph-stat"><div className="graph-stat-num">{totals.totalCalls}</div><div className="graph-stat-lbl">Routes</div></div>
          <div className="graph-stat"><div className="graph-stat-num">{totals.toolCalls}</div><div className="graph-stat-lbl">Tool calls</div></div>
          <div className="graph-stat"><div className="graph-stat-num">{totals.avgLatency}ms</div><div className="graph-stat-lbl">Avg latency</div></div>
        </div>
      </div>
    </div>
  );
}

// ───────────────────── SLA Dashboard ─────────────────────
function BreachRing({ elapsed, total }) {
  const pct = Math.min(1.2, elapsed / total);
  const breached = elapsed > total;
  const color = breached ? 'var(--danger)' : pct > 0.75 ? 'var(--warn)' : 'var(--ok)';
  const r = 18, c = 2*Math.PI*r;
  const offset = c - Math.min(1, pct) * c;
  return (
    <svg className="breach-ring" viewBox="0 0 48 48">
      <circle cx="24" cy="24" r={r} fill="none" stroke="var(--bg-2)" strokeWidth="3"/>
      <circle cx="24" cy="24" r={r} fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="round"
        transform="rotate(-90 24 24)" style={{transition:'stroke-dashoffset 1s ease, stroke .2s'}}/>
      <text x="24" y="27" textAnchor="middle" fontSize="11" fontFamily="JetBrains Mono"
        fill={breached ? 'var(--danger)' : 'var(--fg-1)'} fontWeight="600">
        {breached ? '!' : `${Math.round(pct*100)}%`}
      </text>
    </svg>
  );
}

function Sparkline({ values, color = 'var(--signal)' }) {
  const n = values.length;
  const max = Math.max(...values), min = Math.min(...values);
  const pts = values.map((v,i) => `${(i/(n-1))*100},${100 - ((v-min)/(max-min||1))*100}`).join(' ');
  return (
    <svg className="spark" viewBox="0 0 100 100" preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function SLAPane() {
  const D = window.SLA_DATA;
  return (
    <div className="graph-pane">
      <div className="pane-header">
        <span className="pane-title">SLA Monitoring</span>
        <span className="pane-sub mono">November 2024 · 30-day window</span>
        <span className="pane-chip" style={{color:'var(--danger)',borderColor:'var(--danger)',background:'oklch(0.72 0.18 28 / 0.10)'}}>● 4 active breaches</span>
        <div className="pane-actions">
          <span className="pane-chip">£14.2k credits owed</span>
        </div>
      </div>
      <div className="sla-pane">
        <div className="sla-grid">
          <div className="sla-card">
            <div className="sla-card-title"><span className="ico" style={{background:'var(--danger)'}} /> Active breach watch</div>
            <div className="breach-list">
              {D.breaches.map(b => (
                <div key={b.id} className="breach-row">
                  <BreachRing elapsed={b.elapsed} total={b.total} />
                  <div className="breach-info">
                    <div className="breach-id">{b.id}</div>
                    <div className="breach-title">{b.title}</div>
                    <div className="breach-svc"><span className="priority-tag" data-p={b.priority}>{b.priority}</span>{b.service}</div>
                  </div>
                  <div className="breach-time">
                    <span className="label">DEADLINE</span>{b.deadline}
                  </div>
                  <div className="breach-time">
                    <span className="label">{b.elapsed > b.total ? 'OVER BY' : 'REMAINING'}</span>
                    <span style={{color: b.elapsed > b.total ? 'var(--danger)' : 'var(--fg-1)'}}>{Math.abs(b.total - b.elapsed)}m</span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={{display:'flex',flexDirection:'column',gap:16}}>
            <div className="sla-card">
              <div className="sla-card-title"><span className="ico" style={{background:'var(--signal)'}} /> Month at a glance</div>
              <div className="month-grid">
                {D.monthGrid.map((s, i) => (
                  <div key={i} className="month-cell"
                    data-state={s===0?'ok':s===1?'warn':s===2?'fail':'future'}
                    title={`Day ${i+1}`}/>
                ))}
              </div>
              <div style={{display:'flex',justifyContent:'space-between',marginTop:10,fontSize:10.5,color:'var(--fg-3)'}}>
                <span>Day 1</span><span className="mono">21 clean · 6 incidents · 3 future</span><span>Day 30</span>
              </div>
            </div>

            <div className="kpi-grid">
              {D.kpis.map(k => (
                <div key={k.label} className="kpi">
                  <div className="kpi-label">{k.label}</div>
                  <div className={`kpi-value ${k.dir==='up'?'fail':k.dir==='down'?'ok':''}`}>{k.value}</div>
                  <div className={`kpi-trend ${k.dir}`}>{k.dir==='up'?'▲':'▼'} {k.trend} vs Oct</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="sla-card" style={{marginTop:16,maxWidth:1100}}>
          <div className="sla-card-title"><span className="ico" style={{background:'var(--signal)'}} /> Service availability vs target</div>
          {D.services.map(s => {
            const filled = Math.min(100, (s.actual / 100) * 100);
            const cls = s.status === 'fail' ? 'fail' : s.status === 'warn' ? 'warn' : '';
            return (
              <div key={s.name} className="avail-row">
                <div>
                  <div className="avail-svc">{s.name}</div>
                  <div className="avail-target">target {s.target.toFixed(2)}% · downtime {s.downtime}</div>
                </div>
                <div className="avail-bar-wrap">
                  <div className="avail-bar"><div className={`avail-bar-fill ${cls}`} style={{width:`${(filled-99)*100}%`,minWidth:'4px'}} /></div>
                  <div className="avail-meta"><b>{s.actual.toFixed(2)}%</b><b className={cls||'ok'}>{s.status==='fail'?'BREACH':s.status==='warn'?'WATCH':'OK'}</b></div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

// ───────────────────── Black Friday Simulation ─────────────────────
// Streams real events from POST /api/simulate/black-friday (SSE).  Server
// sends step_start / step_end / error / sim_complete events.  We overlay
// the per-step results onto the visual list in window.BLACK_FRIDAY.
function SimDrawer({ open, onClose }) {
  const baseSteps = window.BLACK_FRIDAY;
  const [running, setRunning] = uS(false);
  const [stepIdx, setStepIdx] = uS(-1);
  const [doneSet, setDoneSet] = uS(new Set());
  const [openSet, setOpenSet] = uS(new Set());
  const [results, setResults] = uS({}); // step number → { agent, response, latency_ms, error }
  const abortRef = uR(null);

  uE(() => () => { if (abortRef.current) abortRef.current.abort(); }, []);
  uE(() => {
    if (!open) {
      setRunning(false); setStepIdx(-1); setDoneSet(new Set()); setOpenSet(new Set()); setResults({});
      if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
    }
  }, [open]);

  // Visual list = static names from window.BLACK_FRIDAY, overlaid with live results.
  const steps = baseSteps.map((s, i) => {
    const r = results[i + 1]; // server steps are 1-based
    return r ? { ...s, agent: r.agent || s.agent, response: r.response || s.response, latency: r.latency_ms ?? s.latency, error: r.error } : s;
  });

  async function run() {
    if (running) return;
    setRunning(true); setStepIdx(0); setDoneSet(new Set()); setResults({});
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await window.api.streamSimulation((evt) => {
        if (evt.type === 'step_start') {
          setStepIdx(evt.step - 1);
        } else if (evt.type === 'step_end') {
          setResults(prev => ({ ...prev, [evt.step]: { agent: evt.agent, response: evt.response, latency_ms: evt.latency_ms } }));
          setDoneSet(prev => new Set([...prev, evt.step - 1]));
          setOpenSet(prev => new Set([...prev, evt.step - 1]));
        } else if (evt.type === 'error') {
          setResults(prev => ({ ...prev, [evt.step]: { error: evt.error } }));
          setDoneSet(prev => new Set([...prev, evt.step - 1]));
        } else if (evt.type === 'sim_complete') {
          setStepIdx(baseSteps.length);
        }
      }, ctrl.signal);
    } catch (e) {
      if (e.name !== 'AbortError') console.error('[sim] stream failed:', e);
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  const progress = doneSet.size / steps.length;

  return (
    <div className="sim-overlay" data-open={open} onClick={(e)=>{if(e.target===e.currentTarget)onClose();}}>
      <div className="sim-drawer">
        <div className="sim-head">
          <div className="sim-glyph"><Icon.cart /></div>
          <div style={{flex:'0 0 auto'}}>
            <div className="sim-title">Black Friday Simulation</div>
            <div className="sim-sub">10 scripted queries flow through orchestrator → all five specialists</div>
          </div>
          <div className="sim-progress">
            <div className="sim-progress-track"><div className="sim-progress-bar" style={{width:`${progress*100}%`}} /></div>
            <div className="sim-progress-meta">{doneSet.size}/{steps.length} steps · {running ? 'running' : progress===1?'complete':'idle'}</div>
          </div>
          <button className="icon-btn" onClick={onClose}><Icon.close /></button>
        </div>

        <div className="sim-body">
          {steps.map((s, i) => {
            const state = doneSet.has(i) ? 'done' : (stepIdx === i && running) ? 'running' : 'pending';
            const isOpen = openSet.has(i);
            const a = agentMeta(s.agent);
            return (
              <div key={s.n} className="sim-step" data-state={state} data-open={isOpen}
                style={{['--agent-color']: a.color, ['--agent-bg']: a.bg}}>
                <div className="sim-step-head" onClick={() => setOpenSet(prev => { const n = new Set(prev); n.has(i)?n.delete(i):n.add(i); return n; })}>
                  <div className="sim-step-num">{state === 'done' ? <Icon.check /> : s.n}</div>
                  <div>
                    <div className="sim-step-title">{s.desc}</div>
                    <div className="sim-step-desc mono">{state === 'running' ? 'querying agent…' : state === 'done' ? `routed → ${s.agent}` : 'queued'}</div>
                  </div>
                  <div className="sim-step-meta">
                    <span className="sim-step-agent" style={{color:a.color, background:a.bg}}>{s.agent}</span>
                    {state === 'done' && <span className="sim-step-lat">{s.latency}ms</span>}
                  </div>
                </div>
                <div className="sim-step-body">
                  <div className="sim-q">{s.query}</div>
                  {state === 'done' && (
                    s.error
                      ? <div className="sim-r" style={{color:'var(--danger)'}}>error: {s.error}</div>
                      : <div className="sim-r">{s.response}</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="sim-foot">
          <button className="btn-primary" data-running={running} onClick={run}>
            {running ? 'Running scenario…' : progress === 1 ? '↺ Run again' : <><Icon.play /> Run scenario</>}
          </button>
          <span style={{flex:1, color:'var(--fg-3)', fontSize:11, fontFamily:"'JetBrains Mono', monospace"}}>
            {running ? 'POST /api/simulate/black-friday — streaming SSE…' :
              progress === 1 ? '✓ Replayed 10 queries through the same Redis-backed session' : 'Streams via /api/simulate/black-friday SSE'}
          </span>
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}

// ───────────────────── Chaos Panel ─────────────────────
function ChaosPanel({ open, mode, setMode, onClose, events }) {
  const [prob, setProb] = uS(50);
  const [delay, setDelay] = uS(3000);
  const M = window.CHAOS_MODES;
  return (
    <div className="chaos-panel" data-open={open}>
      <h3><span className="icon-fire"><Icon.flame /></span> Chaos Engineering</h3>
      <div className="desc">Inject failures into the live agent graph — every event surfaces as an OTel span in Dash0.</div>
      <div className="chaos-mode-grid">
        {M.map(m => (
          <button key={m.id} className="chaos-mode" aria-pressed={mode === m.id} onClick={() => setMode(m.id)}>
            <div className="chaos-mode-name">
              {m.id === 'none' && <span className="none-mark"><Icon.check /></span>}
              {m.label}
            </div>
            <div className="chaos-mode-desc">{m.desc}</div>
          </button>
        ))}
      </div>
      {(mode === 'llm_error' || mode === 'tool_error') && (
        <div className="chaos-slider"><label>Failure probability <b>{prob}%</b></label><input type="range" min="0" max="100" value={prob} onChange={e=>setProb(+e.target.value)} /></div>
      )}
      {mode === 'llm_slow' && (
        <div className="chaos-slider"><label>Injected delay <b>{delay}ms</b></label><input type="range" min="500" max="10000" step="500" value={delay} onChange={e=>setDelay(+e.target.value)} /></div>
      )}
      {events.length > 0 && (
        <div className="chaos-events">
          <div className="chaos-events-title">recent injections</div>
          {events.slice(0, 5).map((e,i) => (
            <div key={i} className="chaos-event"><time>{e.t}</time><b>{e.kind}</b><span style={{color:'var(--fg-2)'}}>{e.msg}</span></div>
          ))}
        </div>
      )}
    </div>
  );
}

Object.assign(window, { OrchestratorGraph, SLAPane, SimDrawer, ChaosPanel, BreachRing, Sparkline });
