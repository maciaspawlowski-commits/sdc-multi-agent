# SDC Historical Service Request Records

---

## SR-20240104-0001
**Date:** 2024-01-04 | **Status:** Fulfilled | **Priority:** Low
**Type:** Access Request | **Category:** User Account Management
**Requester:** Marketing Team (via manager: Claire Bowen)
**Assigned To:** IT Service Desk | **Fulfilled By:** L1 – James Park
**SLA Target:** 8 business hours | **Actual Fulfillment Time:** 3h 45m

**Request:** Provision standard access for 3 new marketing team members joining 2024-01-08. Required: Corporate email, Microsoft 365, Confluence read access, Salesforce Marketing Cloud standard user.

**Actions Taken:**
1. Identity provisioning in Azure AD for all 3 accounts
2. Microsoft 365 E3 licenses assigned
3. Confluence space permission granted (Marketing group membership)
4. Salesforce Marketing Cloud – standard user role assigned
5. Welcome email sent with credentials and setup guide
6. IT onboarding checklist completed

**Outcome:** All access provisioned by 2024-01-04 14:30 UTC. Users confirmed access working before start date.

**Feedback Score:** 5/5 — "Fast and smooth, everything was ready on day 1."

---

## SR-20240108-0002
**Date:** 2024-01-08 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Software Installation | **Category:** Development Tools
**Requester:** Development Team (via Team Lead: Rachel Torres)
**Assigned To:** IT Service Desk → L2 Software Team
**SLA Target:** 4 business hours | **Actual Fulfillment Time:** 2h 10m

**Request:** Install Docker Desktop (v4.26) and kubectl (v1.29) on 5 developer workstations (Windows 11). Required for new Kubernetes development workflow.

**Actions Taken:**
1. Verified software versions are on approved software list
2. Deployed via SCCM to all 5 machines (remote installation)
3. Verified installation with test containers on 2 sample machines
4. Notified team lead of completion

**Outcome:** All 5 installations successful. Team lead confirmed team can proceed with new workflow.

**Feedback Score:** 4/5 — "Quick turnaround, would appreciate a self-service portal for approved software."

---

## SR-20240112-0003
**Date:** 2024-01-12 | **Status:** Fulfilled | **Priority:** High
**Type:** Data Export (GDPR) | **Category:** Compliance
**Requester:** Legal Team (on behalf of customer: ref GDPR-2024-001)
**Assigned To:** Data Engineering
**SLA Target:** 72 hours (statutory) | **Actual Fulfillment Time:** 48h 30m

**Request:** Subject Access Request (SAR) for customer account data. Customer requested all personal data held by SDC. Required: account data, transaction history, support tickets, email logs, audit trail.

**Actions Taken:**
1. Identity verification completed (Legal team confirmed)
2. Data extraction from all 5 relevant systems
3. PII redaction of third-party data references
4. Data package compiled in portable format (JSON + CSV)
5. Secure delivery via encrypted link (24h expiry)
6. GDPR register updated with SAR completion record

**Outcome:** Data package delivered within 72-hour statutory deadline. Legal team confirmed package complete and compliant.

**Compliance Note:** SAR logged in data protection register. No data breaches identified during extraction.

---

## SR-20240115-0004
**Date:** 2024-01-15 | **Status:** Fulfilled | **Priority:** Low
**Type:** Hardware Procurement | **Category:** Workstation
**Requester:** Finance Team (Rachel Simpson)
**Assigned To:** Procurement → IT Logistics
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 4 business days

**Request:** Replacement laptop (current MacBook Pro 2018 showing hardware degradation). Business justification: battery failing (max 2h), display flickering.

**Actions Taken:**
1. Hardware assessment confirmed device beyond economic repair
2. Procurement raised for MacBook Pro 14" M3 (standard finance spec)
3. Device received from Apple Business portal
4. MDM enrolment and data migration from old device
5. Old device securely wiped and sent for certified disposal

**Outcome:** Replacement device delivered and configured. User data migrated. Old device disposed of compliantly.

**Feedback Score:** 5/5 — "Painless process, new laptop much faster."

---

## SR-20240118-0005
**Date:** 2024-01-18 | **Status:** Fulfilled | **Priority:** Medium
**Type:** New Service Onboarding | **Category:** Customer Onboarding
**Requester:** Account Management (new customer: Meridian Retail Group)
**Assigned To:** Customer Success + Technical Onboarding Team
**SLA Target:** 3 business days | **Actual Fulfillment Time:** 2 business days

