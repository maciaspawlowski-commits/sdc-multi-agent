// SDC Operator Console — seed data
// Realistic ITSM scenarios across all five specialist agents.

window.AGENTS = [
  { id: 'orchestrator', name: 'Orchestrator',  short: 'orchestrator', color: 'var(--orch)',     bg: 'var(--orch-bg)',     desc: 'Routes requests' },
  { id: 'incident',     name: 'Incident Response', short: 'incident', color: 'var(--incident)', bg: 'var(--incident-bg)', desc: 'P1–P4, escalation, runbooks' },
  { id: 'change',       name: 'Change Management', short: 'change',   color: 'var(--change)',   bg: 'var(--change-bg)',   desc: 'RFC, CAB, freeze windows' },
  { id: 'problem',      name: 'Problem Management',short: 'problem',  color: 'var(--problem)',  bg: 'var(--problem-bg)',  desc: 'RCA, KEDB, recurring issues' },
  { id: 'service',      name: 'Service Request',   short: 'service',  color: 'var(--service)',  bg: 'var(--service-bg)',  desc: 'Access, provisioning, onboarding' },
  { id: 'sla',          name: 'SLA Monitoring',    short: 'sla',      color: 'var(--sla)',      bg: 'var(--sla-bg)',      desc: 'Availability, breach, credits' },
];

window.AGENT_TOOL_COUNTS = {
  incident: 5, change: 5, problem: 5, service: 5, sla: 5,
};

// ── Suggested prompt chips ──
window.SUGGESTIONS = [
  { agent: 'incident', label: 'Payment gateway P1 — what now?', prompt: 'Our payment gateway is completely down and approximately 450,000 customers are affected. Revenue is being lost. There is no workaround. What priority is this and what do we do?' },
  { agent: 'change',   label: 'Emergency RFC for tonight',       prompt: 'I need to push an emergency hotfix for the auth service tonight at 22:00 UTC. The fix has been validated in staging. Walk me through the CAB approval path.' },
  { agent: 'problem',  label: 'Recurring DB pool exhaustion',    prompt: 'We have had 4 incidents in the last 60 days caused by the payment DB connection pool. Should we open a problem record and what RCA method should we use?' },
  { agent: 'service',  label: 'Onboard 3 emergency contractors', prompt: 'I need monitoring and incident-management read access for 3 emergency contractors helping us with the Black Friday war room. Fastest path?' },
  { agent: 'sla',      label: 'P2 compliance is 78% — analysis', prompt: 'Our P2 SLA compliance dropped to 78% this month against a 95% target. What does that mean and what actions should we take?' },
];

// ── Sessions list ──
window.SESSIONS = [
  { id: 'sess-payment-p1',     title: 'Payment gateway P1 — Black Friday morning', agent: 'incident', when: 'Now',     active: true,  msgs: 14 },
  { id: 'sess-rfc-pool',       title: 'Emergency RFC — DB pool 100→500',          agent: 'change',   when: '12 min',   msgs: 8  },
  { id: 'sess-prb-recurring',  title: 'PRB-20241129-0008 — pool exhaustion',       agent: 'problem',  when: '38 min',   msgs: 11 },
  { id: 'sess-sla-q4',         title: 'Q4 critical-services SLA report',           agent: 'sla',      when: '1h 12m',   msgs: 6  },
  { id: 'sess-onboard-contractors', title: 'Contractor access — incident bridge',  agent: 'service',  when: '2h 03m',   msgs: 4  },
  { id: 'sess-checkout-degraded',   title: 'Checkout latency — degraded P3',       agent: 'incident', when: 'Yesterday', msgs: 9 },
  { id: 'sess-mfa-rollout',         title: 'MFA rollout RFC — staged',             agent: 'change',   when: 'Yesterday', msgs: 12 },
  { id: 'sess-mttr-trend',          title: 'MTTR trend Oct vs Nov',                agent: 'sla',      when: '2 days',    msgs: 5 },
];

