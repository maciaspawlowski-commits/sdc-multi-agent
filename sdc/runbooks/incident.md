# SDC Incident Management Runbook

## Overview and Purpose
This runbook defines the end-to-end procedure for detecting, classifying, managing, and resolving incidents at SDC. It applies to all service disruptions, degradations, and failures affecting customers or internal operations. All staff must follow this runbook when handling incidents.

## Definitions
- **Incident**: Any unplanned interruption to a service or reduction in the quality of a service.
- **Major Incident**: Any P1 or P2 incident, or any incident declared as major by the Duty Manager.
- **Incident Commander**: The person responsible for coordinating the response (usually the Duty Manager for P1/P2).
- **Resolver Group**: The technical team assigned to investigate and fix the incident.
- **War Room**: A dedicated virtual or physical space where all responders coordinate during a major incident.

## Priority Classification Matrix

### P1 – Critical
- **Criteria**: Complete service outage; >500 users affected; revenue or reputational impact; SLA breach imminent within 30 minutes
- **Response target**: 15 minutes first response; 1 hour resolution
- **Availability commitment**: 99.99% (max 4.3 min/month downtime)
- **Actions**: Immediate war room bridge; CTO notification; customer communication within 30 min; all-hands escalation
- **Examples**: Payment gateway down, authentication service offline, production database unreachable, complete API failure

### P2 – High
- **Criteria**: Major functionality degraded; >100 users affected; no viable workaround available
- **Response target**: 30 minutes first response; 4 hours resolution
- **Availability commitment**: 99.9% (max 43.8 min/month)
- **Actions**: Bridge call within 1 hour; Service Delivery Manager notified; 30-min update cadence
- **Examples**: Slow API responses >5s, intermittent login failures, reporting module unavailable, partial data loss

### P3 – Medium
- **Criteria**: Partial degradation; workaround available; <100 users affected
- **Response target**: 2 hours first response; 8 business hours resolution
- **Actions**: Assign to resolver group; notify team lead; standard ticket queue; 2-hour update cadence
- **Examples**: Single non-critical feature broken, degraded performance on non-core path, cosmetic errors with functional impact

### P4 – Low
- **Criteria**: Minor or cosmetic issues; single user affected; no business impact
- **Response target**: 4 hours first response; 3 business days resolution
- **Actions**: Standard queue; team lead review within 4 hours; no proactive communication required
- **Examples**: UI display glitch, incorrect help text, non-critical notification not sending

## Impact vs Urgency Matrix

### Impact Assessment
- **Critical Impact**: Core business service unavailable; financial loss occurring; regulatory breach risk
- **High Impact**: Significant feature unavailable; multiple teams or customers affected
- **Medium Impact**: Limited feature unavailable; workaround exists; single team affected
- **Low Impact**: Cosmetic or minor issue; single user; no operational impact

### Urgency Assessment
- **Critical Urgency**: Immediate fix required; every minute of delay causes additional loss
- **High Urgency**: Fix needed within hours; escalating impact over time
- **Medium Urgency**: Fix needed same day; stable impact not worsening
- **Low Urgency**: Fix can wait days; no risk of escalation

## Escalation Matrix

### P1 Escalation Path
- T+0: Service Desk acknowledges and pages Duty Manager
- T+15min: Duty Manager declares P1, opens war room bridge, pages L2 team
- T+30min: Service Delivery Manager joins bridge
- T+45min: Customer notification sent (if customer-facing)
- T+60min: CTO/VP Engineering paged if no resolution ETA
- T+90min: Executive sponsor loop-in

### P2 Escalation Path
- T+0: Service Desk acknowledges and assigns to L2
- T+30min: Team Lead joined if no progress
- T+60min: Service Delivery Manager notified
- T+2hr: Bridge call opened if still unresolved
- T+3hr: SDM escalates to CTO if ETA beyond SLA

### P3 Escalation Path
- T+0: Service Desk logs and assigns to resolver group
- T+4hr: Team Lead reviews if unacknowledged
- T+6hr: SDM notified if SLA at risk

### P4 Escalation Path
- T+0: Logged and queued
- T+1day: Reviewed in daily standup if no progress

## Incident Response Steps

### Step 1: Detection and Alerting
- Incident detected via: monitoring alert (Dash0/PagerDuty), customer report, internal report, automated health check
- Triage engineer reviews alert or report immediately
- Validate alert is genuine (not false positive) before creating incident
- Log incident in ITSM tool within 5 minutes of confirmed detection
- Assign INC number (format: INC-YYYYMMDD-NNNN)