**Request:** Provision new enterprise customer account: Meridian Retail Group. Required: tenant creation, admin user accounts (3), API key generation, webhook configuration, initial data migration (500K product records).

**Actions Taken:**
1. Tenant provisioned in production environment
2. 3 admin accounts created with temporary credentials
3. API keys generated with enterprise rate limits (10,000 req/min)
4. Webhook endpoint configured and tested
5. Product data import: 500K records migrated in 4h 30m via bulk import tool
6. Onboarding call scheduled and completed
7. Customer Success handover

**Outcome:** Customer fully onboarded 2 days ahead of SLA. First API call received 2024-01-20. Onboarding NPS: 9/10.

---

## SR-20240122-0006
**Date:** 2024-01-22 | **Status:** Fulfilled | **Priority:** Low
**Type:** Access Revocation | **Category:** Offboarding
**Requester:** HR Team (departure: Marcus Webb, Engineering)
**Assigned To:** IT Service Desk
**SLA Target:** 4 business hours | **Actual Fulfillment Time:** 1h 20m

**Request:** Offboard departing employee Marcus Webb (last day 2024-01-22). Revoke all access immediately upon confirmation of departure.

**Actions Taken:**
1. Azure AD account disabled
2. Microsoft 365 license revoked (data retained 90 days per policy)
3. GitHub organization membership removed
4. AWS IAM user deactivated
5. VPN certificate revoked
6. Physical badge deactivated (security notified)
7. Service Desk tools access removed
8. Handover of owned tickets to team lead confirmed
9. HR system updated

**Outcome:** All access revoked within SLA. No orphaned accounts detected in audit. IT asset return confirmed (laptop, badge).

---

## SR-20240125-0007
**Date:** 2024-01-25 | **Status:** Fulfilled | **Priority:** Medium
**Type:** DNS Configuration | **Category:** Network/Infrastructure
**Requester:** Platform Engineering (Tom Bradley)
**Assigned To:** Network Team
**SLA Target:** 4 business hours | **Actual Fulfillment Time:** 2h 5m (DNS propagation: +48h)

**Request:** Create DNS CNAME record for new internal service: metrics.internal.sdc.com → monitoring-cluster.eu-west.sdc.internal

**Actions Taken:**
1. Verified requestor is authorised for DNS changes (Platform Engineering Lead)
2. CNAME record created in Route53 (internal hosted zone)
3. Record verified from 3 internal resolver locations
4. TTL set to 300s (5 minutes) as requested for easy rollback
5. RFC logged (Standard Change SC-003)

**Outcome:** Record active and resolving correctly. Service team confirmed monitoring endpoint accessible.

---

## SR-20240201-0008
**Date:** 2024-02-01 | **Status:** Fulfilled | **Priority:** High
**Type:** SSL Certificate | **Category:** Security
**Requester:** Security Team (Sarah Chen)
**Assigned To:** Security Team (self-service via standard change)
**SLA Target:** 2 business hours | **Actual Fulfillment Time:** 45m

**Request:** Emergency SSL certificate renewal for api-internal.sdc.com. Certificate expired overnight (was missed in rotation schedule).

**Actions Taken:**
1. Let's Encrypt certificate issued (domain validation complete)
2. Certificate installed on API gateway
3. SSL Labs scan confirms A rating and valid certificate
4. Expiry monitoring corrected: api-internal.sdc.com now in automated renewal scope
5. Root cause review: certificate was added manually 12 months ago, not recorded in automation

**Outcome:** Certificate renewed, service restored. No customer-facing impact (internal service only).

**Follow-up:** Audit of all manually managed certificates initiated. Standard change SC-002 process documented.

---

## SR-20240205-0009
**Date:** 2024-02-05 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Permission Change | **Category:** Access Management
**Requester:** Finance Director (Emma Hartley)
**Assigned To:** IT Service Desk → IAM Team
**SLA Target:** 4 business hours | **Actual Fulfillment Time:** 3h 30m

**Request:** Grant Finance team lead (Peter Oduya) read access to AWS Cost Explorer and billing data. Business justification: monthly budget review responsibility.

**Actions Taken:**
1. Manager approval confirmed (Finance Director approved the request)
2. AWS IAM policy for CostExplorer read created
3. Policy attached to Peter Oduya's AWS role
4. Access validated: Cost Explorer dashboard accessible
5. Access review scheduled (quarterly, per Access Management Policy)