// ── Active conversation (Payment Gateway P1) ──
// Mix of user + agent messages, plus a ReAct trace per agent message.
window.ACTIVE_CONVERSATION = [
  {
    id: 'm1', role: 'user', author: 'You',
    time: '08:14:02',
    text: 'Our payment service has been showing severe degradation since 06:00 UTC. Response times are above 8 seconds and growing, requests are timing out, approximately 450,000 customers are currently affected, revenue impact is confirmed, and there is no available workaround. What priority should we assign this incident, and what is our resolution deadline?',
  },
  {
    id: 'm2', role: 'agent', agent: 'incident',
    time: '08:14:06',
    routedFrom: 'orchestrator',
    routingReason: 'Severe service degradation with revenue impact and no workaround',
    latencyMs: 2840,
    tokens: { in: 412, out: 318 },
    text:
`**P1 — Payment Service Outage**

Classification: revenue-impacting outage with 450,000 users affected and no workaround in place. This is a textbook P1 under SDC's incident matrix.

**SLA window**
• First response target: 15 minutes (started at 06:00 UTC)
• Resolution deadline: **07:00 UTC** — already breached by 1h 14m

**Immediate actions** (in order)
1. Open #incident-bridge war room — page Duty Manager now if not already on the call
2. Notify CTO and Executive Sponsor — both are required at T+30 for an unresolved P1
3. Begin 15-minute update cadence to stakeholders — first comms template is ready below
4. Engage the Payment Service primary resolver group and DB-platform on-call together
5. Confirm post-mortem owner — mandatory for any P1, must be assigned within 24h of close

**Notification template**
> INC-20241129-0241 declared P1 at 06:00 UTC. Impact: payment gateway unavailable, ~450k customers, confirmed revenue loss. Resolver: payments-platform + db-platform. Bridge: #incident-bridge. Next update: 08:30 UTC.

I'd recommend pulling the SLA Monitoring Agent into this thread — you're already in breach territory and you'll want the credit calculation queued up.`,
    trace: [
      { kind: 'thought', text: '450k users affected, revenue impact, no workaround → matches the P1 criteria. I need classify_priority to confirm and calculate_resolution_deadline to compute the SLA expiry.' },
      { kind: 'tool', tool: 'classify_priority', args: { service_name: 'Payment Gateway', users_affected: 450000, has_workaround: false, revenue_impact: true }, ms: 412, ok: true,
        result: 'PRIORITY: P1\nService: Payment Gateway\nUsers affected: 450000\nWorkaround available: No\nRevenue impact: Yes\n\nSLA Targets:\n  First response: 15 minutes\n  Resolution target: 1 hour\n  Availability SLA: 99.95%\n\nImmediate actions:\n  1. Open #incident-bridge war room immediately\n  2. Page Duty Manager now\n  3. Notify CTO if not resolved within 30 minutes\n  4. 15-minute update cadence required\n  5. Post-mortem mandatory after resolution' },
      { kind: 'tool', tool: 'calculate_resolution_deadline', args: { priority: 'P1', incident_start_iso: '2024-11-29T06:00:00' }, ms: 38, ok: true,
        result: 'Priority: P1\nIncident started: 2024-11-29 06:00 UTC\nSLA window: 60 minutes\nResolution deadline: 2024-11-29 07:00 UTC\nStatus: ⚠ BREACHED (74 minutes ago)' },
      { kind: 'tool', tool: 'get_escalation_path', args: { priority: 'P1' }, ms: 22, ok: true,
        result: 'Escalation path for P1:\n\nUpdate cadence: 15-minute updates\nWar room: Teams channel #incident-bridge (open immediately)\n\nTimeline:\n  T+0:  Service Desk acknowledges, opens P1 bridge\n  T+0:  Duty Manager paged immediately\n  T+15: CTO notified if not resolved\n  T+30: Executive sponsor notified if no clear ETA\n  T+60: SLA breach — SDM prepares customer communication' },
      { kind: 'tool', tool: 'search_runbook', args: { query: 'P1 payment service outage notification template', k: 3 }, ms: 187, ok: true,
        result: '[runbooks/incident.md §3.2] P1 Notification Template\n"INC-[number] declared P1 at [time] UTC. Impact: [description]. Resolver: [team]. Bridge: #incident-bridge. Next update: [time+15min]."\n\n[runbooks/incident.md §3.4] Update cadence rules\nP1 incidents require 15-minute updates to all stakeholders for the duration of the bridge. The SDM is responsible for stakeholder list maintenance.' },
      { kind: 'answer', text: 'P1 confirmed; deadline already breached. Drafting response with escalation timeline and notification template.' },
    ],
    spans: [
      { name: 'sdc.agent.incident', dur: 2840, agent: 'incident', depth: 0 },
      { name: 'classify_priority',           dur: 412, agent: 'incident', depth: 1 },
      { name: 'calculate_resolution_deadline',dur: 38,  agent: 'incident', depth: 1 },
      { name: 'get_escalation_path',         dur: 22,  agent: 'incident', depth: 1 },
      { name: 'search_runbook',              dur: 187, agent: 'incident', depth: 1 },
      { name: 'llm.chat',                    dur: 1980, agent: 'incident', depth: 1 },
    ],
  },
  {
    id: 'm3', role: 'user', author: 'You',
    time: '08:16:21',
    text: 'Update: the auth service is now also returning 503 errors — 180,000 users hitting checkout. What escalation steps and stakeholder notifications do we need to send out right now for the combined outage?',
  },
  {
    id: 'm4', role: 'agent', agent: 'incident',
    time: '08:16:24',
    routedFrom: 'orchestrator',
    routingReason: 'Cascade failure on dependent service — escalation question',
    latencyMs: 2110,
    tokens: { in: 524, out: 286 },
    text:
`**Cascade detected — Auth Service P1 (linked to payment gateway P1)**

This is a single business event, not two unrelated incidents. Treat it as one bridge.

**Escalations to send right now**
1. **Page CTO immediately** — combined impact now exceeds 600k users. Auto-escalation rule §3.6 fires at >500k.
2. **Notify CFO and CCO** — mandatory under SDC §4.2 when revenue impact is confirmed and total impact passes the customer-experience threshold.
3. **Customer comms** — public status page banner needs to go live in the next 5 minutes. Use the "Multi-service degradation" template.
4. **Cadence change** — switch the bridge to 10-minute updates while the cascade is unresolved.

**Stakeholder notification — ready to copy**
> SEV-1 multi-service incident. Payment Gateway and Auth Service degraded since 06:00 UTC. Impact: ~630,000 customers, checkout unavailable, revenue loss confirmed. Bridge: #incident-bridge. Next update: 08:26 UTC. — SDM on-call`,
    trace: [
      { kind: 'thought', text: 'Cascade — auth depends on payment via shared DB? Need to check escalation rules for combined impact >500k and confirm whether to merge bridges.' },
      { kind: 'tool', tool: 'search_runbook', args: { query: 'cascade incident multi-service P1 escalation CTO threshold', k: 4 }, ms: 211, ok: true,
        result: '[runbooks/incident.md §3.6] Auto-escalation rules\n• Combined customer impact >500k → page CTO without delay\n• Multi-service P1 → consolidated bridge, single incident number\n• Revenue + customer-experience threshold → CFO and CCO notification\n\n[runbooks/incident.md §4.2] Stakeholder matrix\n— CFO: revenue-impacting incidents over £100k/hour estimated loss\n— CCO: any incident with >250k customer impact\n— CTO: all P1, all multi-service, any cascade' },
      { kind: 'tool', tool: 'get_escalation_path', args: { priority: 'P1' }, ms: 19, ok: true,
        result: 'P1 cadence: 15-min updates (override to 10-min for active cascade per §3.7).' },
      { kind: 'tool', tool: 'search_historical_records', args: { query: 'payment auth cascade outage Black Friday', k: 5 }, ms: 264, ok: true,
        result: '[INC-20231124-0188] Black Friday 2023 — payment + auth cascade. Total impact 580k. CTO paged at T+22m. Resolved T+96m. Post-mortem identified shared connection pool as root cause.' },
      { kind: 'answer', text: 'Drafting consolidated escalation list. Recommending merged bridge and 10-minute cadence override.' },
    ],
    spans: [
      { name: 'sdc.agent.incident', dur: 2110, agent: 'incident', depth: 0 },
      { name: 'search_runbook',              dur: 211, agent: 'incident', depth: 1 },
      { name: 'get_escalation_path',         dur: 19,  agent: 'incident', depth: 1 },
      { name: 'search_historical_records',   dur: 264, agent: 'incident', depth: 1 },
      { name: 'llm.chat',                    dur: 1610, agent: 'incident', depth: 1 },
    ],
  },
  {
    id: 'm5', role: 'user', author: 'You',
    time: '08:18:44',
    text: 'The payment P1 has now been open for 47 minutes. Critical-services target is 99.95%, November is a 30-day month. What urgency does this trigger and are we approaching breach?',
  },
  {
    id: 'm6', role: 'agent', agent: 'sla',
    time: '08:18:47',
    routedFrom: 'orchestrator',
    routingReason: 'SLA timing analysis on an open incident',
    latencyMs: 1740,
    tokens: { in: 488, out: 244 },
    text:
`**Status: 🟠 ALERT — 78% of SLA window consumed**

**Calculation**
• SLA window: 60 minutes (P1 critical service)
• Elapsed: 47 minutes → **78.3%** of the window
• Threshold crossed: ALERT (≥75%) — escalate to SDM immediately
• Time to breach: 13 minutes

**Monthly availability impact (forecast)**
• November total minutes: 43,200 (30 days × 1440)
• Critical-services budget at 99.95%: max **21.6 min** monthly downtime
• Already consumed: ~47 min (this incident alone) → **2.18× budget**
• Forecast availability if resolved at T+60: **99.86%** — confirmed breach
• Forecast availability if resolved at T+120: **99.72%** — significant breach

**Recommended actions**
1. Notify SDM the breach is imminent — credit calculation should start now
2. Begin drafting customer comms acknowledging SLA impact for top 5 contracts
3. Once resolved, route to me again with final downtime to compute exact credits owed`,
    trace: [
      { kind: 'thought', text: 'I have all the inputs: 47 min elapsed, 60 min SLA window, 30-day month, 99.95% target. Need sla_breach_warning for urgency tier and calculate_availability for forecast.' },
      { kind: 'tool', tool: 'sla_breach_warning', args: { sla_window_minutes: 60, elapsed_minutes: 47 }, ms: 14, ok: true,
        result: 'Urgency: ALERT\nThreshold crossed: 75%\nWindow consumed: 78.3%\nTime to breach: 13 minutes\nAction: Escalate to SDM immediately; begin breach communication draft.' },
      { kind: 'tool', tool: 'calculate_availability', args: { downtime_minutes: 47, period_minutes: 43200, target: 0.9995 }, ms: 9, ok: true,
        result: 'Period: 43200 min (30 days)\nDowntime: 47 min\nAvailability: 99.8912%\nTarget: 99.9500%\nStatus: ❌ BELOW TARGET\nMonthly downtime budget: 21.6 min\nBudget consumption: 217.6%' },
      { kind: 'tool', tool: 'search_runbook', args: { query: 'SLA breach communication critical services credit', k: 3 }, ms: 188, ok: true,
        result: '[runbooks/sla.md §2.4] Breach communication starts at 75% window consumption. SDM owns customer-facing comms; SLA agent owns credit calculation. Credits computed against contracted hourly value.' },
      { kind: 'answer', text: 'ALERT urgency confirmed. Forecast both T+60 and T+120 outcomes for the SDM brief.' },
    ],
    spans: [
      { name: 'sdc.agent.sla',          dur: 1740, agent: 'sla', depth: 0 },
      { name: 'sla_breach_warning',     dur: 14,   agent: 'sla', depth: 1 },
      { name: 'calculate_availability', dur: 9,    agent: 'sla', depth: 1 },
      { name: 'search_runbook',         dur: 188,  agent: 'sla', depth: 1 },
      { name: 'llm.chat',               dur: 1410, agent: 'sla', depth: 1 },
    ],
  },
];

