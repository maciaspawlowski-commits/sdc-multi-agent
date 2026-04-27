# SDC SLA Monitoring Runbook

## Overview and Purpose
This runbook defines how SDC measures, monitors, reports, and manages Service Level Agreements (SLAs), Operational Level Agreements (OLAs), and Underpinning Contracts (UCs). It covers breach prevention, breach response, penalty management, and continuous improvement of service levels.

## Definitions
- **SLA**: Service Level Agreement — contractual commitment between SDC and its customers.
- **OLA**: Operational Level Agreement — internal commitment between SDC teams.
- **UC**: Underpinning Contract — vendor/supplier commitment that supports an SLA.
- **MTTR**: Mean Time To Resolve — average time from incident creation to resolution.
- **MTTA**: Mean Time To Acknowledge — average time from incident creation to first acknowledgement.
- **FCR**: First Contact Resolution — percentage of incidents resolved without escalation beyond L1.
- **SLA Breach**: An incident or request not resolved/fulfilled within the agreed SLA target.
- **At-Risk**: A ticket where >75% of the SLA window has elapsed without resolution.

## Incident SLA Targets

### Response and Resolution Targets
| Priority | First Response | Resolution Target |
|----------|---------------|-------------------|
| P1 | 15 minutes | 1 hour |
| P2 | 30 minutes | 4 hours |
| P3 | 2 hours | 8 business hours |
| P4 | 4 hours | 3 business days |

### Availability Commitments
| Priority | Availability | Max Downtime/Month | Max Downtime/Year |
|---|---|---|---|
| P1 | 99.99% | 4.32 minutes | 52.6 minutes |
| P2 | 99.9% | 43.8 minutes | 8.77 hours |
| P3 | 99.5% | 3.65 hours | 43.8 hours |
| P4 | 99.0% | 7.3 hours | 87.6 hours |

### Business Hours Definition
- Business hours for P3/P4: Monday–Friday 08:00–18:00 local customer time
- P1/P2: 24 hours × 7 days × 365 days (no exclusions for weekends or holidays)
- Measurement period: calendar month

## Service Request SLA Targets
| Request Type | Fulfillment Target |
|---|---|
| Standard catalog items | 3 business days |
| Complex multi-team requests | 5 business days |
| New starter onboarding | 5 business days |
| Hardware (in stock) | 3 business days |
| Access removal (leavers) | Same business day |
| Emergency access (P1-linked) | 2 hours |
| Custom software/procurement | 15 business days |

## SLA Measurement Rules

### Clock Start Conditions
- Automated monitoring alert: timestamp of alert creation in ITSM
- Customer email: timestamp of email received in ITSM mailbox (not when read)
- Phone call to Service Desk: timestamp logged by agent at start of call
- Self-service portal submission: timestamp of portal submission
- Internal escalation: timestamp of escalated ticket creation

### Clock Pause Conditions (must be documented with evidence)
- **Customer unavailable**: Customer explicitly stated unavailable with return date; evidence in ticket
- **Customer environment issue**: Issue is within customer's environment; evidence from diagnostics
- **Third-party outage**: Vendor/provider outage confirmed; vendor incident reference logged
- **Approved maintenance window**: Pre-scheduled window in ITSM calendar; window must have been approved >24h before
- **Awaiting customer approval**: Formal request for approval sent; timestamp documented

### Clock Stop Conditions
- Customer confirms resolution via email, portal, or phone (agent timestamps call)
- 24-hour auto-closure after "Resolved" status set without customer objection
- For automated service monitoring: green status maintained for 30 consecutive minutes

### Exclusions from SLA
- Force Majeure events (declared by SDM with written record; must meet legal definition)
- Planned maintenance windows (published ≥5 business days in advance for P3/P4 work)
- Changes initiated by the customer that cause the incident

## OLA Targets (Internal Commitments)

### Incident OLAs
| Handover | P1 | P2 | P3 |
|----------|----|----|-----|
| Service Desk → L2 escalation response | 15 min | 30 min | 2 hours |
| L2 → L3 escalation response | 30 min | 1 hour | 4 hours |
| L2/L3 → Vendor escalation | 1 hour | 2 hours | 8 hours |
| Infrastructure team P1 bridge join | 15 min (24×7) | 30 min (24×7) | Business hours |
| DBA team P1/P2 response | 30 min (24×7) | 1 hour (24×7) | 4 hours BH |
| Security team response (security incident) | 15 min (24×7) | 30 min (24×7) | 2 hours BH |