**Outcome:** Access granted. Peter Oduya confirmed he can access billing data. Quarterly access review added to IAM calendar.

---

## SR-20240212-0010
**Date:** 2024-02-12 | **Status:** Fulfilled | **Priority:** Low
**Type:** Report Request | **Category:** Business Intelligence
**Requester:** Customer Success Manager (Sophie Marshall)
**Assigned To:** Data Engineering
**SLA Target:** 3 business days | **Actual Fulfillment Time:** 2 business days

**Request:** Create a monthly report showing API usage per enterprise customer (request count, error rate, average latency) for the past 12 months. To be delivered as CSV + Grafana dashboard.

**Actions Taken:**
1. Requirements clarified with requester (metrics confirmed)
2. ClickHouse query built and tested
3. Grafana dashboard created: "Enterprise API Usage" (shared with Customer Success team)
4. CSV export template created for monthly generation
5. Scheduled monthly export to Customer Success shared drive
6. Report documentation added to Confluence

**Outcome:** Dashboard live. First monthly CSV exported for January 2024. Customer Success team confirmed metrics match expectations.

---

## SR-20240220-0011
**Date:** 2024-02-20 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Firewall Rule | **Category:** Network Security
**Requester:** Integration Engineering (Jack Liu)
**Assigned To:** Network Security Team
**SLA Target:** 2 business days | **Actual Fulfillment Time:** 1 business day

**Request:** Allow outbound HTTPS (443) from webhook-worker subnet to partner API endpoint: api.logistics-partner.com (IP range: 185.10.42.0/24). Required for new logistics integration.

**Actions Taken:**
1. Business justification verified with Integration Engineering Lead
2. IP range confirmed via nslookup and partner documentation
3. Firewall rule created: source=webhook-worker-subnet, dest=185.10.42.0/24, port=443
4. Connectivity test confirmed from integration test environment
5. RFC logged as Standard Change (approved template)
6. CMDB updated with new firewall rule entry

**Outcome:** Connectivity confirmed. Integration team deployed logistics webhook integration successfully.

---

## SR-20240301-0012
**Date:** 2024-03-01 | **Status:** Fulfilled | **Priority:** High
**Type:** Database Restore (Partial) | **Category:** Data Recovery
**Requester:** DBA Team (on behalf of application team)
**Assigned To:** DBA Team
**SLA Target:** 4 business hours | **Actual Fulfillment Time:** 3h 15m

**Request:** Restore specific table (customer_preferences) to state as of 2024-02-29 23:00 UTC. Data was corrupted during failed migration CHG-20240229-0005. Approximately 8,400 rows affected.

**Actions Taken:**
1. Verified backup from 2024-02-29 22:50 UTC is available (S3)
2. Restored table to isolated recovery environment
3. Validated row count and data integrity
4. Applied delta changes from WAL (22:50 UTC to 23:00 UTC target time)
5. Export CSV generated for affected rows
6. Application team validated recovery data
7. Live data updated via controlled script with audit log

**Outcome:** 8,412 rows successfully restored to pre-corruption state. Zero data loss for the target window.

---

## SR-20240315-0013
**Date:** 2024-03-15 | **Status:** Fulfilled | **Priority:** Low
**Type:** Software License | **Category:** License Management
**Requester:** Engineering Team (via Team Lead)
**Assigned To:** Procurement → IT
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 3 business days

**Request:** Purchase 10 additional JetBrains All Products Pack licenses for new engineering hires (starting Q2 2024).

**Actions Taken:**
1. License count verified with current usage report (60% of existing licenses in use)
2. Procurement order raised via JetBrains reseller portal
3. 10 additional seats added to org subscription
4. License assignment instructions sent to Engineering Lead
5. License inventory updated in CMDB

**Outcome:** Licenses available before Q2 hire start dates. Engineering Lead confirmed receipt.

---

## SR-20240320-0014
**Date:** 2024-03-20 | **Status:** Rejected | **Priority:** Low
**Type:** Custom Software Request | **Category:** Software Procurement
**Requester:** Sales Team (Mark Davies)
**Assigned To:** IT Service Desk → IT Manager
**SLA Target:** 5 business days | **Decision Time:** 3 business days

**Request:** Install Zoom Phone add-on for personal use on company device.

