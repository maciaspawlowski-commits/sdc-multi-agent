# SDC Historical SLA Reports & Records

---

## SLA-MONTHLY-2024-01
**Period:** January 2024 | **Report Date:** 2024-02-05
**Overall Compliance Score:** 96.8%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Core API Platform | 99.9% | 99.91% | ✓ MET |
| Payment Gateway | 99.95% | 99.87% | ✗ BREACHED |
| Customer Portal | 99.9% | 99.85% | ✗ BREACHED |
| Authentication Service | 99.99% | 99.93% | ✗ BREACHED |
| Email Notification Service | 99.5% | 99.89% | ✓ MET |
| Reporting Module | 99.0% | 99.93% | ✓ MET |

### Breaches Detail

**Payment Gateway breach (INC-20240103-0001):**
- Outage duration: 1h 42m
- Impact: 2,400 users, £18,000 estimated revenue loss
- SLA deduction: 0.08% availability loss
- Root cause: Connection pool exhaustion (connection leak in v2.3.1)
- Customer credit applied: Yes (per SLA agreement – 1 day service credit)

**Customer Portal breach (INC-20240108-0002):**
- Outage duration: 2h 15m
- Impact: 340 users (Azure AD federated only)
- Root cause: Azure AD certificate rotation not synced to SDC IdP

**Authentication Service breach (INC-20240315-0011):**
- Outage duration: 1h 2m
- Impact: All users (~8,000)
- Root cause: TLS certificate expired (manually managed, not in auto-renewal scope)
- Customer credit applied: Yes (P1 – full SLA breach compensation)

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 2 | 2 (100%) | 100% |
| P2 | Acknowledge 30m, Resolve 4h | 4 | 3 (75%) | 75% |
| P3 | Acknowledge 1h, Resolve 8h | 12 | 11 (92%) | 92% |
| P4 | Acknowledge 4h, Resolve 3d | 28 | 27 (96%) | 96% |

**P2 miss:** INC-20240126-0005 (email notifications) – resolved in 5h 20m (SLA: 4h). Email service queue backup took longer than expected. Workaround (switch to AWS SES) not identified fast enough.

### Change Management SLA
- Change success rate: 96.3% (target: 97%) — marginally below due to 2 rollbacks
- Emergency changes: 8.3% of total (target: <10%) — within target

### Monthly Summary
Challenging month due to 3 P1/P2 incidents linked to the same root cause category (certificate/credential management). Immediate action: certificate audit initiated. Trend: availability slightly below target, corrective actions underway.

---

## SLA-MONTHLY-2024-02
**Period:** February 2024 | **Report Date:** 2024-03-04
**Overall Compliance Score:** 98.2%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Core API Platform | 99.9% | 99.95% | ✓ MET |
| Payment Gateway | 99.95% | 99.99% | ✓ MET |
| Customer Portal | 99.9% | 99.95% | ✓ MET |
| Authentication Service | 99.99% | 99.99% | ✓ MET |
| File Upload Service | 99.5% | 99.76% | ✓ MET |
| Database Cluster | 99.99% | 99.86% | ✗ BREACHED |

### Breach Detail

**Database Cluster breach (INC-20240210-0007):**
- Outage duration: 2h 8m (write operations unavailable)
- Impact: All write-dependent services; data inconsistency window during failover
- Root cause: PostgreSQL primary disk I/O saturation; autovacuum runaway
- SLA credit: Yes (database tier SLA breach – affected 3 enterprise customers)

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 1 | 1 (100%) | 100% |
| P2 | Acknowledge 30m, Resolve 4h | 3 | 3 (100%) | 100% |
| P3 | Acknowledge 1h, Resolve 8h | 9 | 9 (100%) | 100% |
| P4 | Acknowledge 4h, Resolve 3d | 22 | 21 (95%) | 95% |

### Monthly Summary
Improved month overall. Key concern: DB primary failure highlighted need for autovacuum tuning and I/O monitoring. Both addressed in Problem Record PRB-20240210-0003. File upload service recovered quickly from regression introduced by CHG-20240215-0005. No SLA compensation beyond DB breach.