### Change OLAs
| Activity | Target |
|---|---|
| Change Coordinator initial review | 1 business day |
| Technical review sign-off | 2 business days |
| ECAB convening (emergency) | 2 hours (24×7) |
| PIR completion | 5 business days |

### Service Request OLAs
| Activity | Target |
|---|---|
| Manager approval response | 1 business day |
| IT Security review | 2 business days |
| Procurement PO raised | 1 business day after approval |

## SLA Breach Management Process

### Automated Warning Thresholds
All warnings are automated via ITSM rules — no manual intervention required:

| Threshold | Action |
|---|---|
| 50% elapsed | Automated notification to resolver group lead |
| 75% elapsed | Alert to Team Lead + mandatory customer proactive update |
| 90% elapsed | Page Service Delivery Manager + mandatory customer update |
| 100% elapsed (breach) | SDM immediate notification + breach report auto-generated |

### Breach Response Procedure
1. SDM receives breach notification (automated page and email)
2. SDM assigns Breach Investigation Owner within 30 minutes
3. Customer notified within 1 hour of breach: apology, current status, resolution ETA, credit entitlement
4. Breach root cause documented by Investigation Owner within 2 business days
5. Corrective action plan issued by SDM within 5 business days
6. Customer receives formal breach report within 5 business days
7. Breach logged in monthly SLA report and tracked until corrective action complete

### Breach Notification Template
```
Subject: Service Level Breach — INC-YYYYMMDD-NNNN — [Service Name]

Dear [Customer],

We regret to inform you that ticket INC-YYYYMMDD-NNNN has exceeded its [Priority] 
SLA target of [X hours].

Ticket opened: [Date/Time UTC]
SLA target: [Target]
Current elapsed time: [Elapsed]
Current status: [Status]

Actions being taken:
- [Action 1]
- [Action 2]

Expected resolution: [ETA or "Under active investigation"]

We sincerely apologise for this delay. A formal breach report and credit calculation 
will follow within 5 business days.

SDC Service Delivery Manager
[Name] | [Phone] | [Email]
```

## Penalty and Credit Calculation

### Availability Breach Credits
Credit = (Actual downtime − SLA allowance) × Hourly contracted rate × Multiplier

| Breach Severity | Multiplier |
|---|---|
| First breach in 12 months | 1× |
| Second breach in 12 months (same service) | 2× |
| Third or subsequent breach | 3× |

**Example calculation**:
- P1 SLA: 99.99% (allowance: 4.32 min/month)
- Actual downtime this month: 2 hours = 120 minutes
- Breach duration: 120 − 4.32 = 115.68 minutes
- Hourly rate for service: £5,000/hour
- Credit: (115.68/60) × £5,000 × 1× = £9,640

### Response Time Breach Credits
- As defined in individual customer contracts (Contract Schedule B)
- Typically: fixed amount per breach (e.g. £500 per response SLA breach)
- Capped at: maximum 20% of monthly contract value per month

### Consecutive Breach Escalation
- 2 consecutive months breaching same SLA metric → Contract review meeting within 10 business days
- 3 consecutive months → Service Improvement Plan (SIP) mandatory, executive review required
- 4 consecutive months → Contract renegotiation or termination clause may be invoked (legal team)

## Key Performance Metrics

### Primary Monthly KPIs
| Metric | Target | Warning | Critical |
|---|---|---|---|
| P1 SLA compliance | ≥99% | <97% | <95% |
| P2 SLA compliance | ≥97% | <95% | <92% |
| P3 SLA compliance | ≥95% | <92% | <88% |
| P4 SLA compliance | ≥95% | <90% | <85% |
| MTTA P1 | ≤15 min | >10 min | >12 min |
| MTTA P2 | ≤30 min | >22 min | >27 min |
| MTTR P1 | ≤60 min | >45 min | >55 min |
| MTTR P2 | ≤4 hours | >3 hours | >3.5 hours |
| FCR rate | ≥70% | <65% | <60% |
| CSAT score | ≥4.2/5.0 | <4.0 | <3.7 |
| SR fulfillment on time | ≥95% | <92% | <88% |

### Secondary Metrics (tracked monthly)
- Percentage of incidents resolved by workaround (target: <20%)
- Percentage of incidents with incomplete root cause category (target: <5%)
- Average number of escalations per P1 incident (target: <3)
- Breach prevention rate: percentage of at-risk tickets resolved before breach (target: >80%)
- OLA compliance by team (each internal team tracked separately)

