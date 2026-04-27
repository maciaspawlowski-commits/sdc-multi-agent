# SDC Problem Management Runbook

## Overview and Purpose
Problem Management aims to prevent incidents from happening and minimise the impact of incidents that cannot be prevented. It identifies root causes, implements permanent fixes, maintains the Known Error Database (KEDB), and drives continuous improvement across SDC services.

## Definitions
- **Problem**: The unknown underlying cause of one or more incidents.
- **Known Error**: A problem that has a documented root cause and a workaround or fix in progress.
- **KEDB**: Known Error Database — the repository of all known errors and their workarounds.
- **Root Cause**: The fundamental reason why an incident occurred (not just the immediate trigger).
- **Workaround**: A temporary measure that reduces or eliminates the impact while a permanent fix is developed.
- **Problem Manager**: The person responsible for coordinating the problem investigation.

## Problem Detection Triggers

### Reactive Triggers
- Three or more incidents with the same apparent cause within 30 calendar days
- Any P1 incident post-mortem that identifies unresolved root cause
- P2 incident occurring for the second time within 30 days (same root cause)
- Incident resolved by workaround only — permanent fix not applied
- Service Desk agent identifies pattern across multiple tickets

### Proactive Triggers
- Weekly trend analysis identifies emerging incident pattern
- Capacity forecasting identifies risk of future failure
- Availability report shows a service approaching SLA threshold
- Vendor notification of known defect affecting SDC services
- Security advisory (CVE) requiring infrastructure-wide investigation
- Service review meeting identifies recurring theme across months

### Problem Record Creation SLA
| Trigger Type | Create Problem Record Within |
|---|---|
| Post-P1 incident | 1 business day |
| Reactive (3+ incidents) | 2 business days |
| Proactive detection | 3 business days |
| Vendor advisory | 2 business days |

## Problem Record Lifecycle

### Step 1: Problem Detection and Logging
- Create Problem Record in ITSM (PRB-YYYYMMDD-NNNN)
- Link all related incident IDs (mandatory)
- Document affected services and Configuration Items (CIs) from CMDB
- Record initial symptoms observed (what users/monitoring reported)
- Initial categorisation: Application / Infrastructure / Network / Vendor / Process / Security
- Assign to Problem Manager

### Step 2: Problem Prioritisation
- Assess priority using frequency × impact:
  - **Critical**: Recurring P1 or high-frequency P2; ongoing service risk
  - **High**: Recurring P2; significant business impact; workaround in use
  - **Medium**: Recurring P3; moderate impact; workaround adequate
  - **Low**: Occasional P3/P4; minimal impact; low recurrence risk
- Priority determines investigation resourcing and timeline

### Step 3: Problem Investigation Assignment
- Problem Manager assigned (typically L3 team lead)
- Technical SME(s) assigned based on affected CI
- Vendor contacts engaged if third-party component involved
- Define investigation scope: which services, which time period, which data sources
- Set investigation timeline and first checkpoint

### Step 4: Data Collection
- Pull all related incidents — full log extracts, timeline, resolution notes
- Review application logs for the affected time window in Elastic/Splunk
- Pull infrastructure metrics from Dash0/Datadog: CPU, memory, I/O, network
- Review CMDB: confirm CI configuration was as expected
- Check change log: list all changes deployed in the 72 hours before first incident
- Interview incident responders for context not captured in tickets
- Check vendor support portal for related known issues

### Step 5: Root Cause Analysis
- Select appropriate RCA technique based on problem type (see techniques below)
- Document ALL hypotheses — do not focus only on the most obvious
- Test each hypothesis against the evidence
- Confirm root cause: state must be reproducible or clearly evidenced
- If root cause cannot be confirmed: declare "suspected root cause" and continue monitoring

### Step 6: Workaround Development
- If permanent fix will take >3 business days: develop a workaround first
- Document workaround in KEDB (see entry format below)
- Test workaround in non-production environment
- Notify Service Desk with workaround instructions
- Notify affected customers if workaround changes their workflow
- Set review date: workaround must be reviewed every 30 days