---

## SLA-MONTHLY-2024-03
**Period:** March 2024 | **Report Date:** 2024-04-02
**Overall Compliance Score:** 99.1%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Core API Platform | 99.9% | 99.99% | ✓ MET |
| Payment Gateway | 99.95% | 99.99% | ✓ MET |
| Customer Portal | 99.9% | 99.99% | ✓ MET |
| Authentication Service | 99.99% | 99.99% | ✓ MET |
| API Rate Limiting | 99.9% | 99.78% | ✗ BREACHED |

### Breach Detail

**API Rate Limiting breach (INC-20240308-0010):**
- Outage duration: 4h 10m
- Impact: 12 enterprise API customers; 3 customer SLA breaches triggered
- Root cause: Redis rate limit configuration lost during INC-20240119-0004 recovery
- Customer SLA credits issued: 3 customers (£4,200 total credits)
- Root cause addressed: Redis config now managed as code

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 1 | 1 (100%) | 100% |
| P2 | Acknowledge 30m, Resolve 4h | 2 | 2 (100%) | 100% |
| P3 | Acknowledge 1h, Resolve 8h | 8 | 8 (100%) | 100% |
| P4 | Acknowledge 4h, Resolve 3d | 19 | 19 (100%) | 100% |

### Monthly Summary
Strong incident response month. The API rate limiting breach was a consequence of a previous incident's recovery — identified a systemic issue with Redis configuration management. Permanent fix implemented. PostgreSQL upgrade rescheduled for April after February rollback.

---

## SLA-MONTHLY-2024-04
**Period:** April 2024 | **Report Date:** 2024-05-06
**Overall Compliance Score:** 98.4%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Core API Platform | 99.9% | 99.99% | ✓ MET |
| Payment Gateway | 99.95% | 99.99% | ✓ MET |
| Billing & Invoicing | 99.9% | 99.78% | ✗ BREACHED |
| Search Service | 99.5% | 99.30% | ✗ BREACHED |

### Breach Detail

**Billing breach (INC-20240405-0013):**
- Impact: Invoice generation delayed 24 hours for full April billing cycle
- Root cause: S3 bucket IAM policy over-restricted during security hardening
- Business Impact: High – delayed customer invoicing

**Search breach (INC-20240412-0014):**
- Stale search results for 5 hours
- Root cause: Kafka consumer group rebalance loop blocking index sync

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 0 | N/A | N/A |
| P2 | Acknowledge 30m, Resolve 4h | 3 | 3 (100%) | 100% |
| P3 | Acknowledge 1h, Resolve 8h | 10 | 9 (90%) | 90% |
| P4 | Acknowledge 4h, Resolve 3d | 25 | 25 (100%) | 100% |

### PostgreSQL Upgrade
Successfully completed on 2024-04-14 (CHG-20240414-0010). 18% reduction in query p99 latency as direct benefit. No downtime.

---

## SLA-MONTHLY-2024-05
**Period:** May 2024 | **Report Date:** 2024-06-03
**Overall Compliance Score:** 98.9%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Core API Platform | 99.9% | 99.96% | ✓ MET |
| All Services | 99.9% | 99.96% | ✓ MET (BGP incident) |
| Webhook Delivery | 99.5% | 99.65% | ✓ MET |
| Email Notification | 99.5% | 99.88% | ✓ MET |

### Notable Events

**Full platform outage (INC-20240502-0016):** 18-minute BGP routing failure. Availability: 99.96% overall (met 99.9% SLA — incident was below breach threshold for most services). BGP failover speed improved post-incident.

**Email deliverability issue (INC-20240510-0017):** SPF record not updated post-migration. Activation emails affected but no availability SLA breach.

**Webhook delivery (INC-20240518-0018):** OOMKilled workers. 3h 15m degradation. Availability remained above 99.5% SLA threshold.

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 1 | 1 (100%) | 100% |
| P2 | Acknowledge 30m, Resolve 4h | 2 | 2 (100%) | 100% |
| P3 | Acknowledge 1h, Resolve 8h | 11 | 11 (100%) | 100% |
| P4 | Acknowledge 4h, Resolve 3d | 23 | 23 (100%) | 100% |

