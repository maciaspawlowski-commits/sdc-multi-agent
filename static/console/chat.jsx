// Chat pane + inspector
const { useState, useEffect, useRef, useMemo } = React;

// ─────────────── helpers ───────────────
function agentMeta(id) { return (window.AGENTS || []).find(a => a.id === id) || {}; }

function AgentBadge({ id, size = 'sm' }) {
  const a = agentMeta(id);
  const px = size === 'sm' ? 18 : 24;
  return (
    <span style={{display:'inline-flex',alignItems:'center',gap:6,fontSize:size==='sm'?10.5:12,color:a.color,background:a.bg,padding:'2px 7px',borderRadius:5,fontFamily:"'JetBrains Mono', monospace"}}>
      <span style={{width:6,height:6,borderRadius:'50%',background:a.color,boxShadow:`0 0 6px ${a.color}`}} />
      {a.short || id}
    </span>
  );
}

// ─────────────── User message ───────────────
function UserMessage({ msg }) {
  return (
    <div className="msg user-msg">
      <div className="msg-head">
        <span className="msg-author">You</span>
        <span className="msg-time mono">{msg.time}</span>
      </div>
      <div className="msg-bubble">{msg.text}</div>
    </div>
  );
}

// ─────────────── Agent message card ───────────────
function AgentMessage({ msg, onInspect, isInspected, isStreaming, streamProgress }) {
  const a = agentMeta(msg.agent);
  const text = isStreaming
    ? msg.text.slice(0, Math.floor(msg.text.length * streamProgress))
    : msg.text;

  return (
    <div className="msg agent-msg" style={{['--agent-color']: a.color, ['--agent-bg']: a.bg}}>
      <div className="agent-card">
        <div className="agent-card-head">
          <span className="agent-card-glyph">{(() => { const I = Icon[msg.agent] || Icon.orchestrator; return <I />; })()}</span>
          <div>
            <div className="agent-card-name">{a.name}</div>
            <div className="agent-card-route mono">orchestrator → {msg.agent} · {msg.routingReason}</div>
          </div>
          <div className="agent-card-meta-right">
            <span>{msg.tokens?.in || '—'} ↑ {msg.tokens?.out || '—'} ↓</span>
            <span>{msg.latencyMs ? `${msg.latencyMs}ms` : (isStreaming ? 'streaming…' : '—')}</span>
          </div>
        </div>
        <div className="agent-card-body">
          {renderRichText(text)}
          {isStreaming && <span className="streaming-caret" />}
        </div>
        <div className="agent-card-foot">
          <span>{msg.time}</span>
          <span style={{margin:'0 4px'}}>·</span>
          <span>{(msg.trace || []).filter(t=>t.kind==='tool').length} tool calls</span>
          <span style={{flex:1}} />
          <button className="foot-btn" data-on={isInspected} onClick={()=>onInspect(msg.id)}>
            <Icon.trace /> {isInspected ? 'inspecting' : 'inspect trace'}
          </button>
          <button className="foot-btn"><Icon.copy /> copy</button>
        </div>
      </div>
    </div>
  );
}

// Markdown-lite — bold, headers, blockquote, lists
function renderRichText(s) {
  if (!s) return null;
  const lines = s.split('\n');
  const out = [];
  let listBuf = null;
  const flush = () => { if (listBuf) { out.push(<ul key={'ul'+out.length} style={{margin:'4px 0 6px 20px'}}>{listBuf}</ul>); listBuf = null; } };
  lines.forEach((ln, i) => {
    if (/^\* {2,}/.test(ln) || /^\d+\.\s/.test(ln)) {
      const txt = ln.replace(/^(?:\*\s+|\d+\.\s+)/, '');
      listBuf = listBuf || [];
      listBuf.push(<li key={i}>{inline(txt)}</li>);
      return;
    }
    flush();
    if (/^\*\*([^*]+)\*\*$/.test(ln)) { out.push(<h4 key={i}>{ln.replace(/\*\*/g,'')}</h4>); return; }
    if (ln.startsWith('> ')) { out.push(<blockquote key={i} style={{borderLeft:'2px solid var(--agent-color)',padding:'4px 10px',color:'var(--fg-1)',fontStyle:'italic',margin:'6px 0',background:'var(--bg-1)',borderRadius:4}}>{inline(ln.slice(2))}</blockquote>); return; }
    if (ln.trim() === '') { out.push(<div key={i} style={{height:6}} />); return; }
    out.push(<div key={i}>{inline(ln)}</div>);
  });
  flush();
  return out;
}
function inline(s) {
  const parts = s.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return parts.map((p, i) => {
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={i}>{p.replace(/\*\*/g,'')}</strong>;
    if (/^`[^`]+`$/.test(p)) return <code key={i}>{p.replace(/`/g,'')}</code>;
    return <span key={i}>{p}</span>;
  });
}

