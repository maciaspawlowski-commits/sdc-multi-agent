# SDC Change Management Runbook

## Overview and Purpose
This runbook governs all changes to SDC's production and non-production environments. It ensures changes are planned, assessed, approved, implemented safely, and reviewed. All changes — no matter how small — must follow this process unless pre-approved as standard changes.

## Definitions
- **Change**: The addition, modification or removal of anything that could affect IT services.
- **RFC (Request for Change)**: The formal record of a proposed change.
- **CAB (Change Advisory Board)**: The body that reviews and approves Normal changes.
- **ECAB (Emergency CAB)**: A subset of CAB convened urgently for emergency changes.
- **PIR (Post-Implementation Review)**: Review conducted after change completion.
- **Freeze Window**: A period during which changes are prohibited except emergencies.

## Change Types Overview

### Standard Change
- Pre-approved, low-risk, well-documented repeatable procedure
- Follows a pre-approved catalogue entry exactly — any deviation requires reclassification
- No CAB approval required
- Must be logged in ITSM for audit purposes
- Examples: routine OS patching from approved patch list, SSL certificate renewal, DNS A-record update, standard firewall rule from approved template, password reset for service account

### Normal Change – Minor
- Low risk, limited scope, not pre-approved as standard
- Requires CAB assessment at next scheduled meeting
- Minimum 72 hours notice before implementation
- Examples: application configuration parameter change, adding a DB index, modifying user role permissions, updating a monitoring threshold

### Normal Change – Major
- Higher risk, significant business impact, or architectural change
- Full CAB review with detailed documentation
- Minimum 5 business days lead time for CAB submission
- Examples: new software release to production, infrastructure migration, database schema change, third-party integration update, network topology change

### Emergency Change
- Urgent fix required to restore service or prevent imminent outage
- Triggered by P1/P2 incident or critical security vulnerability (CVE with active exploit)
- ECAB approval required: Service Delivery Manager + Technical Lead minimum
- ECAB convened within 2 hours, 24×7
- Must be retrospectively documented within 24 hours of completion

## Standard Change Catalogue

### SC-001: OS Security Patching (Linux)
- **Scope**: Approved patch list only, no version upgrades
- **Window**: Saturday 02:00–06:00 UTC
- **Rollback**: Snapshot taken automatically before patch (VMware/AWS)
- **Verification**: Service health endpoint returns 200 after reboot
- **Approver**: Patch Manager (pre-approved)

### SC-002: SSL Certificate Renewal
- **Scope**: Renewal of existing certificates (no CN change)
- **Window**: Any time, 15-minute service disruption expected
- **Rollback**: Revert to previous certificate within 5 minutes
- **Verification**: SSL Labs scan shows valid certificate
- **Approver**: Security team lead (pre-approved)

### SC-003: DNS A-Record Update
- **Scope**: Updating existing A-record IP address (no new records)
- **Window**: Any time, propagation takes up to 48 hours
- **Rollback**: Revert DNS record (takes up to 48 hours)
- **Verification**: nslookup confirms new IP from multiple locations
- **Approver**: Network team lead (pre-approved)

### SC-004: User Access Role Change (Standard Roles)
- **Scope**: Adding/removing standard role from existing user
- **Window**: Business hours only
- **Rollback**: Remove added role immediately
- **Verification**: User confirms access works as expected
- **Approver**: Line manager (pre-approved)

### SC-005: Monitoring Threshold Adjustment
- **Scope**: Adjusting alert thresholds within ±20% of current value
- **Window**: Business hours, requires 24h observation period after
- **Rollback**: Revert threshold to previous value
- **Verification**: No false positives in 24h observation period
- **Approver**: Monitoring team lead (pre-approved)

## CAB Schedule and Submission Process

### CAB Meeting Schedule
- **Tuesday CAB**: 14:00 UTC — standard and minor normal changes
- **Thursday CAB**: 10:00 UTC — major changes and complex reviews
- Submissions deadline: 48 hours before the meeting
- Minutes published within 4 hours of meeting end