**Reason for Rejection:** SDC uses Microsoft Teams for all telephony (mandatory standard). Zoom Phone would duplicate functionality and introduce unsupported software. Per IT software policy, personal preference software not installed on company devices.

**Outcome:** Requester notified with explanation. Referred to Microsoft Teams Phone feature guide. No escalation requested.

---

## SR-20240402-0015
**Date:** 2024-04-02 | **Status:** Fulfilled | **Priority:** Medium
**Type:** API Key Rotation | **Category:** Security
**Requester:** Platform Engineering (Rachel Torres)
**Assigned To:** Platform Engineering (self-service via ITSM)
**SLA Target:** 4 business hours | **Actual Fulfillment Time:** 1h 30m

**Request:** Rotate API keys for internal monitoring integration (Dash0 ingest key). Keys are 12 months old, rotating per security policy.

**Actions Taken:**
1. New API key generated in Dash0 portal
2. Old key revoked after confirming new key functional
3. New key stored in HashiCorp Vault (secrets manager)
4. Kubernetes secret updated via Vault Operator
5. Monitoring connectivity confirmed (test trace sent and received)
6. Key rotation logged in security audit log

**Outcome:** Key rotated without service interruption. Monitoring confirmed operational with new key.

---

## SR-20240415-0016
**Date:** 2024-04-15 | **Status:** Fulfilled | **Priority:** High
**Type:** Incident Investigation Request | **Category:** Root Cause Analysis Support
**Requester:** Problem Manager (Operations)
**Assigned To:** Data Engineering + DBA Team
**SLA Target:** 1 business day | **Actual Fulfillment Time:** 6h

**Request:** Pull full database audit logs and application logs for 2024-04-05 00:00–06:00 UTC for PRB-20240405-0005 investigation (billing invoice job failure).

**Actions Taken:**
1. PostgreSQL audit logs extracted for specified window
2. Application logs pulled from Elastic for invoice-service
3. S3 access logs for invoice template bucket extracted
4. All logs compiled into investigation package
5. Delivered to Problem Manager with index document

**Outcome:** Investigation package enabled confirmation of root cause (IAM permission removal). Problem record closed within 5 days.

---

## SR-20240501-0017
**Date:** 2024-05-01 | **Status:** Fulfilled | **Priority:** Low
**Type:** Workstation Setup | **Category:** New Starter
**Requester:** HR Team (new starter: Amara Osei, Junior Developer)
**Assigned To:** IT Service Desk
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 3 business days

**Request:** Full workstation setup for new junior developer starting 2024-05-06.

**Checklist Completed:**
- MacBook Pro 14" M3 (developer spec) provisioned and enrolled in MDM
- Azure AD account created with Developer role
- GitHub organisation invitation sent
- Development toolchain deployed (Docker, VS Code, kubectl, Node.js LTS)
- VPN client configured
- Jira, Confluence, Slack access provisioned
- Password manager account set up
- IT security induction scheduled

**Outcome:** All access and hardware ready 3 days before start date. New starter confirmed everything working on day 1.

**Feedback Score:** 5/5

---

## SR-20240510-0018
**Date:** 2024-05-10 | **Status:** Fulfilled | **Priority:** High
**Type:** Emergency Access Provision | **Category:** Incident Support
**Requester:** Incident Commander (INC-20240502-0016 post-incident)
**Assigned To:** Network Engineering
**SLA Target:** 2 business hours | **Actual Fulfillment Time:** 45m

**Request:** Provision read-only access to ISP management portal for Network Engineering on-call team. Required for direct visibility during BGP incidents.

**Actions Taken:**
1. ISP TAM contacted and access request submitted
2. ISP provisioned read-only portal access for 3 network engineers
3. MFA configured on ISP portal accounts
4. Credentials stored in team secrets manager
5. Access verified by all 3 engineers

**Outcome:** Network team has direct BGP monitoring capability. Used successfully in subsequent network review meeting.

---

## SR-20240522-0019
**Date:** 2024-05-22 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Capacity Upgrade | **Category:** Infrastructure
**Requester:** DBA Team (Anna Patel)
**Assigned To:** Platform Engineering + DBA
**SLA Target:** 3 business days | **Actual Fulfillment Time:** 2 business days

**Request:** Increase Primary PostgreSQL instance from db.r6g.4xlarge to db.r6g.8xlarge (double RAM: 128GB → 256GB). Capacity forecast shows current instance will reach 80% memory within 60 days.