### Step 2: Initial Classification
- Set priority using impact × urgency matrix
- Identify affected services and Configuration Items (CIs) in CMDB
- Record number of users affected (estimated or confirmed)
- Identify if related to recent change (check CHG log for last 24 hours)
- Assign to correct resolver group based on affected CI owner

### Step 3: Acknowledge and Communicate
- Acknowledge ticket — stop the response SLA clock recording
- Send initial notification within SLA window (see templates below)
- For P1/P2: Open Teams war room bridge #incident-INC-NNNN
- For P1/P2: Send customer-facing notification if service is externally visible
- Update ITSM ticket status to "In Progress"

### Step 4: Investigate
- Document all investigation steps with timestamps in real time
- Review monitoring dashboards (Dash0, Datadog, CloudWatch)
- Check application and infrastructure logs in Elastic/Splunk
- Review recent deployments in CI/CD pipeline
- Check KEDB for known errors matching symptoms
- Engage specialist teams as needed (DBA, Network, Security, Vendor)

### Step 5: Identify Workaround
- Determine if a workaround can restore service faster than permanent fix
- Document workaround steps clearly in the incident ticket
- Notify customers of workaround availability
- Apply workaround with change manager awareness (emergency change if needed)
- Record workaround in KEDB for future use

### Step 6: Resolve
- Apply permanent or temporary fix
- For production changes: follow emergency change procedure (ECAB approval)
- Run smoke tests after fix applied
- Verify with monitoring tools that service is restored
- Confirm with at least one affected user or automated test

### Step 7: Close
- Set ticket status to "Resolved" once fix verified
- Send resolution notification (see template below)
- 24-hour auto-close if customer does not reopen
- Complete all ticket fields: root cause category, CI affected, resolution action
- For P1/P2: trigger post-mortem creation immediately

## Communication Templates

### Initial Notification Template (P1/P2)
```
Subject: [P1/P2 INCIDENT] INC-YYYYMMDD-NNNN — [Service Name] [Impact Summary]

We are currently investigating an issue affecting [service name].

Impact: [Description of what users are experiencing]
Users affected: [Estimated number]
Started: [Time UTC]
Current status: Investigation in progress

Our team is actively working on this. Next update: [Time UTC].

Incident reference: INC-YYYYMMDD-NNNN
Bridge: [Teams link]
```

### Update Template
```
Subject: [UPDATE N] INC-YYYYMMDD-NNNN — [Service Name]

Update as of [Time UTC]:

Current status: [Investigating / Identified / Implementing fix / Monitoring]
Actions taken: [What has been done]
Current hypothesis: [What we believe is causing the issue]
Next steps: [What is being done now]
ETA: [Best estimate or "Under investigation"]

Next update: [Time UTC]
```

### Resolution Template
```
Subject: [RESOLVED] INC-YYYYMMDD-NNNN — [Service Name]

The incident affecting [service name] has been resolved as of [Time UTC].

Duration: [Start time] to [End time] ([X hours Y minutes])
Root cause: [Brief description]
Resolution: [What was done to fix it]
Prevention: [What will prevent recurrence]

We apologise for the disruption. A full post-incident review will follow within 5 business days.
```

## War Room Protocol

### Opening the War Room (P1/P2)
1. Incident Commander creates Teams channel: #incident-INC-NNNN
2. Invite: Duty Manager, SDM, relevant L2/L3 leads, customer liaison if needed
3. Pin the incident ticket URL at top of channel
4. Appoint incident commander (usually Duty Manager)
5. Appoint scribe (junior team member or SDM PA) to document all decisions

### War Room Rules
- All decisions made in the bridge — no parallel side channels
- Scribe documents every action with timestamp: "[HH:MM] [Person] [Action taken]"
- Commander provides summary update every 15 minutes
- No spectators — only people actively contributing
- Commander can remove non-contributing participants

### War Room Closure
- Commander confirms service restored and monitoring green
- Final update sent to all stakeholders
- Bridge recording saved to incident folder
- Post-mortem scheduled before bridge closes

## Application Incident Procedures

### API Service Failure
1. Check API gateway status (AWS API Gateway / Kong dashboard)
2. Verify backend service health endpoints (/health, /ready)
3. Check for recent deployment in CI/CD (last 4 hours)
4. Review error rate in Dash0 — identify specific endpoint failing
5. Check database connectivity from API service
6. If recent deployment: initiate rollback per emergency change procedure
7. If no deployment: escalate to L3 backend team with log evidence

### Authentication Service Failure
1. Check identity provider status (Okta/Auth0 status page)
2. Verify certificate validity (SSL cert expiry check)
3. Test login flow manually from multiple network locations
4. Check session store (Redis) health
5. Review auth service logs for error patterns
6. If IdP issue: contact vendor immediately, implement backup auth if available
7. Customer communication mandatory if >50 users cannot log in