---

## SLA-MONTHLY-2024-06
**Period:** June 2024 | **Report Date:** 2024-07-02
**Overall Compliance Score:** 97.3%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Checkout & Payment | 99.95% | 99.88% | ✗ BREACHED |
| CDN / Static Assets | 99.9% | 99.77% | ✗ BREACHED |
| Internal HR Portal | 99.0% | 99.17% | ✓ MET |

### Breach Detail

**Payment breach (INC-20240605-0019):**
- Duration: 52 minutes
- Stripe API version deprecated and removed
- Revenue loss: £22,000. SLA credits issued: 2 enterprise customers
- Lessons: External API lifecycle tracking implemented

**CDN breach (INC-20240620-0021):**
- Duration: 1h 40m impact for APAC users
- Singapore CDN PoP offline (provider hardware failure)
- 340 APAC accounts affected
- Mitigation: Multi-PoP failover subsequently configured

### Change Stats
- Changes this month: 34 (Standard: 18, Normal Minor: 12, Normal Major: 4)
- Success rate: 97.1% (2 changes requiring follow-up)
- PostgreSQL upgrade (April) showing continued benefit: p99 query latency 22% below pre-upgrade

---

## SLA-MONTHLY-2024-Q3-SUMMARY
**Period:** Q3 2024 (July–September) | **Report Date:** 2024-10-07
**Overall Q3 Compliance Score:** 97.6%
**Prepared By:** Service Delivery Manager

### Q3 Availability Summary

| Service | Q3 SLA | Q3 Actual | Breaches |
|---|---|---|---|
| Core API Platform | 99.9% | 99.84% | 1 (INC-20240710-0023, INC-20240801-0025) |
| Authentication Service | 99.99% | 99.97% | 1 (INC-20240718-0024 – MFA) |
| Payment Gateway | 99.95% | 99.99% | 0 |
| Database Cluster | 99.99% | 99.87% | 1 (INC-20240905-0028 – disk full) |
| Customer Portal | 99.9% | 99.99% | 0 |
| All Services (Kubernetes) | 99.9% | 99.83% | 1 (INC-20241020-0032) |

### Q3 Root Cause Categories (Pareto)
1. **Infrastructure capacity** (3 incidents): Redis disk, Kafka lag, DB disk — 45% of P1/P2 outage time
2. **Vendor/external dependency** (2 incidents): FCM deprecation, ISP BGP
3. **Process gaps** (2 incidents): NTP monitoring, PDB enforcement
4. **Application bugs** (1 incident): Customer account suspension logic

### Key Improvements Delivered in Q3
- BGP failover time reduced from 5 minutes to 90 seconds
- PodDisruptionBudgets enforced across all production deployments
- Spot instances removed from production critical workloads
- WAL archiving implemented with failure alerting
- Kafka consumer lag monitoring active

### Q3 SLA Credit Summary
Total SLA credits issued in Q3: £14,200 (4 customer accounts)

---

## SLA-MONTHLY-2024-10
**Period:** October 2024 | **Report Date:** 2024-11-04
**Overall Compliance Score:** 97.1%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Kubernetes Platform | 99.9% | 99.60% | ✗ BREACHED |
| SLA Dashboard | 99.9% | 99.75% | ✗ BREACHED |
| All Other Services | 99.9% | 99.99% | ✓ MET |

### Breach Detail

**Kubernetes cluster breach (INC-20241020-0032):**
- Duration: 1h 15m (60% capacity loss)
- AWS spot instance reclamation
- Impact: Widespread service degradation
- Root cause: Spot instances in production without PDB or on-demand fallback (policy was in change process, not yet enforced)
- Note: PDB enforcement CHG (July) applied to most but not all deployments. 3 services missed.