**Actions Taken:**
1. Capacity forecast validated (agreed: upgrade warranted)
2. RFC raised as Normal Minor change (CHG-20240524-0019)
3. Maintenance window scheduled (low traffic)
4. Instance class changed via AWS console (15-minute planned downtime)
5. Post-upgrade: memory metrics confirmed at 38% utilisation (comfortable headroom)

**Outcome:** Upgrade completed within planned 15-minute window. Memory forecast now comfortable for 18 months.

---

## SR-20240605-0020
**Date:** 2024-06-05 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Monitoring Setup | **Category:** Observability
**Requester:** Payments Engineering (on behalf of Stripe integration)
**Assigned To:** Platform Engineering (Observability)
**SLA Target:** 2 business days | **Actual Fulfillment Time:** 1 business day

**Request:** Create Dash0 alert for Stripe API version deprecation monitoring. Alert when current API version is within 90 days of Stripe's deprecation date.

**Actions Taken:**
1. Stripe API deprecation dates retrieved from Stripe documentation
2. Custom metric added: stripe_api_days_until_deprecation
3. Dash0 alert configured: warning at 90 days, critical at 30 days
4. Alert tested with simulated deprecation date
5. Alert routed to Payments Engineering + Operations channels

**Outcome:** Stripe API deprecation alert active. Next API version deprecation: 340 days away (safe).

---

## SR-20240620-0021
**Date:** 2024-06-20 | **Status:** Fulfilled | **Priority:** Low
**Type:** Training Request | **Category:** Staff Development
**Requester:** Operations Team Lead (David Kim)
**Assigned To:** L&D Team → IT
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 4 business days

**Request:** Purchase Kubernetes Administrator (CKA) exam vouchers for 4 operations engineers.

**Actions Taken:**
1. Manager approval obtained (Engineering Director)
2. Training budget verified (within Q2 training budget allocation)
3. CNCF exam vouchers purchased (4x CKA, $395 each)
4. Vouchers distributed to engineers via secure message
5. Learning time allocated in team calendar (1 day/week study)

**Outcome:** All 4 engineers received exam vouchers. 3 of 4 passed CKA within 3 months.

---

## SR-20240701-0022
**Date:** 2024-07-01 | **Status:** Fulfilled | **Priority:** High
**Type:** Data Deletion (GDPR Right to Erasure) | **Category:** Compliance
**Requester:** Legal Team (customer ref GDPR-2024-018)
**Assigned To:** Data Engineering + DBA
**SLA Target:** 30 days (statutory) | **Actual Fulfillment Time:** 4 business days

**Request:** Process Right to Erasure (GDPR Article 17) request for customer account. Delete all personal data across all systems.

**Actions Taken:**
1. Identity verification confirmed by Legal
2. Data audit: identified 7 systems containing personal data
3. Account soft-deleted in main application (preserving anonymised transaction records for financial compliance)
4. Personal identifiers anonymised in: marketing system, support tickets, email logs, analytics, audit logs
5. Backups documented: personal data will expire from backups within 90 days (policy compliant)
6. Legal team notified with completion certificate
7. GDPR register updated

**Outcome:** All personal data erased or anonymised within statutory requirement. Compliance certificate issued.

---

## SR-20240715-0023
**Date:** 2024-07-15 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Performance Investigation | **Category:** Application Support
**Requester:** Customer (Enterprise Account: Zenith Insurance)
**Assigned To:** Platform Engineering + Data Engineering
**SLA Target:** 1 business day (P2 SLA) | **Actual Fulfillment Time:** 5h

**Request:** Customer reporting API response times degrading during batch processing windows (18:00–20:00 UTC daily). P99 latency reported at 4-8 seconds during this window.

**Investigation Actions:**
1. Traced customer's API calls through Dash0 (tracing enabled)
2. Identified: database query slowdown during batch job window
3. Root cause: customer's API calls hitting same database shard as SDC nightly batch job
4. Solution: customer's requests rescheduled to dedicated read replica

**Outcome:** Customer API latency reduced to p99 <500ms during batch window. Customer confirmed improvement. Follow-up scheduled in 2 weeks to confirm sustained improvement.

---

## SR-20240801-0024
**Date:** 2024-08-01 | **Status:** Fulfilled | **Priority:** Low
**Type:** Documentation Update | **Category:** Knowledge Management
**Requester:** Operations Team
**Assigned To:** Operations Team (self-service)
**SLA Target:** 3 business days | **Actual Fulfillment Time:** 2 business days