// What the next agent answer will stream — used for the "send" demo flow.
window.STREAMING_REPLY = {
  agent: 'change',
  routingReason: 'Emergency change request for active P1 hotfix',
  latencyMs: 0, // computed live
  text:
`**Emergency Change — DB connection pool 100 → 500**

This qualifies as an **Emergency Change** under §1.4 — it is fixing an active P1 with confirmed customer impact and no service-restoring workaround available.

**Approval path (fastest route)**
1. Skip standard CAB — Emergency CAB convened by Duty Manager + on-call CAB chair
2. Verbal approval permitted with written follow-up within 24h
3. Two reviewers minimum: Duty Manager + DB Platform Lead
4. Risk assessment must accompany the approval — short-form is acceptable here

**Required artifacts (minimum viable)**
• 1-line change summary
• Rollback plan (revert pool to 100, confirm via metric)
• Verification check (pool metric stable for 10 min, error rate <0.1%)
• Post-implementation review scheduled within 5 business days

**Freeze-window check**
29 Nov falls inside the **Black Friday change freeze** (28 Nov – 2 Dec). Emergency Changes are explicitly exempted under §6.1 — proceed.

I'll generate RFC-EMG-20241129-0014 with these defaults populated. Approve to file.`,
  trace: [
    { kind: 'thought', text: 'Emergency change for active P1 — need to verify freeze window and pull the emergency CAB process.' },
    { kind: 'tool', tool: 'check_freeze_window', args: { date: '2024-11-29' }, ms: 24, ok: true,
      result: 'Date 2024-11-29 IS inside an active freeze window: BLACK_FRIDAY (2024-11-28 to 2024-12-02). Emergency Changes are exempted per §6.1. Standard and Normal Changes are blocked.' },
    { kind: 'tool', tool: 'classify_change_type', args: { is_emergency: true, has_workaround: false, tested_in_staging: true }, ms: 12, ok: true,
      result: 'Change Type: EMERGENCY\nReason: Fixing active P1 with no workaround available; staging-validated.\nApproval path: Emergency CAB (Duty Manager + on-call CAB chair). Verbal approval permitted; written follow-up within 24h required.' },
    { kind: 'tool', tool: 'search_runbook', args: { query: 'emergency CAB approval black friday freeze exemption', k: 4 }, ms: 174, ok: true,
      result: '[runbooks/change.md §1.4] Emergency Change criteria: active P1, no workaround, time-critical fix.\n[runbooks/change.md §6.1] Black Friday freeze (28 Nov – 2 Dec): Standard and Normal Changes blocked; Emergency Changes exempted but require post-implementation review within 5 business days.' },
    { kind: 'answer', text: 'Emergency CAB path confirmed. RFC-EMG-20241129-0014 ready for population.' },
  ],
  spans: [
    { name: 'sdc.agent.change',           dur: 1980, agent: 'change', depth: 0 },
    { name: 'check_freeze_window',        dur: 24,   agent: 'change', depth: 1 },
    { name: 'classify_change_type',       dur: 12,   agent: 'change', depth: 1 },
    { name: 'search_runbook',             dur: 174,  agent: 'change', depth: 1 },
    { name: 'llm.chat',                   dur: 1620, agent: 'change', depth: 1 },
  ],
};