### CAB Members
- Chair: Service Delivery Manager (mandatory)
- Change Manager: owns the process (mandatory)
- Infrastructure Lead, Application Lead, Security Lead (mandatory)
- Network Lead, DBA Lead (as required by change type)
- Customer representative (for major customer-impacting changes)
- Business stakeholder (for changes affecting business processes)

### CAB Submission Checklist
- [ ] RFC form completed in ITSM (all mandatory fields filled)
- [ ] Detailed description of change and business justification
- [ ] Risk assessment form completed (probability × impact)
- [ ] Impact assessment: affected services, users, upstream/downstream dependencies
- [ ] Rollback plan: step-by-step procedure with estimated time
- [ ] Test evidence: test environment results, test cases executed and passed
- [ ] Implementation schedule: date, window start/end, responsible engineer
- [ ] Communication plan: who to notify, when, channel (email/Teams/status page)
- [ ] Stakeholder sign-offs obtained: business owner, technical lead
- [ ] CMDB impact: which CIs will be changed

### CAB Presentation Format
1. Change summary (2 minutes): what, why, when, who
2. Risk and impact (2 minutes): risk rating, mitigations, business impact
3. Rollback (1 minute): confirm rollback is tested and available
4. Q&A (5 minutes): CAB member questions

## RFC Lifecycle

### Step 1: RFC Creation
- Submit RFC in ITSM — CHG number auto-assigned (CHG-YYYYMMDD-NNNN)
- Complete all mandatory fields (see checklist above)
- Attach all documentation (risk assessment, test evidence, rollback plan)
- Set implementation date/window (must be future date)
- Tag all affected CIs from CMDB

### Step 2: Change Coordinator Initial Review
- Within 1 business day of submission
- Validates completeness of all mandatory fields
- Confirms classification is correct (standard/minor/major/emergency)
- Returns RFC if incomplete — provides specific list of missing items
- RFC clock paused until resubmission
- Schedules for appropriate CAB or routes to standard change approver

### Step 3: Technical Review
- Technical peer review by relevant team lead
- Validates implementation plan is technically sound
- Confirms rollback plan is executable and has been tested
- Signs off in ITSM (digital signature with timestamp)

### Step 4: CAB/ECAB Approval
- RFC presented at CAB meeting
- CAB decision options:
  - **Approved**: Proceed as planned
  - **Approved with conditions**: Approved subject to additional steps (documented)
  - **Deferred**: More information required — resubmit for next CAB
  - **Rejected**: Change not approved — reason documented, cannot proceed
- Approval recorded in ITSM with approver names and decision timestamp

### Step 5: Pre-Implementation
- Change engineer notified of approval and confirmation of window
- Notify all stakeholders per communication plan (at least 24 hours before)
- Confirm implementation team availability for window
- Verify rollback resources available during window (snapshots, backups)
- Confirm monitoring team on standby during window
- Pre-implementation checklist signed off by Change Coordinator

### Step 6: Implementation
- Execute change within approved window ONLY
- Document each step as executed with exact timestamps
- Note any deviations from plan immediately to Change Coordinator
- Monitor service health metrics throughout
- Post-implementation smoke test: run verification checklist

### Step 7: Rollback Decision
Trigger rollback if ANY of the following occur:
- Change window exceeded by >20%
- Monitoring shows service degradation after implementation
- Smoke test failures after implementation
- Business stakeholder requests halt
- Unexpected behaviour observed not covered in risk assessment

### Step 8: Post-Implementation Review
- PIR due within 5 business days
- Verify all change objectives met
- Document deviations from plan
- Update CMDB with new CI configuration
- Lessons learned fed into standard change catalogue if applicable
- Close RFC with outcome and PIR reference

## Risk Assessment Methodology