**Request:** Update incident management runbook to reflect new escalation matrix following organisational restructure. CTO contact details updated; new Duty Manager rotation added.

**Actions Taken:**
1. Runbook reviewed against current org chart
2. Escalation matrix updated (new CTO contact, Duty Manager rotation)
3. Updated runbook reviewed by SDM (approved)
4. Published to Confluence and shared with all L2/L3 teams
5. Teams notification sent: "Runbook v2.3 published — please review escalation changes"

**Outcome:** Runbook updated and distributed. All team leads confirmed receipt.

---

## SR-20240820-0025
**Date:** 2024-08-20 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Storage Expansion | **Category:** Infrastructure
**Requester:** Data Engineering (capacity forecast)
**Assigned To:** Platform Engineering
**SLA Target:** 3 business days | **Actual Fulfillment Time:** 2 business days

**Request:** Increase Elasticsearch cluster storage from 2TB to 4TB per node (3 nodes). Current usage at 78%, forecast to reach 90% in 45 days.

**Actions Taken:**
1. Capacity forecast validated (current growth rate: 35GB/day)
2. AWS EBS volume expansion executed (online, no downtime)
3. Elasticsearch cluster rebalancing confirmed
4. New capacity: 12TB total. Current usage: 39%.
5. Disk alert thresholds recalibrated for new capacity

**Outcome:** Storage expanded without downtime. Capacity now comfortable for estimated 12 months.

---

## SR-20240905-0026
**Date:** 2024-09-05 | **Status:** Fulfilled | **Priority:** High
**Type:** DR Test | **Category:** Business Continuity
**Requester:** SDM (quarterly DR test schedule)
**Assigned To:** Platform Engineering + DBA
**SLA Target:** 2 business days scheduling | **Actual Test Duration:** 4h

**Request:** Execute quarterly DR test: simulate EU-West availability zone failure. Validate failover to EU-Central. Measure RTO and RPO.

**Test Execution:**
1. EU-West services scaled to zero (simulated AZ failure)
2. DNS failover to EU-Central (Route53 health check triggered)
3. Measured time to first healthy response: 4m 20s (RTO target: 15 minutes ✓)
4. Data consistency check: zero data loss (replica lag at time of failover: 4 seconds)
5. Restored EU-West and confirmed failback

**Results:** RTO: 4m 20s (✓), RPO: 4 seconds (✓). DR test PASSED.

**Outcome:** Results reported to SDM and documented. Certificate of DR Test completion issued for compliance. Next DR test: December 2024.

---

## SR-20241001-0027
**Date:** 2024-10-01 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Vulnerability Assessment | **Category:** Security
**Requester:** CISO (quarterly security review)
**Assigned To:** Security Team + External Penetration Test Vendor
**SLA Target:** 10 business days | **Actual Fulfillment Time:** 8 business days

**Request:** Q3 penetration test of public-facing APIs and web application. Scope: api.sdc.com, portal.sdc.com, authentication flows.

**Actions Taken:**
1. Scope confirmed with Security Team and vendor (Hargreaves Security Ltd)
2. Test window: 2024-10-07 to 2024-10-14 (business hours)
3. Pen test executed (black-box + grey-box with API documentation)
4. Report received 2024-10-15

**Findings (summary):**
- Critical: 0
- High: 1 (API endpoint returning stack trace on error — information disclosure)
- Medium: 3 (CORS misconfiguration on 2 endpoints; weak rate limiting on password reset)
- Low: 7

**Outcome:** All Critical/High findings remediated within 2 weeks. Medium findings scheduled for next sprint. Report archived in Confluence (restricted access).

---

## SR-20241105-0028
**Date:** 2024-11-05 | **Status:** Fulfilled | **Priority:** Low
**Type:** Archive / Decommission | **Category:** Data Management
**Requester:** DBA Team
**Assigned To:** DBA Team + Storage Team
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 4 business days

**Request:** Archive and decommission legacy reporting database (reports-db-legacy). Database unused since Q2 2024 (new ClickHouse cluster replaced it). Data to be archived to S3 (cold storage) before deletion.

**Actions Taken:**
1. Confirmed no active connections in past 90 days (pg_stat_activity audit)
2. Final backup taken and uploaded to S3 (cold storage, AES-256 encrypted)
3. Data retention confirmed: 7 years per financial data policy
4. Database instance terminated (AWS RDS)
5. CMDB updated: reports-db-legacy marked as Decommissioned
6. Cost saving: $340/month