**SLA Dashboard breach (INC-20241010-0031):**
- Dashboard showing 0% compliance for 2h
- Column rename in schema migration caused division-by-null
- Operational impact only (internal tooling)

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 1 | 1 (100%) | 100% |
| P2 | Acknowledge 30m, Resolve 4h | 1 | 1 (100%) | 100% |
| P3 | Acknowledge 1h, Resolve 8h | 9 | 9 (100%) | 100% |
| P4 | Acknowledge 4h, Resolve 3d | 21 | 20 (95%) | 95% |

---

## SLA-MONTHLY-2024-11
**Period:** November 2024 | **Report Date:** 2024-12-02
**Overall Compliance Score:** 98.1%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| External API (OAuth2) | 99.9% | 99.80% | ✗ BREACHED |
| All Other Services | 99.9% | 99.99% | ✓ MET |

### Breach Detail

**OAuth2 breach (INC-20241118-0034):**
- Duration: 2h 55m
- JWT signing key rotation incomplete — 3 of 8 validation nodes using old key
- 600 API consumers affected
- Root cause: Key distribution verification not in rotation procedure
- Fix: Key rotation runbook updated, distribution verification added

### Change Performance
- Changes: 28 (Standard: 15, Normal Minor: 9, Normal Major: 4)
- Success rate: 100% (first month at 100% since August)

---

## SLA-MONTHLY-2024-12
**Period:** December 2024 | **Report Date:** 2025-01-06
**Overall Compliance Score:** 98.6%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Payment Gateway (3DS) | 99.95% | 99.88% | ✗ BREACHED |
| All Other Services | 99.9% | 99.99% | ✓ MET |

### Year-End Freeze Period
Change freeze: 2024-12-19 to 2025-01-02. Zero standard/normal changes during freeze. One emergency change: CHG-20241215-0025 (3DS protocol emergency fix). SDM + CTO approval obtained.

### Annual 2024 Review

| Metric | Target | Full-Year Actual |
|---|---|---|
| Overall Availability | 99.9% | 99.87% |
| P1 Incidents | <12/year | 11 ✓ |
| P2 Incidents | <36/year | 28 ✓ |
| Mean Time to Resolve P1 | <1h | 52m ✓ |
| Mean Time to Resolve P2 | <4h | 3h 10m ✓ |
| Change success rate | ≥97% | 96.8% (close miss) |
| SLA credits issued | Minimise | £42,800 total |

**2024 Observations:**
- 11 P1 incidents — all resolved within SLA MTTR target
- Largest cost driver: payment gateway outages (£40K of the £42.8K credits)
- Q4 showed improved resilience post-infrastructure changes
- PostgreSQL upgrade in April delivered persistent 18-22% query performance improvement

---

## SLA-MONTHLY-2025-01
**Period:** January 2025 | **Report Date:** 2025-02-03
**Overall Compliance Score:** 96.4%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| All Services (etcd failure) | 99.9% | 99.94% | ✓ MET (breach below threshold) |
| Billing Service | 99.9% | 99.97% | ✓ MET |

### Notable Events

**etcd cluster failure (INC-20250108-0037):**
- Duration: 45 minutes. All services restored within 1 hour RTO target.
- Data loss: 22 minutes (between backup and failure). RPO breach documented.
- SLA availability: 99.94% — above 99.9% threshold (incident duration below breach threshold)
- However: RPO breach reported to affected enterprise customers. 2 customer credits issued (£3,400).

**Invoice duplicate issue (INC-20250120-0038):**
- 340 accounts received duplicate invoices
- No availability impact but significant customer satisfaction issue
- Credits: £0 (no SLA breach, but customer apology communications sent)

### Incident Response SLA Compliance

| Priority | SLA Target | Tickets Raised | Met SLA | Compliance |
|---|---|---|---|---|
| P1 | Acknowledge 15m, Resolve 1h | 1 | 1 (100%) | 100% |
| P2 | Acknowledge 30m, Resolve 4h | 1 | 1 (100%) | 100% |
| P3 | Acknowledge 1h, Resolve 8h | 7 | 7 (100%) | 100% |
| P4 | Acknowledge 4h, Resolve 3d | 17 | 17 (100%) | 100% |

---