// ─────────────── Inspector ───────────────
function Inspector({ message }) {
  const [tab, setTab] = useState('trace');

  if (!message) {
    return (
      <>
        <div className="inspector-tabs">
          <button className="inspector-tab" aria-current="true"><Icon.trace /> Trace</button>
          <button className="inspector-tab"><Icon.spans /> Spans</button>
        </div>
        <div className="inspector-empty">
          Select an agent message to inspect its ReAct trace and OTel spans.
        </div>
      </>
    );
  }

  const a = agentMeta(message.agent);
  const trace = message.trace || [];
  const spans = message.spans || [];
  const tools = trace.filter(t => t.kind === 'tool');

  return (
    <>
      <div className="inspector-tabs">
        <button className="inspector-tab" aria-current={tab==='trace'} onClick={()=>setTab('trace')}><Icon.trace /> Trace <span className="count">{trace.length}</span></button>
        <button className="inspector-tab" aria-current={tab==='tools'} onClick={()=>setTab('tools')}>Tools <span className="count">{tools.length}</span></button>
        <button className="inspector-tab" aria-current={tab==='spans'} onClick={()=>setTab('spans')}><Icon.spans /> Spans <span className="count">{spans.length}</span></button>
      </div>
      <div className="inspector-body">
        <div style={{padding:'4px 4px 12px',marginBottom:8,borderBottom:'1px solid var(--line-soft)'}}>
          <div style={{fontSize:11,color:'var(--fg-3)',letterSpacing:'.06em'}}>ROUTED VIA</div>
          <div style={{display:'flex',alignItems:'center',gap:8,marginTop:6}}>
            <AgentBadge id="orchestrator" />
            <span style={{color:'var(--fg-3)'}}>→</span>
            <AgentBadge id={message.agent} />
          </div>
          <div className="mono" style={{fontSize:10.5,color:'var(--fg-3)',marginTop:6}}>{message.routingReason}</div>
        </div>

        {tab === 'trace' && <ReactTrace trace={trace} agent={message.agent} />}
        {tab === 'tools' && <ToolsList tools={tools} />}
        {tab === 'spans' && <SpanWaterfall spans={spans} agent={message.agent} />}
      </div>
    </>
  );
}

function ReactTrace({ trace, agent }) {
  return (
    <div className="trace-list">
      {trace.map((step, i) => (
        <div key={i} className="trace-step" data-kind={step.kind}>
          <div className="trace-kind">{step.kind === 'thought' ? 'Reasoning' : step.kind === 'tool' ? 'Tool call' : step.kind === 'result' ? 'Result' : 'Final answer'}</div>
          {step.kind === 'tool'
            ? <ToolCard step={step} />
            : <div className="trace-content">{step.text}</div>}
        </div>
      ))}
    </div>
  );
}

function ToolCard({ step }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="tool-card" data-open={open}>
      <div className="tool-card-head" onClick={()=>setOpen(o=>!o)}>
        <span className="tool-status-dot" data-error={!step.ok} />
        <span className="tool-name">{step.tool}</span>
        <span className="tool-latency">{step.ms}ms</span>
        <span className="tool-arrow"><Icon.chevron /></span>
      </div>
      <div className="tool-card-body">
        <dl className="kv-list">
          {Object.entries(step.args || {}).map(([k, v]) => (
            <React.Fragment key={k}>
              <dt>{k}</dt><dd>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd>
            </React.Fragment>
          ))}
        </dl>
        <div className="tool-result">{step.result}</div>
      </div>
    </div>
  );
}

function ToolsList({ tools }) {
  return (
    <div style={{display:'flex',flexDirection:'column',gap:8}}>
      {tools.map((t, i) => <ToolCard key={i} step={{...t, ok:t.ok}} />)}
    </div>
  );
}

function SpanWaterfall({ spans, agent }) {
  const total = Math.max(...spans.map(s => s.dur));
  return (
    <div style={{display:'flex',flexDirection:'column',gap:2}}>
      {spans.map((s, i) => {
        const pct = (s.dur / total) * 100;
        const a = agentMeta(s.agent);
        return (
          <div key={i} style={{['--agent-color']: a.color}}>
            <div className="span-row" style={{paddingLeft: 6 + s.depth * 12}}>
              <span className="span-icon"><Icon.bolt /></span>
              <span className="span-name">{s.name}</span>
              <span className="span-dur">{s.dur}ms</span>
            </div>
            <div className="span-bar-track" style={{marginLeft: 18 + s.depth * 12}}>
              <div className="span-bar" style={{width: `${pct}%`}} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { UserMessage, AgentMessage, Inspector, AgentBadge, agentMeta, renderRichText });