### Step 7: Known Error Declaration
- Declare Known Error when root cause confirmed AND permanent fix is deferred
- Create KEDB entry (see format below)
- Link Known Error to all open and future incidents with matching symptoms
- Update Problem Record status to "Known Error"
- Communicate Known Error to resolver teams and Service Desk

### Step 8: Permanent Fix Planning
- Raise RFC (CHG) to implement permanent resolution
- Link Problem Record to RFC
- Problem Record remains open until RFC fully implemented and verified
- If fix requires infrastructure change: follow emergency or normal change process accordingly

### Step 9: Fix Verification
- Monitor for 30 days after fix deployment: no recurrence of same incidents
- Review linked incidents: confirm all are resolved with the fix in place
- Update KEDB: mark Known Error as Resolved
- Close linked incidents if they are still open and were waiting for this fix
- Notify affected customers of permanent fix deployment

### Step 10: Problem Closure
- Verify fix effectiveness confirmed (30-day monitoring passed)
- Close KEDB entry
- Complete problem closure report (see template below)
- Trigger post-problem review for P1-equivalent problems
- Feed lessons learned into process improvement backlog

## Root Cause Analysis Techniques

### 5-Whys Method
**Best for**: Single-factor failures with a clear chain of cause and effect
**Process**:
1. State the problem clearly as the starting point
2. Ask "Why did this happen?" — document the answer
3. Ask "Why?" of the answer — repeat five times or until reaching a systemic cause
4. The final answer is typically a process, training, or design failure
**Example**:
1. Why did the API service fail? → Database connection pool exhausted
2. Why was pool exhausted? → Connection leak introduced in v2.3.1 deployment
3. Why was the leak not caught? → No connection pool monitoring in staging
4. Why no monitoring in staging? → Staging monitoring not aligned with production config
5. Why not aligned? → No monitoring parity requirement in deployment checklist
Root cause: Missing monitoring parity requirement → Fix: Update deployment checklist

### Fishbone (Ishikawa) Diagram
**Best for**: Complex failures with multiple contributing factors
**Categories to investigate**:
- **People**: Skills gaps, training deficiencies, staffing levels, fatigue, communication failure
- **Process**: Missing procedures, inadequate runbooks, approval gaps, testing gaps
- **Technology**: Hardware failure, software bugs, configuration errors, capacity limits, monitoring gaps
- **Environment**: Cloud provider issues, facility problems, third-party dependencies
- **Data**: Incorrect configuration data, stale CMDB, missing documentation
**Process**: Draw central spine with problem at head; add branches for each category; brainstorm contributing causes for each branch; identify which causes have evidence

### Fault Tree Analysis
**Best for**: Complex systems where multiple independent failures must combine
**Process**:
1. Start from the top-level failure event
2. Work backwards using AND gates (all inputs must occur) and OR gates (any input can cause output)
3. Build tree until reaching basic events (hardware failure, human error, software bug)
4. Identify minimal cut sets — the fewest failures that together cause the top event
5. Prioritise fixing the smallest cut sets first
**Output**: Tree diagram saved to Problem Record; identified minimal cut sets listed

### Timeline Analysis
**Best for**: Incidents where the sequence of events is unclear or disputed
**Process**:
1. Collect all timestamped evidence: logs, alerts, tickets, emails, chat messages
2. Build a single unified timeline sorted by timestamp
3. Mark: first symptom visible, first detection, first escalation, each significant action, resolution
4. Identify gaps: where were the biggest delays? Why?
5. Identify missed signals: were there earlier indicators that were ignored?
**Output**: Timeline document attached to Problem Record

### Change Analysis Method
**Best for**: Problems that appeared after a recent change
**Process**:
1. List all changes deployed in the 72 hours before first incident
2. For each change: assess whether it could cause the observed symptoms
3. Test rollback of suspected change in non-production if possible
4. Compare pre-change and post-change monitoring data
5. Check change test coverage: was the failure mode tested in staging?
**Output**: Change analysis table in Problem Record; link RFC to PRB

## Known Error Database (KEDB) Management