### Risk Rating Matrix
| Likelihood \ Impact | Negligible | Minor | Moderate | Major | Critical |
|---|---|---|---|---|---|
| Rare | Very Low | Low | Low | Medium | High |
| Unlikely | Low | Low | Medium | High | Critical |
| Possible | Low | Medium | Medium | High | Critical |
| Likely | Medium | Medium | High | Critical | Critical |
| Almost Certain | Medium | High | High | Critical | Critical |

### Risk Factors Checklist
- **Reversibility**: Can the change be fully rolled back within the window? (reduces risk)
- **Test coverage**: Has the change been tested in a production-like environment? (reduces risk)
- **Data changes**: Does the change modify or migrate data? (increases risk)
- **Number of services**: How many services are affected? (increases risk proportionally)
- **Time of day**: Is the window during low-traffic period? (reduces risk)
- **Team experience**: Has this team done this type of change before? (reduces risk)
- **Vendor support**: Is vendor support available during the window? (reduces risk for vendor changes)
- **Monitoring**: Will active monitoring be in place during and after? (reduces risk)

## Change Freeze Windows

### Scheduled Freeze Periods (Annual Calendar)
- **Q1 Quarter-End**: Last 5 business days of March
- **Q2 Quarter-End**: Last 5 business days of June
- **Q3 Quarter-End**: Last 5 business days of September
- **Q4 Quarter-End / Year-End**: Last 10 business days of December
- **Major Release Windows**: 48 hours before and after (announced 2 weeks ahead)
- **Holiday Periods**: Christmas/New Year (announced annually)

### Freeze Window Rules
- Only Emergency Changes permitted during freeze windows
- Emergency Change requires ECAB approval (SDM + CTO for year-end freeze)
- All teams notified of freeze dates at start of each quarter
- Calendar published on intranet and pinned in #change-management Teams channel
- Exception process: written request to SDM with business justification

## Emergency Change Process

### When to Use
- Active P1/P2 incident requiring a production change to resolve
- Critical security vulnerability with active exploit in the wild
- Regulatory/compliance emergency requiring immediate action

### ECAB Approval Process
1. Change engineer contacts Change Manager via emergency phone line
2. Change Manager convenes ECAB via Teams within 2 hours
3. Minimum ECAB quorum: SDM + Technical Lead + Security Lead
4. Change engineer presents: what, why, risk, rollback, time required
5. ECAB votes (majority): Approved / Rejected
6. If approved: change can proceed immediately
7. Implementation monitored live by at least one ECAB member

### Post-Emergency Documentation
- Full RFC created within 24 hours
- PIR mandatory for all emergency changes
- Lessons learned: was this a genuine emergency or could it have been planned?

## Rollback Procedures by Change Type

### Application Deployment Rollback
1. Identify current deployment version
2. Trigger rollback in CI/CD pipeline (blue-green switch or Helm rollback)
3. Command: `helm rollback [release-name] [revision]` or pipeline rollback button
4. Verify pods are healthy: `kubectl rollout status deployment/[name]`
5. Run smoke tests
6. Notify Change Manager and update RFC

### Database Migration Rollback
1. Apply reverse migration script (must be prepared before implementation starts)
2. Verify row counts match pre-migration baseline
3. Run application connectivity tests
4. Check application logs for any residual errors
5. Note: some migrations may be irreversible — document this clearly in RFC

### Infrastructure Change Rollback
1. Revert to snapshot (VM) or previous Terraform state
2. Command: `terraform apply -target=[resource] -var="[previous_config]"`
3. For AWS: restore from snapshot via Console or CLI
4. Verify services are accessible from monitoring
5. DNS/load balancer changes may have TTL propagation delay — document expected time

### Configuration Change Rollback
1. Restore previous configuration file from version control (git revert)
2. Apply via configuration management tool (Ansible/Chef/Puppet)
3. Verify configuration applied: run idempotency check
4. Smoke test affected service

## Communication Plan Templates