### Database Incident Procedure
1. Check DB connection pool utilisation (alert threshold: >80%)
2. Verify storage space availability (alert threshold: >85% full)
3. Check for long-running queries causing locks: run slow query report
4. Review replication lag (for primary-replica setups)
5. Escalate to DBA team for P1/P2 immediately
6. If storage full: emergency disk expansion (ECAB required)
7. If connection pool exhausted: restart application pods to clear stale connections (check with app team first)

### Network / Connectivity Incident
1. Verify DNS resolution from multiple locations
2. Check CDN status (Cloudflare/Akamai status page)
3. Test connectivity from internal network vs external
4. Check firewall logs for blocked traffic
5. Review network monitoring dashboards
6. Engage network team and cloud provider if SDN/VPC issue suspected
7. Document all traceroute outputs in the incident ticket

## Infrastructure Incident Procedures

### Cloud Provider Outage
1. Check AWS/Azure/GCP status page immediately
2. Identify affected regions and services
3. Assess if failover to secondary region is possible
4. If failover available: initiate failover procedure (requires SDM approval)
5. Customer communication: reference cloud provider incident number
6. Do not attempt infra changes during active provider outage without explicit approval
7. Monitor provider updates — update customers at same cadence as provider

### Kubernetes / Container Platform
1. Check cluster health: `kubectl get nodes` and `kubectl get pods -A`
2. Identify failing pods: look for CrashLoopBackOff, OOMKilled, Pending states
3. Check resource quotas: CPU/memory limits hitting ceiling
4. Review recent Helm chart deployments
5. Check persistent volume availability
6. For OOMKilled: increase memory limits via emergency change
7. Escalate to platform team for node-level issues

## Security Incident Procedure

### Classification as Security Incident
- Any suspected data breach or unauthorised access
- Malware, ransomware, or suspicious process detected
- Unexpected privilege escalation
- External report of vulnerability being exploited

### Security Incident Response
1. **DO NOT** use standard incident bridge — use secure channel only
2. Page Security Operations Centre (SOC) immediately — 24×7 coverage
3. Declare Security Incident in ITSM with restricted visibility (SOC team only)
4. Do not share details in normal incident channels
5. Preserve evidence: do not restart systems unless absolutely necessary
6. Follow SIRP (Security Incident Response Procedure) document
7. Legal and compliance team notified by SOC lead
8. DPA notification may be required within 72 hours (GDPR)

## Post-Incident Review (PIR) Process

### PIR Trigger Criteria
- All P1 incidents (mandatory)
- Repeat P2 incidents (same root cause, second occurrence within 30 days)
- Any incident causing SLA breach
- Any incident with significant customer impact at P3 level

### PIR Timeline
- PIR document created: within 24 hours of resolution
- PIR meeting: within 5 business days of resolution
- PIR report finalised: within 2 business days of meeting
- Action items tracked in ITSM: ongoing

### PIR Document Structure
1. Incident summary (title, date, duration, priority, impact)
2. Timeline (minute-by-minute from first alert to resolution)
3. Root cause analysis (use 5-Whys or Fishbone)
4. Contributing factors (what made it worse or harder to detect)
5. What went well (keep doing these things)
6. What went poorly (process or tool failures)
7. Action items (owner, due date, priority)
8. Lessons learned (process improvements, training needs)

## SLA Clock Management

### Clock Start Rules
- Automated monitoring alert: timestamp of alert creation
- Customer email: timestamp of email receipt
- Phone call: timestamp logged by Service Desk agent
- Self-reported via portal: timestamp of portal submission

### Clock Pause Conditions
- Customer-caused delay: documented with evidence in ticket (customer unavailable, customer environment issue)
- Approved maintenance window: pre-scheduled and in ITSM calendar
- Third-party outage: vendor incident reference number required

### Clock Stop Rules
- Customer confirms resolution by email or portal
- 24-hour auto-close if no customer response after resolution notification
- For automated monitoring: green status confirmed for 30 minutes

## ITSM Ticket Mandatory Fields

### Required at Creation
- Priority (P1/P2/P3/P4)
- Affected service(s)
- Short description (max 80 chars)
- Detailed description including symptoms
- Reporter name and contact
- Number of users affected (estimated)

### Required at Resolution
- Root cause category (Application / Infrastructure / Network / Process / Vendor / Unknown)
- Resolution description (step-by-step what was done)
- Related change record (if applicable)
- CMDB CI updated (yes/no)
- Post-mortem required (yes/no — auto-set for P1)

## Incident Metrics and Reporting