### KEDB Entry Format
```
KEDB ID: KE-NNNN
Problem Record: PRB-YYYYMMDD-NNNN
Status: Active / Under Review / Resolved
Date Created: YYYY-MM-DD
Last Reviewed: YYYY-MM-DD
Next Review Due: YYYY-MM-DD
Created By: [Name]

## Affected Services
- [Service 1]
- [Service 2]

## Affected CIs (from CMDB)
- [CI Name] version [X.Y]

## Symptoms
- [Observable symptom 1 — exactly what users see]
- [Observable symptom 2 — what monitoring shows]
- [Error message if applicable: paste exact text]

## Root Cause
[Confirmed root cause — describe the technical failure mechanism]
[If suspected: prefix with "SUSPECTED: " and note evidence level]

## Workaround (step-by-step)
1. [Step 1 — action to take]
2. [Step 2]
3. [Verify: expected outcome after workaround applied]
Note: Workaround [does / does not] fully restore service.
Estimated time to apply workaround: [X minutes]

## Permanent Fix
RFC: CHG-YYYYMMDD-NNNN
ETA: YYYY-MM-DD
Fix description: [Brief description of permanent fix]
Status: [Pending approval / CAB approved / In progress / Deployed / Verified]

## History
- YYYY-MM-DD: Created [Name]
- YYYY-MM-DD: Workaround updated [Name] — reason
- YYYY-MM-DD: Marked resolved [Name]
```

### KEDB Review Process
- All Active Known Errors reviewed every 30 days
- Review checklist:
  - [ ] Workaround still valid (test if possible)
  - [ ] Permanent fix still on track (check RFC status)
  - [ ] No new incidents since last review (if so, update impact assessment)
  - [ ] Affected services and CIs still accurate
- If workaround is no longer valid: escalate to Problem Manager immediately
- If fix is delayed beyond original ETA: notify SDM and update customer communication

### KEDB Access and Visibility
- All Service Desk agents: read access to all entries
- L2/L3 engineers: read/write access to their domain entries
- Problem Managers: full access
- Customers: selected entries shared via public knowledge base articles (sanitised, no internal details)

## Proactive Problem Management

### Weekly Trend Analysis Procedure
1. Pull incident report for past 7 days from ITSM
2. Group by: category, affected service, resolver group, resolution code
3. Compare to previous 4 weeks — identify any increasing trends
4. Flag: any category with >20% week-on-week increase
5. Identify: top 3 most frequent root cause categories
6. Cross-reference with open problem records: are trends already being addressed?
7. Output: Weekly Problem Review report → distribute to SDM and Team Leads every Monday

### Monthly Pareto Analysis
1. Pull all incidents for the month — categorised by root cause
2. Rank by frequency (most to least)
3. Calculate cumulative percentage
4. Identify the 20% of root causes driving 80% of incidents (Pareto principle)
5. For each top cause not already addressed by an active problem record: create one
6. Present findings at Monthly Service Review meeting

### Capacity and Availability Problem Prevention
- Review capacity reports monthly: identify services approaching resource limits
- Create preemptive problem record if capacity breach risk within 60 days
- Review availability reports: identify services with declining availability trend
- Cross-reference with change log: is availability decline correlated with recent changes?

### Vendor Problem Management
- Maintain list of vendor-reported known issues (portal subscriptions)
- For each vendor issue affecting SDC: create KEDB entry with vendor reference
- Engage vendor TAM (Technical Account Manager) for P1-equivalent vendor issues
- Track vendor fix ETA in KEDB — escalate if ETA slips

## Problem Closure Report Template
```
Problem Closure Report

Problem ID: PRB-YYYYMMDD-NNNN
Title: [Brief title]
Opened: YYYY-MM-DD  |  Closed: YYYY-MM-DD
Problem Manager: [Name]

## Summary
[2-3 sentence summary of the problem and its resolution]

## Root Cause Confirmed
[Full root cause statement]

## Fix Implemented
[Description of permanent fix]  |  RFC: CHG-YYYYMMDD-NNNN  |  Deployed: YYYY-MM-DD

## Incidents Linked (total: N)
[List of INC numbers linked to this problem]

## Monitoring Outcome
30-day monitoring period: YYYY-MM-DD to YYYY-MM-DD
Recurrence during monitoring: None / [N incidents — describe]
Result: [Pass / Fail — if fail, problem re-opened]

## Lessons Learned
1. [Lesson 1 — process/tool improvement identified]
2. [Lesson 2]

## Action Items Generated
| Action | Owner | Due Date | Status |
|---|---|---|---|
| [Action 1] | [Owner] | YYYY-MM-DD | Open |
```