// ── SLA pane data ──
window.SLA_DATA = {
  services: [
    { name: 'Payment Gateway',  target: 99.95, actual: 99.78, downtime: '94 min', status: 'fail' },
    { name: 'Auth Service',     target: 99.95, actual: 99.86, downtime: '60 min', status: 'fail' },
    { name: 'Core API',         target: 99.95, actual: 99.97, downtime: '13 min', status: 'ok'   },
    { name: 'Checkout',         target: 99.90, actual: 99.92, downtime: '34 min', status: 'ok'   },
    { name: 'Catalog Search',   target: 99.90, actual: 99.94, downtime: '26 min', status: 'ok'   },
    { name: 'Recommendations',  target: 99.50, actual: 99.45, downtime: '4h 47m', status: 'warn' },
    { name: 'Email Service',    target: 99.00, actual: 99.62, downtime: '2h 44m', status: 'ok'   },
    { name: 'Reporting Pipeline', target: 99.00, actual: 98.71, downtime: '9h 18m', status: 'fail' },
  ],
  // 30-day grid: 0=ok, 1=warn, 2=fail, 3=future
  monthGrid: [0,0,0,0,0,1,0,0,0,0,0,2,1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,2,2,2,3],
  kpis: [
    { label: 'MTTR (P1)',         value: '47m',   trend: '+12m', dir: 'up' },
    { label: 'MTTA (P1)',         value: '4m 12s',trend: '−18s', dir: 'down' },
    { label: 'P1 Compliance',     value: '92%',   trend: '−3pp', dir: 'up' },
    { label: 'Credits Owed',      value: '£14.2k',trend: '+£8.1k', dir: 'up' },
  ],
  breaches: [
    { id: 'INC-20241129-0241', priority: 'P1', service: 'Payment Gateway', title: 'DB connection pool exhausted under Black Friday load', elapsed: 74, total: 60, deadline: '07:00 UTC' },
    { id: 'INC-20241129-0242', priority: 'P1', service: 'Auth Service',    title: '503 cascade — checkout unavailable',                   elapsed: 32, total: 60, deadline: '08:46 UTC' },
    { id: 'INC-20241128-0188', priority: 'P2', service: 'Recommendations', title: 'Personalisation engine stalled on 12% of carts',        elapsed: 178, total: 240, deadline: '11:42 UTC' },
    { id: 'INC-20241128-0184', priority: 'P3', service: 'Reporting Pipeline', title: 'Daily exports lagging — affecting 14 customers',     elapsed: 412, total: 480, deadline: '16:30 UTC' },
  ],
};