## SLA Compliance Calculation Examples

### Example 1: Monthly Compliance %
```
Data: 85 P2 incidents this month, 80 resolved within 4 hours
SLA Compliance = (80 / 85) × 100 = 94.1%
Status: WARNING — below 97% target
Action: Investigate why 5 tickets breached; check OLA compliance for L2 escalation
```

### Example 2: MTTR Calculation
```
P1 incidents this month:
  INC-001: 45 minutes
  INC-002: 72 minutes
  INC-003: 38 minutes
  INC-004: 55 minutes
MTTR = (45 + 72 + 38 + 55) / 4 = 52.5 minutes
Status: WARNING — above 45-minute warning threshold (target ≤60 min)
Trend: Was 41 min last month — increasing, requires investigation
```

### Example 3: Availability Calculation
```
Service: Payment API
Month: April 2026 (30 days = 43,200 minutes)
P1 SLA: 99.99% = max 4.32 minutes downtime allowed
Actual unplanned downtime: 18 minutes (INC-001: 12min, INC-002: 6min)
Actual availability = (43,200 - 18) / 43,200 × 100 = 99.958%
Target: 99.99%  |  Actual: 99.958%  |  Status: BREACH
Breach duration: 18 - 4.32 = 13.68 minutes over allowance
```

## Reporting Procedures

### Daily SLA Dashboard (automated)
- Refreshed hourly via ITSM reporting engine
- Shows: all open P1/P2 tickets with elapsed time and SLA status
- Shows: tickets At-Risk (>75% elapsed)
- Shows: breach count today and MTD
- Distributed to: SDM daily at 09:00 via email; always-on screen in operations centre

### Weekly SLA Report
- Published every Monday by 10:00 for the previous week
- Contents:
  - SLA compliance % by priority (with week-on-week change)
  - Breach count and list (INC number, duration, resolver team)
  - MTTR/MTTA trends (weekly average vs 4-week rolling average)
  - FCR rate
  - Top 3 resolver teams by breach count (for OLA review)
  - Actions from previous week: completed / outstanding
- Distributed to: SDM, Team Leads, Account Managers

### Monthly SLA Report
- Published within 5 business days of month end
- Contents (full report):
  1. Executive summary (1 page): compliance %, trend, highlights
  2. SLA compliance detail by priority and service
  3. Breach analysis: each breach with root cause and corrective action
  4. MTTR/MTTA analysis with trend chart (12-month view)
  5. Availability by service (compare to commitment)
  6. FCR analysis and drivers
  7. Customer Satisfaction Score (CSAT) with verbatim comments
  8. OLA compliance by team
  9. Improvement actions from last month: status update
  10. New improvement actions with owner and due date
- Reviewed at Monthly Service Review meeting with customer

### Quarterly Service Review Meeting
- Formal meeting with customer executive sponsor
- Agenda:
  1. 3-month SLA performance summary
  2. Contract compliance status (any penalty calculations)
  3. Major incidents review: post-mortems and preventive actions
  4. Service improvement initiatives: progress and roadmap
  5. Upcoming changes affecting service levels
  6. Customer satisfaction and feedback
  7. Action items review from last quarter
- Output: Signed meeting minutes with agreed actions

## Proactive SLA Risk Management

### Daily Hygiene Checklist (Operations Team)
1. Review all open P1/P2 tickets — confirm each has been updated in last 2 hours
2. Identify any P3 tickets where >50% SLA elapsed — confirm resolver is active
3. Check for any stale tickets (no update in >4 hours for P1/P2; >8 hours for P3)
4. Verify no tickets stuck in "Pending" status without a valid pause reason
5. Confirm overnight P1/P2 incidents have proper handover notes for day shift

### SLA Improvement Levers
- **High MTTR for P2**: Investigate OLA compliance — is L2 escalation happening within 30 minutes?
- **Low FCR rate**: Review L1 knowledge base for gaps; identify top 10 escalation reasons
- **Repeat breaches for same service**: Trigger Problem Management investigation
- **CSAT declining**: Review communication quality; analyse negative feedback verbatim
- **At-Risk tickets not resolved before breach**: Review alerting — are 75% warnings reaching the right people?

### Vendor UC Monitoring
- Maintain register of vendor UCs with SDC's SLA dependencies mapped
- Review vendor performance monthly (pull from vendor portals)
- Vendor UC breach → escalate to Vendor Manager immediately
- If vendor breach causes SDC SLA breach: document as third-party exclusion with evidence
- Annual UC review: renegotiate underperforming vendor contracts