## SLA Targets for Problem Management
| Activity | Target |
|---|---|
| Problem record creation (post-P1) | 1 business day |
| Problem record creation (reactive) | 2 business days |
| Initial RCA report (Critical) | 48 hours |
| Initial RCA report (High) | 5 business days |
| Initial RCA report (Medium/Low) | 10 business days |
| Workaround documented | 3 business days from identification |
| KEDB entry created | 1 business day after Known Error declaration |
| Permanent fix RFC raised | 10 business days from root cause confirmed |
| Post-problem review held | 10 business days from closure |
| KEDB 30-day review | Every 30 calendar days per entry |

## Integration with Other ITIL Processes

### Problem ↔ Incident
- Every P1 post-mortem must create or update a Problem Record
- Service Desk checks KEDB before escalating new incidents (may apply workaround immediately)
- Problem Manager notified when new incident matches open problem symptoms

### Problem ↔ Change
- Every permanent fix requires an RFC (CHG)
- RFC must reference the Problem Record
- Change Manager notifies Problem Manager when fix RFC is deployed
- Problem Manager verifies fix effectiveness before closing Problem Record

### Problem ↔ Configuration Management
- CMDB data is critical input to root cause analysis
- Problem Manager updates CMDB if investigation reveals inaccurate CI records
- After fix deployment: CMDB updated to reflect new CI state

## Problem Management Metrics

### Key Problem KPIs (Monthly)
| Metric | Target |
|---|---|
| Problem records created vs trigger events | ≥90% |
| RCA completed within SLA | ≥95% |
| KEDB entries with current workaround | 100% |
| KEDB entries reviewed within 30 days | ≥90% |
| Known Errors with overdue permanent fix RFC | <5% |
| Incidents linked to open problems | Tracked (no target — awareness metric) |

### Monthly Problem Report
- Number of new problems opened by trigger type
- RCA completion rate and average time-to-RCA
- KEDB size: new entries, resolved entries, total active
- Problem resolution rate: problems closed this month
- Recurring incident reduction: incidents matched to existing KEDB entries vs new problems
- Top 3 root cause categories (Pareto) with trend

## Problem Management Tooling

### ITSM Problem Record Fields
- Problem ID (auto-generated: PRB-YYYYMMDD-NNNN)
- Linked incidents (mandatory — minimum 1)
- Affected services (from CMDB service catalogue)
- Category: Application / Infrastructure / Network / Process / Vendor / Security
- Priority: Critical / High / Medium / Low
- Problem Manager (assigned staff member)
- Technical SME(s)
- Status: New / Investigation / Known Error / Fix Pending / Resolved / Closed
- Root cause category (populated at RCA completion)
- KEDB entry reference (if Known Error declared)
- Linked RFC (populated when permanent fix raised)

### Integration with Monitoring Tools
- Dash0 alerts can auto-create problem records (via ITSM webhook integration)
- Threshold: same alert pattern firing ≥3 times in 7 days → auto-creates PRB
- Auto-linked to incidents created from same alert
- Problem Manager receives automated notification with alert history attached

## Escalation Within Problem Management

### When to Escalate to SDM
- RCA overdue beyond SLA by >2 business days
- Root cause requires executive decision (e.g., vendor replacement, major architectural change)
- Permanent fix requires unplanned budget approval
- Customer requesting formal problem status update

### When to Escalate to CTO
- Root cause reveals fundamental architectural risk to multiple services
- Fix requires significant engineering investment (>2 weeks of L3 time)
- Vendor refusing to acknowledge or fix a known defect
- Problem directly linked to security vulnerability with regulatory implications