### Pre-Change Notification (customer-facing)
```
Subject: Planned Maintenance — [Service Name] — [Date] [Time UTC]

Dear [Customer],

We will be performing planned maintenance on [service name] on [date] from [start time] to [end time] UTC.

What to expect: [Description of impact — brief service interruption / no impact expected]
Duration: [Expected window]
Reason: [Brief business justification]

If you have any concerns, please contact support@sdc.com quoting reference CHG-NNNN.

Thank you for your understanding.
SDC Operations Team
```

### Change Completion Notification
```
Subject: Maintenance Complete — [Service Name] — CHG-NNNN

The planned maintenance for [service name] has been completed successfully at [time UTC].

Outcome: [Completed as planned / Completed with minor deviations / Rolled back]
Current status: [All systems normal]
Next steps: [Any monitoring period or follow-up actions]

If you experience any issues, please contact support@sdc.com.
```

## ITSM RFC Mandatory Fields

### Creation Fields
- Short description (max 80 chars)
- Change type (Standard / Normal Minor / Normal Major / Emergency)
- Affected services and CI list from CMDB
- Business justification
- Risk assessment rating (Low / Medium / High / Critical)
- Implementation start/end datetime
- Responsible engineer name
- Rollback plan reference (attached document)
- Test evidence reference (attached document)

### Closure Fields
- Actual start/end datetime
- Outcome (Successful / Rolled Back / Partially Completed)
- Deviations from plan (if any)
- CMDB updated (yes/no)
- PIR required (yes/no)
- Lessons learned summary

## Change Metrics and Reporting

### Key Change KPIs (Monthly)
| Metric | Target |
|---|---|
| Change success rate | ≥97% |
| Emergency change % of total | <10% |
| PIR completion on time | ≥95% |
| Changes rolled back | <5% |
| CAB submission on time | ≥90% |
| Changes during freeze window | 0 (standard/normal) |

### Monthly Change Report
- Total RFC volume by type (Standard / Normal Minor / Normal Major / Emergency)
- Success rate and rollback analysis
- Emergency change list with reasons and post-review outcomes
- CAB meeting attendance and decision summary
- PIR completion status
- Changes deferred from CAB with reasons
- Lessons learned from rolled-back changes

## Change Advisory Board (CAB) Operations

### CAB Chair Responsibilities
- Ensure all submissions reviewed before meeting
- Facilitate discussion — keep focus on risk and impact
- Record decisions with clear rationale
- Follow up deferred items from previous meeting
- Publish minutes within 4 hours

### CAB Member Responsibilities
- Review assigned RFCs before meeting (not during)
- Challenge unclear risk assessments
- Confirm OLA commitments for changes requiring their team's support
- Sign off in ITSM within 24 hours of verbal approval

### ECAB Activation Criteria
- P1/P2 incident requires production change to resolve
- Security vulnerability requires immediate patching
- Regulatory deadline requires emergency deployment
- Business-critical date (e.g., product launch) at risk without emergency change

## Testing and Validation Requirements

### Non-Production Environment Requirements
- All Normal Major changes must be fully tested in staging environment
- Staging must be production-equivalent for: OS version, application version, data volume (anonymised)
- Test cases must cover: happy path, error path, rollback procedure
- Performance testing required if change affects high-traffic services
- Security testing required if change modifies authentication or data access

### Change Validation Checklist
- [ ] Functional test: does the change do what it is designed to do?
- [ ] Regression test: have existing functions been broken?
- [ ] Performance test: response time within acceptable bounds?
- [ ] Rollback test: rollback procedure tested successfully in non-production?
- [ ] Monitoring test: monitoring and alerting still firing correctly after change?
- [ ] Security test: no new vulnerabilities introduced?

## Change Freeze Compliance

### Monitoring Freeze Compliance
- Change Coordinator reviews ITSM daily during freeze windows
- Any change submitted during freeze automatically flagged for SDM review
- Report of freeze-window changes included in monthly report
- Repeated freeze violations: escalate to department head

### Emergency Change During Freeze
- Stricter approval during year-end freeze: SDM + CTO + CISO required
- Business justification must reference specific financial or regulatory impact
- Post-freeze: all emergency changes from freeze period reviewed in retrospective