### Key Incident Metrics (Monthly)
| Metric | Target | Measurement |
|---|---|---|
| P1 SLA compliance | ≥99% | Resolved within 1 hour / total P1 |
| P2 SLA compliance | ≥97% | Resolved within 4 hours / total P2 |
| MTTA P1 | ≤15 min | Avg time from creation to acknowledgement |
| MTTR P1 | ≤60 min | Avg time from creation to resolution |
| FCR rate | ≥70% | Resolved at L1 / total |
| Repeat incidents (same root cause) | <15% | Recurring / total |

### Monthly Incident Report Contents
1. Total incident volume by priority
2. SLA compliance % with trend vs prior month
3. MTTR/MTTA by priority
4. Top 5 incident categories by volume
5. P1 incident list with summary, duration, and root cause
6. Breach list with root cause and corrective action
7. Open problem records linked to incidents
8. FCR rate and drivers

## Incident Category Taxonomy

### Application Category
- Application Error: unhandled exception, crash, unexpected behaviour
- Performance Degradation: slow response, high latency, timeout
- Data Issue: incorrect data, missing data, data corruption
- Integration Failure: API error, webhook failure, third-party integration down
- Deployment Issue: broken deployment, regression introduced by release

### Infrastructure Category
- Server/VM: hardware failure, OS crash, reboot required
- Storage: disk full, I/O error, NAS/SAN unavailability
- Network: packet loss, latency, DNS failure, firewall issue
- Cloud Provider: AWS/Azure/GCP outage or service degradation
- Kubernetes: pod failure, node not ready, cluster degradation

### Security Category
- Access Control: unauthorised access detected, privilege escalation
- Data Breach: suspected or confirmed data exfiltration
- Malware: ransomware, virus, or suspicious process
- Vulnerability: active exploit of known CVE

### Process Category
- Human Error: configuration mistake, wrong command executed
- Change-Related: incident caused by or during a change
- Runbook Gap: no procedure existed for the situation encountered

## Handover Procedure (Shift Change)

### Shift Handover Checklist
At end of each shift, outgoing engineer must:
1. Update all open P1/P2 tickets with latest status and next action
2. Document any ongoing investigations: hypothesis, evidence gathered so far, next steps
3. Complete handover note in shared handover log: active incidents, pending escalations, things to watch
4. Brief incoming engineer verbally (or via recorded Teams message if async)
5. Confirm incoming engineer has accepted all open incident assignments

### Handover Note Format
```
Shift Handover — [Date] [Time UTC] — [Outgoing Engineer]

ACTIVE INCIDENTS:
- INC-NNNN [P1/P2]: [Summary]. Status: [current status]. Next action: [what incoming must do].

MONITORING ITEMS (watch, not yet incident):
- [Service]: [What to watch for]. Alert threshold: [X].

PENDING ACTIONS:
- [Action]: [Owner]. Due: [time].

NOTES: [Any context the incoming engineer should know]
```

## Incident Communication Channels

### Internal Communication
- P1/P2 war room: Teams channel #incident-INC-NNNN (auto-created)
- Operations team: Teams channel #operations-alerts
- Senior management updates: direct Teams message from SDM
- All-staff awareness (P1 only): Slack #company-announcements

### Customer Communication Channels
- Primary: email to designated customer contact (from support@sdc.com)
- Status page: incidents.sdc.com — updated for all P1/P2 affecting multiple customers
- Account Manager: briefed by SDM for enterprise customers
- Phone: SDM calls enterprise customer executive for P1 incidents >1 hour duration

### Status Page Update Cadence
- P1: Update status page within 15 minutes of declaration; update every 30 minutes
- P2: Update status page within 30 minutes; update every hour
- Resolution: Update status page within 15 minutes of resolution
- Post-incident: Update status page to "Resolved" with brief summary

## Vendor and Third-Party Incident Management

### Escalating to a Vendor
1. Check vendor's status page first (status.aws.amazon.com, etc.)
2. If not on vendor status page: open priority support ticket via vendor portal
3. Provide: SDC account ID, affected region/service, symptoms, impact, logs/evidence
4. Reference SDC's support tier (Premium/Enterprise support if applicable)
5. Escalate to vendor TAM if no response within OLA window
6. Log vendor ticket number in SDC incident ticket for traceability

### Managing a Vendor-Caused Incident
- Track vendor incident number in SDC incident ticket (mandatory)
- Update customers every 30 minutes with latest from vendor
- If vendor provides ETA: communicate to customers with appropriate caveat
- Document vendor response time for UC compliance review
- If vendor breaches UC: notify Vendor Manager immediately

### Post-Vendor Incident Actions
- UC compliance report: was vendor's response within contracted times?
- If vendor UC breached: formal notification to vendor within 5 business days
- Assess dependency risk: is this vendor causing repeated incidents? Escalate to Vendor Manager