**Outcome:** Legacy database decommissioned. Archive available if needed. Cost savings realised.

---

## SR-20241201-0029
**Date:** 2024-12-01 | **Status:** Fulfilled | **Priority:** High
**Type:** Year-End Infrastructure Review | **Category:** Capacity Planning
**Requester:** SDM (annual planning)
**Assigned To:** Platform Engineering + DBA + Network
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 5 business days

**Request:** Produce 2025 infrastructure capacity plan. Include: current utilisation, 2024 growth rates, 2025 headroom recommendations, cost forecast.

**Deliverables Produced:**
- Current utilisation report (all major services)
- 2024 growth analysis (CPU: +34%, Storage: +67%, Network: +28%)
- Capacity recommendations for 2025: PostgreSQL storage upgrade Q2, Elasticsearch expansion Q1, Redis memory upgrade Q1
- 2025 infrastructure cost forecast: £420K (+12% YoY)

**Outcome:** Capacity plan presented to CTO and Finance Director. Q1 2025 upgrades approved. Budget allocated.

---

## SR-20250110-0030
**Date:** 2025-01-10 | **Status:** Fulfilled | **Priority:** High
**Type:** Emergency Procurement | **Category:** Hardware
**Requester:** Platform Engineering (post INC-20250108-0037)
**Assigned To:** Procurement + Infrastructure
**SLA Target:** 2 business days | **Actual Fulfillment Time:** 2 business days

**Request:** Emergency procurement of 2 replacement server nodes for etcd cluster (different hardware generation to failed nodes). Required to restore etcd cluster resilience.

**Actions Taken:**
1. Hardware specifications confirmed (different SSD manufacturer/model)
2. Emergency purchase order raised and approved (SDM approval)
3. Servers delivered from distributor
4. etcd nodes configured and joined cluster
5. Cluster health confirmed (3 nodes, quorum restored)
6. Anti-affinity rules enforced

**Outcome:** Cluster resilience restored. etcd cluster healthy with 3 nodes across different hardware generations.

**Cost:** £8,400 (emergency procurement premium). Approved under incident response budget.

---

## SR-20250120-0031
**Date:** 2025-01-20 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Compliance Audit Support | **Category:** Audit
**Requester:** Compliance Manager (annual ISO 27001 audit)
**Assigned To:** IT Service Desk + All Team Leads
**SLA Target:** 10 business days | **Actual Fulfillment Time:** 8 business days

**Request:** Compile evidence package for annual ISO 27001 surveillance audit. Evidence required: access reviews, change records, incident records, training completion, risk register.

**Actions Taken:**
1. Access review completed for all privileged accounts (Q4 2024)
2. Change management records exported from ITSM (2024 full year)
3. Incident records exported and redacted for auditor
4. Training completion report extracted from LMS
5. Risk register reviewed and updated
6. Evidence package compiled and shared with auditor

**Outcome:** Audit completed. Result: ISO 27001 surveillance audit PASSED. 3 minor non-conformities (all corrective actions accepted). Certificate maintained.

---

## SR-20250205-0032
**Date:** 2025-02-05 | **Status:** Fulfilled | **Priority:** Low
**Type:** User Training | **Category:** Knowledge Management
**Requester:** Operations Manager
**Assigned To:** L&D + Operations Team
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 4 business days

**Request:** Organise ITIL 4 Foundation refresher training for 8 Service Desk agents (team has grown, several new members unfamiliar with ITIL 4 practices).

**Actions Taken:**
1. Training provider contracted (AXELOS certified: BCS Learning)
2. Online course access provisioned for 8 agents
3. 2-week completion target set
4. Pass confirmation received for 7 of 8 agents
5. 1 agent requiring resit (additional support arranged)

**Outcome:** 7/8 agents passed ITIL 4 Foundation within target. 8th agent resitting in 3 weeks.

---

## SR-20250301-0033
**Date:** 2025-03-01 | **Status:** Fulfilled | **Priority:** High
**Type:** Security Incident Support | **Category:** Security
**Requester:** CISO (CVE advisory)
**Assigned To:** Security Team + Platform Engineering
**SLA Target:** 2 business days (vendor advisory) | **Actual Fulfillment Time:** 1 business day