## SLA-MONTHLY-2025-02
**Period:** February 2025 | **Report Date:** 2025-03-04
**Overall Compliance Score:** 99.2%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| All Services | 99.9% | 99.98% | ✓ ALL MET |
| Machine Learning (Recommendations) | 99.5% | 99.79% | ✓ MET |

### Notable Events
Clean month for availability. ML recommendation engine (INC-20250215-0040) caused 2h 40m degradation but remained above 99.5% SLA threshold. Feature store memory increased, model updated for graceful degradation.

### Incident Response SLA Compliance: 100% across all priorities

### Change Stats
- Changes: 22 (all successful)
- Change success rate: 100%

### Service Request SLA Compliance
- Total SRs: 45 | Met SLA: 44 (97.8%) | Missed: 1 (data export request — customer delayed in providing verification)

---

## SLA-MONTHLY-2025-03
**Period:** March 2025 | **Report Date:** 2025-04-01
**Overall Compliance Score:** 98.5%
**Prepared By:** Service Delivery Manager

### Service Availability

| Service | SLA Target | Actual | Status |
|---|---|---|---|
| Core API Platform | 99.9% | 99.93% | ✓ MET |
| EU-West Region | 99.9% | 99.87% | ✗ BREACHED |
| Log Aggregation | 99.9% | 99.76% | ✗ BREACHED |
| All Other Services | 99.9% | 99.99% | ✓ MET |

### Breach Detail

**EU-West breach (INC-20250325-0043):**
- EU-West users: 1h 50m high latency (>8s page loads)
- Database replica lag 28 minutes — read traffic serving stale data
- Root cause: Replica fell behind during batch migration
- Lag-based routing implemented via CHG-20250325-0031

**Log aggregation breach (INC-20250315-0042):**
- Elasticsearch index shard count reduction causing indexing delay
- Recent logs not visible for 3h 30m
- Operational impact (internal tooling) — no customer SLA breach triggered

### Change Performance
- Changes: 31 (Standard: 16, Normal Minor: 11, Normal Major: 4)
- Success rate: 100%

---

## SLA-MONTHLY-2025-04
**Period:** April 2025 (in progress at report date) | **Partial Report Date:** 2025-04-27
**Period Covered:** 2025-04-01 to 2025-04-27 | **Overall Compliance (partial):** 97.9%
**Prepared By:** Service Delivery Manager

### Service Availability (to date)

| Service | SLA Target | MTD Actual | Status |
|---|---|---|---|
| Payment Processing | 99.95% | 99.91% | ✗ BREACHED (Stripe suspension, 33m) |
| Core API Platform | 99.9% | 99.85% | ✗ BREACHED (nginx connection exhaustion, 58m) |
| Customer API v2 | 99.9% | 99.99% | ✓ MET |
| All Other Services | 99.9% | 99.99% | ✓ MET |

### Breach Detail

**Payment breach (INC-20250408-0044):**
- Stripe account suspended by fraud detection — 33 minutes
- £14,000 lost revenue during outage
- Enterprise customer notification: pre-notification to Stripe for large import onboarding added

**Core API breach (INC-20250301-0041 — March carry-over confirmed breach):**
- nginx connection exhaustion — 58 minutes
- nginx worker_connections tuned. Customer API usage policy updated.

### Month-to-Date Metrics

| Metric | Target | MTD Actual |
|---|---|---|
| P1 acknowledgement within 15m | 100% | 100% |
| P1 resolution within 1h | 100% | 100% |
| P2 resolution within 4h | 100% | 100% |
| Change success rate | ≥97% | 100% |
| SRs fulfilled within SLA | ≥95% | 97.3% |

### Risk Flags (April)
- Customer API v2 backward compatibility breach (INC-20250423-0046) — no availability SLA breach but customer impact significant; API contract policy strengthened
- Backup validation gap (INC-20250418-0045) discovered: 11-day backup failure. No data loss but RPO risk identified. Backup monitoring upgraded.

### Forecast: Full Month
Projected April availability: ~99.93% for most services. Payment and Core API breaches will show in final report.