## ITSM SLA Configuration Reference

### Alert Rules (ITSM Automation)
```
Rule: P1 50% Warning
  Condition: P1 ticket open AND elapsed time = 30 minutes
  Action: Email resolver group lead; add note to ticket

Rule: P1 75% At-Risk
  Condition: P1 ticket open AND elapsed time = 45 minutes
  Action: Email Team Lead + SDM; add note; set flag "At-Risk"

Rule: P1 90% Critical
  Condition: P1 ticket open AND elapsed time = 54 minutes
  Action: Page SDM + CTO; send customer update; add note

Rule: P1 Breach
  Condition: P1 ticket open AND elapsed time = 60 minutes
  Action: Page all; generate breach report; send customer notification; create breach record
```

### SLA Calendar Management
- Maintenance windows entered in ITSM calendar ≥24 hours before window
- Business hours calendar updated at start of each year with public holidays per region
- Freeze window dates entered at start of each quarter
- SLA exclusions applied automatically when ticket timestamps fall within calendar entries

## Per-Service SLA Targets

### Customer Portal (External)
- Availability target: 99.9% (P2-level)
- Response: 30 minutes for critical errors; 2 hours for degraded functionality
- Planned maintenance window: Sunday 02:00–06:00 UTC (monthly)
- RTO (Recovery Time Objective): 4 hours
- RPO (Recovery Point Objective): 1 hour

### Payment Processing Service
- Availability target: 99.99% (P1-level) — financial service, zero tolerance
- Response: 15 minutes for any degradation
- Planned maintenance: only during confirmed low-traffic windows (Friday 23:00–01:00 UTC)
- RTO: 1 hour  |  RPO: 15 minutes
- Vendor dependencies: payment gateway (separate UC with Stripe/PayPal)

### Authentication and Identity Service
- Availability target: 99.99% — login failure affects all other services
- Response: 15 minutes
- Planned maintenance: Sunday 03:00–04:00 UTC (monthly)
- RTO: 30 minutes  |  RPO: 5 minutes
- SSO dependency: Okta UC maintained separately

### Reporting and Analytics Platform
- Availability target: 99.5% (P3-level) — not real-time critical
- Response: 2 hours for unavailability; 8 hours for degraded reports
- Planned maintenance: Friday 21:00–23:00 UTC (bi-weekly)
- RTO: 8 hours  |  RPO: 24 hours (next batch run)

### Internal IT Infrastructure (Service Desk Tools)
- Availability target: 99.9% during business hours; best-effort outside
- Response: 30 minutes business hours; 2 hours outside
- Planned maintenance: weekends 08:00–12:00 UTC

## Customer-Specific SLA Addendums

### Enterprise Customer SLA Variations
Some customers negotiate SLAs above standard targets. These are tracked in contract management system and override the standard targets for their services only:
- **Tier 1 Enterprise** (>£1M ARR): P1 response 10 minutes; P2 response 20 minutes; dedicated SDM
- **Tier 2 Enterprise** (£250K–£1M ARR): Standard SLA with enhanced reporting (weekly executive summary)
- **Standard**: Default SLA targets as defined in this document

### Customer-Specific Exclusions
- Some customers have negotiated additional exclusion windows (e.g., batch processing windows)
- All customer-specific exclusions documented in contract annex and configured in ITSM per customer
- SDM maintains register of non-standard SLA terms — reviewed at contract renewal

## SLA Review and Negotiation Process

### Annual SLA Review
- Triggered: 90 days before contract renewal date
- SDM reviews: actual performance vs commitments over contract period
- If consistently exceeding targets: opportunity to tighten commitments (increases customer confidence)
- If struggling to meet targets: negotiate relaxation or request investment in improvement
- Output: revised SLA schedule for new contract period

### New Customer SLA Onboarding
1. Sales provides draft SLA targets to SDM for feasibility review
2. SDM assesses: are the targets achievable with current capacity and processes?
3. For aggressive targets: SDM provides cost estimate for additional headcount/tooling
4. Legal incorporates agreed targets into Master Service Agreement
5. ITSM configured with new customer SLA targets before go-live
6. Monitoring dashboards created for new customer
7. First SLA report generated at end of month 1

### SLA Target Setting Principles
- Targets should be ambitious but achievable: based on current MTTR + 20% improvement headroom
- New services: set at P3-level initially for first 3 months; tighten after baseline established
- Do not commit to targets that require >80% of current capacity (leaves no headroom for incidents)
- Always include exclusion clauses for third-party dependencies