**Request:** Assess and remediate CVE-2025-1234 (critical RCE vulnerability in nginx versions <1.25.4). SDC production nginx version: 1.25.3. Patch required.

**Actions Taken:**
1. Vulnerability confirmed: CVE affects SDC production nginx
2. Emergency change raised: ECB-20250301-001
3. nginx updated to 1.25.4 via rolling deployment (zero downtime)
4. Vulnerability scan confirmed remediation
5. CISO notified of completion
6. CMDB updated

**Outcome:** CVE remediated within 24 hours of advisory. Zero service disruption. Security advisory closed.

---

## SR-20250315-0034
**Date:** 2025-03-15 | **Status:** Fulfilled | **Priority:** Medium
**Type:** API Documentation | **Category:** Customer Success
**Requester:** Customer Success Team (on behalf of 5 enterprise customers)
**Assigned To:** Platform Engineering + Technical Writing
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 4 business days

**Request:** Create API migration guide for customers moving from API v2 to API v3. Customers need to understand field name changes and new authentication flow.

**Actions Taken:**
1. API v2 → v3 field mapping documented
2. Authentication flow differences documented (OAuth2 scope changes)
3. Code examples in Python, JavaScript, and cURL added
4. Migration guide published to developer portal
5. Customer Success notified to share with affected customers
6. Webinar scheduled for enterprise customers (2025-03-25)

**Outcome:** Migration guide published. Webinar attended by 18 enterprise customer contacts. 3 customers have begun migration.

---

## SR-20250401-0035
**Date:** 2025-04-01 | **Status:** Fulfilled | **Priority:** Medium
**Type:** Vendor Management | **Category:** Contract Renewal
**Requester:** Operations Manager + Procurement
**Assigned To:** Operations Manager + Legal
**SLA Target:** 5 business days | **Actual Fulfillment Time:** 4 business days

**Request:** Renew Datadog contract (annual renewal, coming up 2025-04-30). Evaluate whether to continue, negotiate, or switch to alternative (Dash0 now primary observability).

**Evaluation Outcome:**
- Datadog usage: primarily synthetic monitoring and APM for legacy services
- Dash0 has replaced 80% of Datadog functionality at 40% lower cost
- Remaining Datadog use: 5 legacy services not yet migrated
- Decision: downgrade Datadog to minimal plan (synthetic monitoring only), full migration to Dash0 by end of 2025

**Actions Taken:**
1. Negotiated Datadog plan downgrade: $12,000/year savings
2. Contract renewed at reduced tier
3. Dash0 migration plan for remaining 5 services created
4. Target: full Datadog deprecation by 2025-12-31

**Outcome:** $12K annual savings. Dash0 migration plan approved by CTO.

---

## SR-20250415-0036
**Date:** 2025-04-15 | **Status:** In Progress | **Priority:** Medium
**Type:** New Integration | **Category:** Platform Extension
**Requester:** Product Team (Product Director: Henry Ashmore)
**Assigned To:** Integration Engineering
**SLA Target:** 10 business days | **Estimated Completion:** 2025-04-30

**Request:** Integrate Salesforce CRM with SDC customer platform. Bi-directional sync: SDC account status → Salesforce, Salesforce opportunity status → SDC onboarding workflow.

**Current Status:** Requirements gathering complete. Technical design in review. Integration engineering team allocated. RFC being drafted for CAB.

**Risks Identified:** Salesforce API rate limits may constrain sync frequency. Sandbox testing environment provisioned.

---

## SR-20250422-0037
**Date:** 2025-04-22 | **Status:** Fulfilled | **Priority:** High
**Type:** Access Emergency | **Category:** Security / Access
**Requester:** Security Team (suspicious activity alert)
**Assigned To:** IAM Team
**SLA Target:** 1 hour | **Actual Fulfillment Time:** 22m

**Request:** Immediately suspend all access for contractor account (ext.john.barker@sdc.com) due to suspicious login activity (multiple failed MFA attempts from unusual IP range, followed by successful login from different country).

**Actions Taken:**
1. Azure AD account immediately disabled (9 minutes after alert)
2. All active sessions terminated (token revocation)
3. AWS access keys disabled
4. VPN certificate revoked
5. Security team notified to begin investigation
6. Account manager notified
7. Contractor contacted to verify activity

**Outcome:** Access suspended within SLA. Investigation confirmed account credentials were compromised. Credentials reset and MFA re-enrolled before access restored 48 hours later after verification.