// ── Black Friday simulation steps (matches simulation/black_friday.py + scripted responses) ──
window.BLACK_FRIDAY = [
  { n: 1, agent: 'incident', desc: 'P1 declared — payment service severe degradation',
    query: 'Our payment service has been showing severe degradation since 06:00 UTC. Response times above 8 seconds, ~450k customers affected, revenue impact confirmed, no workaround. Priority and resolution deadline?',
    response: 'P1 — payment gateway. SLA window 60 min from 06:00 UTC. Resolution deadline 07:00 UTC. Open #incident-bridge, page Duty Manager, notify CTO at T+30, executive sponsor at T+60.', latency: 2840 },
  { n: 2, agent: 'incident', desc: 'Auth service 503 cascade — escalation required',
    query: 'Update: auth service now returning 503s, ~180k users hitting checkout. Combined outage. Escalation steps and notifications?',
    response: 'Cascade detected — combined impact ~630k. Page CTO immediately (>500k threshold). Notify CFO & CCO. Switch bridge to 10-min cadence. Public status banner within 5 min.', latency: 2110 },
  { n: 3, agent: 'sla',      desc: 'SLA breach warning — 47 min elapsed on the P1',
    query: 'P1 has been open 47 min. 99.95% target, November 30-day month. Urgency level and breach proximity?',
    response: 'ALERT urgency — 78% of SLA window consumed, 13 min to breach. Forecast 99.86% if resolved at T+60 — confirmed breach. SDM should begin breach comms now.', latency: 1740 },
  { n: 4, agent: 'change',   desc: 'Freeze-window check — can we deploy the hotfix?',
    query: 'Hotfix validated in staging. Today is 29 Nov — inside a freeze? What change type for emergency production fix?',
    response: 'Inside Black Friday freeze (28 Nov – 2 Dec). Emergency Changes exempted under §6.1. Classified Emergency. Emergency CAB: Duty Manager + on-call CAB chair, verbal approval allowed.', latency: 1980 },
  { n: 5, agent: 'problem',  desc: 'Problem record — 4th recurrence threshold met?',
    query: 'This is the 4th payment DB pool failure in 60 days, all P1/P2. Open a formal problem record? Which RCA method?',
    response: 'Yes — meets recurring-incident threshold (≥3 in 90d, same root cause family). Recommend Five Whys + Fishbone. PRB-20241129-0008 created, linked to 4 source incidents.', latency: 2240 },
  { n: 6, agent: 'service',  desc: 'Emergency contractor onboarding — monitoring access',
    query: '3 emergency contractors needed for incident bridge — read access to monitoring + incident system. Fastest path?',
    response: 'Emergency Access Request, expedited path. Approver: Duty Manager (single approval). Required: legal name, ID, sponsor. Access via SSO group sdc-emergency-readonly (24h auto-expiry).', latency: 1640 },
  { n: 7, agent: 'sla',      desc: 'Availability + credit calculation — 154 min downtime',
    query: '154 min downtime this month so far. Target 99.95%. 30-day month. Top customer billed at £500/hour. Calculate availability and credit owed.',
    response: 'Availability: 99.6435%. ❌ Below 99.95% target. Breach confirmed. Customer credit: 154 min × (£500/60) × 1.5× breach multiplier = £1,925 + 50% goodwill = £2,887.50.', latency: 1490 },
  { n: 8, agent: 'problem',  desc: 'KEDB entry — DB pool exhaustion under peak load',
    query: 'Root cause confirmed: payment DB pool exhausted by 3× normal Black Friday traffic at 100-conn hard cap. Create KEDB entry.',
    response: 'KEDB-20241129-0008 created. Title: "Payment DB pool exhaustion under peak traffic." Workaround: restart DB proxy. Permanent fix: pool size 100→500. ETA 2h. Linked to PRB-0008.', latency: 1820 },
  { n: 9, agent: 'change',   desc: 'Emergency RFC — pool 100 → 500',
    query: 'Emergency RFC: increase payment DB pool 100→500. Not staging-tested due to time pressure. Live DB config change. Active P1.',
    response: 'RFC-EMG-20241129-0014 — Emergency. Verbal approval allowed. Required: rollback plan (revert to 100, verify in 10 min), monitoring plan (pool metric, error rate). PIR scheduled within 5 business days.', latency: 1980 },
  { n:10, agent: 'incident', desc: 'P1 closure + post-incident review',
    query: 'Payment service recovered at 08:34 UTC. Total downtime 154 min. Steps to formally close P1? PIR process and timeline?',
    response: 'Close: confirm 30-min stable monitoring, file RFO, notify all stakeholders, archive bridge transcript. PIR: blameless format, owner = SDM, draft within 5 business days, exec review within 10 days, KEDB cross-link to PRB-0008.', latency: 2520 },
];

// ── Status / footer telemetry ──
window.STATUS_DATA = {
  ollama: 'llama3.2',
  langgraph: '0.3.21',
  observability: 'Dash0 · OTel 1.27',
  sessionId: 'a4f8c190',
  build: 'sdc-agents@5.2.0',
};

// chaos modes
window.CHAOS_MODES = [
  { id: 'none',        label: 'Off',        desc: 'Normal operation' },
  { id: 'llm_slow',    label: 'LLM Slow',   desc: 'Add artificial latency to every LLM call' },
  { id: 'llm_error',   label: 'LLM Errors', desc: 'Random LLM failures' },
  { id: 'tool_error',  label: 'Tool Errors',desc: 'Random tool failures' },
  { id: 'rag_degraded',label: 'RAG Degraded',desc: 'Force empty RAG results' },
];