## Customer Communication Scripts

### Proactive SLA Risk Notification (At-Risk)
Use when ticket reaches 75% elapsed and resolution is not imminent:
```
Subject: Update — INC-YYYYMMDD-NNNN — [Service Name]

Dear [Customer],

We want to proactively update you on ticket INC-YYYYMMDD-NNNN raised on [date].

Current status: [Status]
Actions being taken: [List current actions]
Estimated resolution: [ETA]

We are committed to resolving this within your SLA. If you have any additional 
information that could help, please reply to this email.

[SDM Name] | SDC Service Delivery
```

### SLA Breach Apology Call Script
For calls to customers following a breach (SDM-led):
1. Open: "Good morning/afternoon [name], this is [SDM name] from SDC. I'm calling personally regarding incident INC-NNNN."
2. Acknowledge: "I want to apologise that we did not meet your SLA commitment on this occasion. This is not the standard we hold ourselves to."
3. Explain: "Here is what happened and what we did to resolve it: [brief summary]."
4. Credit: "In accordance with our contract, you are entitled to a service credit of [amount]. We will apply this to your next invoice."
5. Prevention: "We have taken the following steps to prevent recurrence: [actions]."
6. Close: "You will receive a formal breach report within 5 business days. Is there anything else you would like to discuss?"

### Monthly Service Review Email Template
```
Subject: Monthly Service Review — [Month YYYY] — SDC

Dear [Customer],

Please find attached your monthly service performance report for [Month].

Headlines:
- Overall SLA compliance: [X]%
- P1 incidents: [N] (all resolved within SLA / [N] breaches)
- P2 incidents: [N] ([X]% within SLA)
- Service requests fulfilled on time: [X]%
- CSAT score: [X]/5.0

[If breaches occurred]: We have included a detailed breach analysis with corrective 
actions in Section 3 of the report.

We look forward to discussing this in our service review meeting on [date]. 
Please confirm attendance via [calendar link].

[SDM Name] | SDC Service Delivery Manager
```

## SLA Governance and Compliance

### SLA Governance Framework
- **Owner**: Service Delivery Manager
- **Review frequency**: Monthly (operational); Annual (strategic/contractual)
- **Escalation path**: SDM → VP Operations → CTO → CEO
- **Audit**: Annual SLA audit by internal quality team
- **Evidence retention**: SLA compliance records kept for duration of contract + 2 years

### Regulatory Considerations
- For customers in regulated industries (finance, healthcare): SLA commitments may have regulatory implications
- GDPR Article 32: security incident response may have mandatory reporting timelines (72 hours)
- FCA-regulated customers: availability requirements may exceed standard SLA targets
- Coordinate with Legal and Compliance team before committing to regulated customers' SLAs

### Internal SLA Governance Meetings
- **Weekly**: SDM team stand-up — review breaches, at-risk tickets, open actions (30 min)
- **Monthly**: SLA governance review — full metrics review, trend analysis, improvement planning (2 hours)
- **Quarterly**: Service review with each enterprise customer — formal governance meeting (1 hour each)
- **Annual**: SLA framework review — update targets, exclusions, measurement rules based on year's data (half-day workshop)

## Continuous Improvement Process

### SLA Improvement Cycle
1. **Measure**: Collect monthly SLA data by priority, service, and team
2. **Analyse**: Identify top 3 root causes of breaches and near-misses
3. **Improve**: Define specific actions with owners and due dates
4. **Control**: Track action completion; verify improvement in next month's data

### Common SLA Improvement Actions
| Root Cause | Improvement Action | Expected Impact |
|---|---|---|
| Late escalation from L1 to L2 | Reduce ITSM escalation threshold; add explicit OLA alert | Reduce P2 MTTR by 20% |
| Resolver unaware of at-risk ticket | Fix alert delivery (SMS backup added) | Reduce breach rate by 30% |
| Slow vendor response | Renegotiate UC; add escalation clause | Reduce P1 MTTR by 15% |
| Incorrect priority classification | L1 retraining; update classification guide | Reduce re-classifications by 50% |
| Insufficient L2 capacity | Review roster; consider additional headcount | Reduce queue depth by 40% |

### Lessons Learned from Breaches
- Every breach logged in Lessons Learned register
- Monthly review: are lessons being applied?
- Patterns in lessons → systemic improvement → process change
- Annual lessons report shared with all technical teams