---

## SLA-BREACH-REGISTER-2024-2025
**Period:** January 2024 – April 2025
**Maintained By:** Service Delivery Manager

### All SLA Breaches (P1/P2 causing availability SLA breach)

| Date | Incident | Service | Duration | Priority | SLA Breach | Credits |
|---|---|---|---|---|---|---|
| 2024-01-03 | INC-20240103-0001 | Payment Gateway | 1h 42m | P1 | Yes | £2,100 |
| 2024-01-08 | INC-20240108-0002 | Customer Portal (SSO) | 2h 15m | P2 | Yes | £0 (workaround available) |
| 2024-01-19 | INC-20240119-0004 | Core API | 37m | P1 | No (below threshold) | £0 |
| 2024-01-26 | INC-20240126-0005 | Email Notifications | 5h 20m | P2 | No (99.5% SLA) | £0 |
| 2024-02-10 | INC-20240210-0007 | Database Cluster | 2h 8m | P1 | Yes | £3,800 |
| 2024-02-18 | INC-20240218-0008 | File Upload | 1h 55m | P2 | No (99.5% SLA) | £0 |
| 2024-03-08 | INC-20240308-0010 | API Rate Limiting | 4h 10m | P2 | Yes | £4,200 |
| 2024-03-15 | INC-20240315-0011 | Authentication | 1h 2m | P1 | Yes | £2,900 |
| 2024-04-05 | INC-20240405-0013 | Billing & Invoicing | 24h delay | P2 | Yes | £1,500 |
| 2024-04-12 | INC-20240412-0014 | Search (stale) | 5h | P3 | Yes | £800 |
| 2024-05-02 | INC-20240502-0016 | All Services | 18m | P1 | No (below threshold) | £0 |
| 2024-06-05 | INC-20240605-0019 | Checkout/Payment | 52m | P1 | Yes | £4,400 |
| 2024-06-20 | INC-20240620-0021 | CDN (APAC) | 1h 40m | P2 | Yes | £2,200 |
| 2024-07-10 | INC-20240710-0023 | Real-time Pipeline | 1h 28m | P1 | No (availability met) | £0 |
| 2024-07-18 | INC-20240718-0024 | MFA | 2h 20m | P2 | Yes | £1,100 |
| 2024-08-12 | INC-20240812-0026 | External API | 3h 5m | P2 | No (99.9% SLA met) | £0 |
| 2024-09-05 | INC-20240905-0028 | Database | 2h 45m | P1 | Yes | £4,800 |
| 2024-09-25 | INC-20240925-0030 | Push Notifications | 3h | P3 | No (99.5% SLA) | £0 |
| 2024-10-10 | INC-20241010-0031 | SLA Dashboard | 2h | P2 | Yes (internal) | £0 |
| 2024-10-20 | INC-20241020-0032 | Kubernetes | 1h 15m | P1 | Yes | £3,200 |
| 2024-11-18 | INC-20241118-0034 | OAuth2 API | 2h 55m | P2 | Yes | £2,100 |
| 2024-12-15 | INC-20241215-0036 | Payment 3DS | 1h 20m | P2 | Yes | £1,800 |
| 2025-01-08 | INC-20250108-0037 | All Services | 45m | P1 | No (RPO breach only) | £3,400 |
| 2025-03-01 | INC-20250301-0041 | Core API | 58m | P1 | Yes | £1,200 |
| 2025-03-25 | INC-20250325-0043 | EU-West Region | 1h 50m | P2 | Yes | £900 |
| 2025-04-08 | INC-20250408-0044 | Payment | 33m | P1 | Yes | £2,800 |

**Total SLA Credits Issued (Jan 2024 – Apr 2025):** £42,800

### Repeat Breach Services (2+ breaches)
- **Payment Gateway:** 4 breaches — highest priority for hardening
- **Database Cluster:** 3 breaches — WAL and autovacuum improvements implemented
- **Core API Platform:** 2 breaches — nginx tuning and capacity monitoring improved
- **Authentication/IAM:** 2 breaches — certificate management automated
