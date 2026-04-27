# SDC Historical Incident Records

---

## INC-20240103-0001
**Date:** 2024-01-03 | **Priority:** P1 | **Status:** Resolved
**Service:** Payment Gateway | **Duration:** 1h 42m
**Affected Users:** ~2,400 | **Business Impact:** £18,000 estimated revenue loss
**Reported By:** Automated monitoring (Dash0 alert)
**Resolver Group:** Application Engineering – Payments

**Description:** Payment gateway returned HTTP 503 for all card transactions. Checkout flow completely broken for all customer-facing storefronts.

**Timeline:**
- 08:14 UTC – Dash0 alert fires: payment-gateway error rate >50%
- 08:16 UTC – Incident declared P1, war room opened on Teams #incident-bridge
- 08:18 UTC – Duty Manager and Payments Lead joined bridge
- 08:35 UTC – Root cause narrowed to database connection pool exhaustion
- 09:21 UTC – Connection pool limit increased from 50 to 150; service restored
- 09:56 UTC – All monitoring green; incident resolved

**Root Cause:** Deployment of v2.3.1 introduced a connection leak. Each request opened a new DB connection but failed to close it on exception paths. Pool exhausted after ~4 hours of overnight traffic.

**Resolution:** Increased pool limit as immediate workaround; hotfix v2.3.2 deployed to close connections on exception. Problem record PRB-20240103-0001 raised.

**Lessons Learned:** Connection pool exhaustion not monitored in staging. Monitoring parity checklist updated.

---

## INC-20240108-0002
**Date:** 2024-01-08 | **Priority:** P2 | **Status:** Resolved
**Service:** Customer Portal (Authentication) | **Duration:** 2h 15m
**Affected Users:** ~340 | **Business Impact:** High – users locked out of accounts
**Reported By:** Service Desk (multiple tickets received)
**Resolver Group:** Identity & Access Management

**Description:** SSO login failures for all users federated via Azure AD. Internal accounts unaffected.

**Timeline:**
- 14:05 UTC – Service Desk receives 3rd login failure ticket, escalates to L2
- 14:22 UTC – L2 identifies pattern: Azure AD federation only
- 14:30 UTC – Azure AD admin confirms tenant token signing certificate rotated automatically
- 15:10 UTC – New certificate metadata uploaded to SDC IdP
- 16:20 UTC – All users able to log in; incident resolved

**Root Cause:** Azure AD certificate auto-rotation (annual) not reflected in SDC IdP metadata. No alert configured for certificate expiry mismatch.

**Resolution:** Updated IdP metadata. Added certificate expiry monitoring for all federation partners.

**Lessons Learned:** External IdP certificate rotation must be tracked. SLA: 2 business hours for P2 login failures met.

---

## INC-20240115-0003
**Date:** 2024-01-15 | **Priority:** P3 | **Status:** Resolved
**Service:** Reporting Module | **Duration:** 4h 30m
**Affected Users:** 12 (Finance team)
**Reported By:** Finance Manager via Service Desk ticket
**Resolver Group:** Data Engineering

**Description:** Monthly financial reports showing incorrect totals. Data discrepancy of approximately 3% in aggregated figures.

**Root Cause:** ETL pipeline timestamp handling bug introduced in pipeline v1.8.0 caused some records timestamped 23:50–23:59 to be excluded from daily aggregations due to UTC/local time mismatch.

**Resolution:** ETL pipeline reprocessed for affected date range (2024-01-01 to 2024-01-14). Reports regenerated and validated by Finance.

**Lessons Learned:** ETL pipeline testing must include boundary time values. Added timezone edge case tests to pipeline test suite.

---

## INC-20240119-0004
**Date:** 2024-01-19 | **Priority:** P1 | **Status:** Resolved
**Service:** Core API Platform | **Duration:** 37m
**Affected Users:** All (estimated 8,000+)
**Business Impact:** Critical – all downstream services dependent on Core API
**Reported By:** Automated monitoring (Dash0 – response time >5s p99)
**Resolver Group:** Platform Engineering

**Description:** Core API response times degraded to >8 seconds p99, then completely unavailable for 12 minutes.

**Timeline:**
- 11:02 UTC – Dash0 alert: p99 latency >5s
- 11:04 UTC – P1 declared
- 11:08 UTC – Platform team identifies Redis cache cluster degraded (1 of 3 nodes down)
- 11:18 UTC – Redis node restarted; cache warming begins
- 11:39 UTC – Latency returns to normal p99 <200ms; incident resolved

**Root Cause:** Redis cluster node ran out of disk space due to AOF log not being rotated. Node became read-only, then unresponsive. Other two nodes unable to handle full traffic alone.

**Resolution:** Disk cleared, AOF rotation policy enforced, node rejoined cluster. Problem record raised for permanent disk monitoring solution.

**Lessons Learned:** Redis disk usage not monitored. Added disk space alert for all cache nodes (>75% threshold).

---

## INC-20240126-0005
**Date:** 2024-01-26 | **Priority:** P2 | **Status:** Resolved
**Service:** Email Notification Service | **Duration:** 5h 20m
**Affected Users:** Indirect – 4,200 users did not receive notifications
**Reported By:** Customer complaint escalated via Account Manager
**Resolver Group:** Messaging Team

**Description:** Transactional emails (order confirmations, password resets) not being delivered for 5+ hours. Queue backed up to 47,000 messages.

**Root Cause:** SMTP relay provider (SendGrid) IP range added to external spam block list. All outbound mail silently dropped.

**Resolution:** Switched to secondary SMTP relay (AWS SES). Queued messages flushed over 2 hours. Notified affected customers via alternative channel.

**Lessons Learned:** Single SMTP relay provider is SPOF. Secondary relay now configured and tested quarterly.

---

## INC-20240202-0006
**Date:** 2024-02-02 | **Priority:** P3 | **Status:** Resolved
**Service:** Mobile App (iOS) | **Duration:** 3h
**Affected Users:** ~180 on iOS 17.3
**Reported By:** App store reviews + Service Desk
**Resolver Group:** Mobile Engineering

**Description:** App crashes on launch for users who updated to iOS 17.3. Android unaffected.

**Root Cause:** iOS 17.3 changed background thread scheduling behaviour. A race condition in the app's startup sequence, previously masked by timing, became a consistent crash.

**Resolution:** Hotfix v4.2.1 released to App Store. Users advised to update. Fix reviewed and approved via emergency App Store submission.

**Lessons Learned:** Beta OS versions must be included in pre-release test matrix. Added iOS beta lane to CI pipeline.

---

## INC-20240210-0007
**Date:** 2024-02-10 | **Priority:** P1 | **Status:** Resolved
**Service:** Database Cluster (Primary) | **Duration:** 2h 8m
**Affected Users:** All services using primary DB
**Business Impact:** Full write operations unavailable
**Reported By:** Automated monitoring
**Resolver Group:** DBA Team + Platform Engineering

**Description:** Primary PostgreSQL node failed. Automatic failover to replica triggered but replica was 18 minutes behind, causing partial data inconsistency window.

**Timeline:**
- 03:22 UTC – Primary node unreachable
- 03:22 UTC – Automatic failover initiated (pg_auto_failover)
- 03:40 UTC – Replica promoted, replica lag resolved, writes restored
- 05:30 UTC – Primary node investigated, root cause identified (disk I/O saturation), node returned to service as standby

**Root Cause:** Runaway vacuum process combined with high write load caused disk I/O saturation on primary. Node became unresponsive.

**Resolution:** Tuned autovacuum settings, added I/O saturation alert. Replica lag monitoring added.

**Lessons Learned:** Replica lag was not monitored. Failover SLO now includes max acceptable lag measurement.

---

## INC-20240218-0008
**Date:** 2024-02-18 | **Priority:** P2 | **Status:** Resolved
**Service:** File Upload Service | **Duration:** 1h 55m
**Affected Users:** ~220 (all users uploading files >10MB)
**Reported By:** Support tickets
**Resolver Group:** Storage Engineering

**Description:** All file uploads larger than 10MB failing with HTTP 413. Customers unable to upload documents, contracts, or media.

**Root Cause:** nginx ingress proxy body size limit was reset to default (10MB) during CHG-20240215-0012 (ingress configuration update). Change was not tested with large file uploads.

**Resolution:** nginx client_max_body_size reset to 100MB. Verified with 50MB test upload. Problem linked to change failure.

**Lessons Learned:** Upload size testing added to post-change verification checklist for any ingress configuration changes.

---

## INC-20240301-0009
**Date:** 2024-03-01 | **Priority:** P3 | **Status:** Resolved
**Service:** Analytics Dashboard | **Duration:** 2h 20m
**Affected Users:** 45 (Analytics team)
**Reported By:** Team Lead via Service Desk
**Resolver Group:** Data Engineering

**Description:** Dashboard charts not loading. Page displayed blank widget areas with spinner indefinitely.

**Root Cause:** Grafana data source connection to ClickHouse cluster timed out after ClickHouse maintenance window (overnight) left one shard in degraded state.

**Resolution:** Degraded ClickHouse shard repaired and rebalanced. Grafana data source connection reset.

**Lessons Learned:** Post-maintenance health checks must include all downstream consumers. Added dashboard smoke test to maintenance runbook.

---

## INC-20240308-0010
**Date:** 2024-03-08 | **Priority:** P2 | **Status:** Resolved
**Service:** API Rate Limiting / Gateway | **Duration:** 4h 10m
**Affected Users:** 12 enterprise API customers
**Business Impact:** SLA breach for 3 customers
**Reported By:** Customer complaint (API returning 429 unexpectedly)
**Resolver Group:** Platform Engineering

**Description:** Enterprise API customers with dedicated rate limit tiers receiving 429 Too Many Requests errors despite being within their contracted limits.

**Root Cause:** Rate limit configuration stored in Redis was flushed during INC-20240119-0004 recovery. Redis was restored from a 6-hour-old backup, losing customer tier configuration updates made that day.

**Resolution:** Customer rate limit tiers restored from CMDB source of truth. Redis configuration sync now automated from CMDB on startup.

**Lessons Learned:** Redis configuration must not be treated as authoritative source. Configuration-as-code principle reinforced.

---

## INC-20240315-0011
**Date:** 2024-03-15 | **Priority:** P1 | **Status:** Resolved
**Service:** Authentication Service | **Duration:** 1h 2m
**Affected Users:** All users (~8,000)
**Business Impact:** Complete login outage
**Reported By:** Automated monitoring + customer escalation
**Resolver Group:** Identity & Access Management

**Description:** All user logins failing across all channels (web, mobile, API). JWT signing service returned 500.

**Root Cause:** TLS certificate for internal JWT signing service expired. Certificate was not in the automated renewal scope (added manually, not via IaC).

**Resolution:** Certificate manually renewed via Let's Encrypt. Service restarted. All authentication restored.

**Lessons Learned:** All TLS certificates must be managed via IaC / automated renewal. Manual certificates now prohibited. Audit of remaining manual certificates initiated.

---

## INC-20240322-0012
**Date:** 2024-03-22 | **Priority:** P3 | **Status:** Resolved
**Service:** Customer Notification Preferences | **Duration:** 3h 15m
**Affected Users:** ~800 (customers who updated preferences)
**Reported By:** Service Desk (pattern identified after 8 tickets)
**Resolver Group:** Application Engineering

**Description:** Changes to notification preferences (email/SMS opt-in/out) not being saved. Users experiencing the same unwanted notifications despite changing settings.

**Root Cause:** Preferences service write path was calling a deprecated API endpoint that returned 200 but silently discarded writes after v3.1.0 of the preferences backend.

**Resolution:** Write path updated to use current API endpoint. Affected users' preferences re-applied from audit log.

**Lessons Learned:** Deprecated endpoints must not return 200. Breaking change documentation improved. API versioning policy updated.

---

## INC-20240405-0013
**Date:** 2024-04-05 | **Priority:** P2 | **Status:** Resolved
**Service:** Billing & Invoicing | **Duration:** 3h 30m
**Affected Users:** Finance team + customers with April invoices
**Business Impact:** Invoice generation delayed by 24h
**Reported By:** Finance Manager
**Resolver Group:** Finance Tech Team

**Description:** Monthly invoice generation job failed silently at 02:00 UTC. No invoices generated for April billing cycle.

**Root Cause:** Invoice job references an S3 bucket for template storage. Bucket policy was modified during a security hardening exercise (CHG-20240402-0008), removing the service account's read permissions.

**Resolution:** S3 bucket policy corrected. Invoice job re-run manually. All invoices generated and sent.

**Lessons Learned:** Service account permissions must be included in change impact assessment. IAM change testing must include integration tests.

---

## INC-20240412-0014
**Date:** 2024-04-12 | **Priority:** P3 | **Status:** Resolved
**Service:** Search Service | **Duration:** 5h
**Affected Users:** ~1,200 (users using search)
**Reported By:** Customer feedback form + Service Desk
**Resolver Group:** Search Engineering

**Description:** Product search returning stale results (up to 3 days old). New products not appearing in search. Elasticsearch index not updating.

**Root Cause:** Elasticsearch index sync job was failing silently due to a Kafka consumer group rebalance loop. Consumer group never stabilised due to a misconfigured `max.poll.interval.ms` after cluster version upgrade.

**Resolution:** Kafka consumer configuration corrected. Index sync job restarted. Manual index refresh triggered to catch up on 3 days of changes.

**Lessons Learned:** Kafka consumer lag must be monitored. Alert added for consumer group not committing offsets.

---

## INC-20240420-0015
**Date:** 2024-04-20 | **Priority:** P2 | **Status:** Resolved
**Service:** Data Export Service | **Duration:** 2h 45m
**Affected Users:** 34 (enterprise customers using bulk export)
**Reported By:** Customer (Enterprise Account)
**Resolver Group:** Data Engineering

**Description:** GDPR data export requests stuck in "Processing" state indefinitely. Export never completed or failed, just hung.

**Root Cause:** Export worker deadlocked when processing an account with >500,000 records. A mutex lock acquired during chunk processing was never released if chunk size exceeded memory buffer.

**Resolution:** Lock release moved to finally block. Worker restarted. Affected exports re-queued and completed within 30 minutes.

**Lessons Learned:** Large data processing paths must include load testing with realistic data volumes. Added export worker lock timeout (60s).

---

## INC-20240502-0016
**Date:** 2024-05-02 | **Priority:** P1 | **Status:** Resolved
**Service:** Core Platform (all services) | **Duration:** 18m
**Affected Users:** All (~8,000)
**Business Impact:** Full platform outage
**Reported By:** Automated monitoring
**Resolver Group:** Platform Engineering + Network Team

**Description:** All services returned 502 Bad Gateway. Complete platform outage.

**Root Cause:** BGP route advertisement withdrawn by ISP during network equipment maintenance. Traffic could not reach SDC data centre for 18 minutes.

**Resolution:** ISP restored BGP advertisement. Automatic failover to secondary ISP path did not trigger (failover threshold set too high). Threshold reconfigured.

**Lessons Learned:** BGP failover threshold was 5 minutes (too long). Reduced to 90 seconds. ISP maintenance windows must be communicated to SDC NOC in advance.

---

## INC-20240510-0017
**Date:** 2024-05-10 | **Priority:** P3 | **Status:** Resolved
**Service:** Customer Onboarding | **Duration:** 2h
**Affected Users:** ~25 (new customers being onboarded)
**Reported By:** Account Manager
**Resolver Group:** Application Engineering

**Description:** New customer account activation emails not being sent. Welcome emails went to spam or not delivered.

**Root Cause:** SPF record not updated after migration to new mail infrastructure (CHG-20240430-0015). Receiving mail servers rejected messages as SPF fail.

**Resolution:** SPF record updated to include new mail infrastructure IP ranges. Affected customers re-sent activation emails.

**Lessons Learned:** DNS/email configuration changes must be validated with email deliverability test tools post-change.

---

## INC-20240518-0018
**Date:** 2024-05-18 | **Priority:** P2 | **Status:** Resolved
**Service:** Webhook Delivery | **Duration:** 3h 15m
**Affected Users:** 28 customers using webhooks
**Business Impact:** Delayed or missed webhook events
**Reported By:** Customer complaint
**Resolver Group:** Integration Engineering

**Description:** Webhooks not being delivered. Events queuing up internally but not being sent to customer endpoints. Queue depth reached 180,000 events.

**Root Cause:** Webhook worker pods crashed due to OOMKilled. Memory limit set to 256Mi was insufficient for the current webhook payload sizes after a customer started sending large JSON payloads.

**Resolution:** Memory limit increased to 512Mi. Pod replica count increased. Queue drained over 45 minutes.

**Lessons Learned:** Per-pod memory limits must be reviewed when payload size characteristics change. Added Kubernetes OOMKilled alert.

---

## INC-20240605-0019
**Date:** 2024-06-05 | **Priority:** P1 | **Status:** Resolved
**Service:** Checkout & Payment | **Duration:** 52m
**Affected Users:** ~3,100
**Business Impact:** £22,000 estimated lost revenue
**Reported By:** Automated monitoring (error rate spike)
**Resolver Group:** Payments Engineering

**Description:** Stripe payment processing returning "card_declined" for all cards. Not a card issue — integration layer was sending malformed requests.

**Root Cause:** Stripe API version pinned in code was deprecated and removed by Stripe. All requests after deprecation date rejected.

**Resolution:** Stripe API version updated to current stable. Deployed as emergency change ECB-20240605-001.

**Lessons Learned:** External API deprecation notices must be tracked and acted on proactively. Added Stripe API deprecation monitoring to vendor review process.

---

## INC-20240614-0020
**Date:** 2024-06-14 | **Priority:** P3 | **Status:** Resolved
**Service:** Internal HR Portal | **Duration:** 6h
**Affected Users:** HR Team (18 users)
**Reported By:** HR Manager
**Resolver Group:** Corporate IT

**Description:** HR portal unable to generate payroll reports. Export button returned 500 error.

**Root Cause:** Database view used by payroll report query was dropped accidentally during a schema migration (CHG-20240612-0021). Migration rollback plan did not account for dependent views.

**Resolution:** Database view recreated from version control. Payroll reports generated successfully.

**Lessons Learned:** Database migration scripts must check for and recreate dependent views in rollback procedures.

---

## INC-20240620-0021
**Date:** 2024-06-20 | **Priority:** P2 | **Status:** Resolved
**Service:** Content Delivery (CDN) | **Duration:** 1h 40m
**Affected Users:** ~1,800 (users in APAC region)
**Reported By:** Customer complaints (APAC accounts)
**Resolver Group:** Network Engineering + CDN Provider

**Description:** Static assets (images, CSS, JS) not loading for users in Australia and South-East Asia. Pages appeared broken/unstyled.

**Root Cause:** CDN PoP in Singapore went offline due to provider hardware failure. No automatic failover to Hong Kong PoP configured.

**Resolution:** CDN provider restored Singapore PoP. SDC configured failover routing to Hong Kong as interim. Permanent: multi-PoP failover configured.

**Lessons Learned:** CDN failover must be configured and tested. PoP failover now tested quarterly.

---

## INC-20240702-0022
**Date:** 2024-07-02 | **Priority:** P3 | **Status:** Resolved
**Service:** Password Reset | **Duration:** 1h 50m
**Affected Users:** ~90 (users attempting password reset)
**Reported By:** Service Desk
**Resolver Group:** Identity & Access Management

**Description:** Password reset emails delivered but reset links returning 404. Users unable to reset passwords.

**Root Cause:** Password reset token validation service was deployed to a new URL during infrastructure migration but the email template still referenced the old URL.

**Resolution:** Email template updated with new reset URL. Link validation service reconfigured. Affected users asked to request new reset links.

**Lessons Learned:** URL changes in email templates must be explicitly included in migration checklists.

---

## INC-20240710-0023
**Date:** 2024-07-10 | **Priority:** P1 | **Status:** Resolved
**Service:** Real-time Data Pipeline | **Duration:** 1h 28m
**Affected Users:** All services consuming real-time events
**Business Impact:** 88-minute gap in event processing
**Reported By:** Automated monitoring (Kafka lag alert)
**Resolver Group:** Data Engineering

**Description:** Kafka consumer lag grew to 2.4 million messages. Real-time dashboards frozen. Alerting delayed.

**Root Cause:** A large customer imported 8 years of historical data simultaneously, creating a burst of 2.4M events. Consumer group could not keep up. Backpressure not implemented.

**Resolution:** Consumer group scaled from 6 to 24 pods. Historical import rate-limited. Lag cleared within 3 hours.

**Lessons Learned:** Bulk data imports must be rate-limited at ingestion point. Added consumer lag alerting at 100k messages threshold.

---

## INC-20240718-0024
**Date:** 2024-07-18 | **Priority:** P2 | **Status:** Resolved
**Service:** Multi-factor Authentication | **Duration:** 2h 20m
**Affected Users:** ~420 (users with MFA enabled)
**Reported By:** Customer complaints + Service Desk
**Resolver Group:** Identity & Access Management

**Description:** TOTP MFA codes rejected as invalid. Authenticator app codes not accepted despite being generated correctly.

**Root Cause:** Server time drifted by 4 minutes due to NTP synchronisation failure on MFA service host. TOTP window is ±30 seconds; 4-minute drift fell outside acceptable range.

**Resolution:** NTP re-synchronised. Server time corrected. All MFA codes immediately valid.

**Lessons Learned:** NTP synchronisation failure must be monitored. Clock drift alert added at ±10 seconds threshold.

---

## INC-20240801-0025
**Date:** 2024-08-01 | **Priority:** P3 | **Status:** Resolved
**Service:** Customer Self-Service Portal | **Duration:** 4h
**Affected Users:** ~150
**Reported By:** Service Desk (ticket volume spike)
**Resolver Group:** Application Engineering

**Description:** Customer portal showing error "Your account is suspended" for active accounts. Customers unable to access services.

**Root Cause:** Automated account review job misclassified accounts with payment method update pending as "payment overdue" and suspended them. Logic error in the payment status check.

**Resolution:** Account review job rolled back to previous version. Affected accounts reinstated. Customer apology communications sent.

**Lessons Learned:** Account status changes must require human approval for suspension actions. Automated suspension disabled pending review.

---

## INC-20240812-0026
**Date:** 2024-08-12 | **Priority:** P2 | **Status:** Resolved
**Service:** API Platform (External) | **Duration:** 3h 5m
**Affected Users:** 8 enterprise API customers
**Reported By:** Customer (direct alert)
**Resolver Group:** Platform Engineering

**Description:** API customers experiencing intermittent 504 Gateway Timeout on large requests (>1MB body). Occurred 30% of the time.

**Root Cause:** Load balancer timeout set to 60 seconds but processing for large payloads taking up to 75 seconds. Balancer killed connections before response.

**Resolution:** Load balancer timeout increased to 120 seconds for the API tier. Long-term fix: streaming API for large payloads raised as story.

**Lessons Learned:** Timeout values must be aligned end-to-end: client, load balancer, application, database.

---

## INC-20240820-0027
**Date:** 2024-08-20 | **Priority:** P3 | **Status:** Resolved
**Service:** Reporting (Scheduled Reports) | **Duration:** 5h 30m
**Affected Users:** 35 (subscribers to scheduled reports)
**Reported By:** Customer complaint
**Resolver Group:** Data Engineering

**Description:** Weekly scheduled reports not sent on Monday morning. Subscribers received nothing.

**Root Cause:** Report scheduler was using local server timezone (BST, UTC+1) but job cron was defined in UTC. After daylight saving adjustment, job ran 1 hour late — but ran at 08:00 BST on Sunday instead of Monday (cron day boundary shift).

**Resolution:** All cron jobs standardised to UTC explicitly. Affected reports sent manually. DST handling documented in job scheduling standards.

**Lessons Learned:** All scheduled jobs must be defined in UTC explicitly. DST transition checklist added to quarterly operations calendar.

---

## INC-20240905-0028
**Date:** 2024-09-05 | **Priority:** P1 | **Status:** Resolved
**Service:** Core Database | **Duration:** 2h 45m
**Affected Users:** All
**Business Impact:** Write operations unavailable
**Reported By:** Automated monitoring
**Resolver Group:** DBA Team

**Description:** Database primary node ran out of disk space. All write operations failed with "no space left on device". Read operations unaffected.

**Root Cause:** Transaction log files not being purged. WAL archiving was enabled for a new DR setup but archiving target became unavailable. PostgreSQL continued writing WAL locally, filling disk.

**Resolution:** WAL archive target restored. Old WAL files cleared (after verification archiving was caught up). Disk alerts added at 70% and 85%.

**Lessons Learned:** WAL archiving failure must trigger an alert. Disk usage monitoring was in place but threshold was set at 95% — too late.

---

## INC-20240915-0029
**Date:** 2024-09-15 | **Priority:** P2 | **Status:** Resolved
**Service:** Customer Import Tool | **Duration:** 1h 30m
**Affected Users:** 5 (admin users doing bulk imports)
**Reported By:** Operations Team
**Resolver Group:** Application Engineering

**Description:** Bulk customer CSV import tool failing at row ~5,000 for all files regardless of content. Import job terminated without error message.

**Root Cause:** PHP memory limit set to 128MB in the import worker was being hit when processing files with >5,000 rows. Exception was swallowed by a bare except clause, causing silent failure.

**Resolution:** Memory limit increased to 512MB. Exception logging added. Import retry triggered successfully.

**Lessons Learned:** Import tools must log all exceptions with row context. Memory limits for batch processes must be sized for maximum expected input.

---

## INC-20240925-0030
**Date:** 2024-09-25 | **Priority:** P3 | **Status:** Resolved
**Service:** Notification Service (Push) | **Duration:** 3h
**Affected Users:** ~2,200 (mobile app users)
**Reported By:** Service Desk
**Resolver Group:** Mobile + Messaging Teams

**Description:** Push notifications not being received on Android devices. iOS unaffected.

**Root Cause:** Firebase Cloud Messaging (FCM) legacy API used for Android push notifications was deprecated and shut down by Google on September 20, 2024. Migration to FCM v1 API was scheduled but not completed.

**Resolution:** Emergency migration to FCM v1 API completed. Android push notifications restored.

**Lessons Learned:** Google's FCM deprecation was known for 12 months. Migration backlog item was not prioritised. External API deprecation tracking improved.

---

## INC-20241010-0031
**Date:** 2024-10-10 | **Priority:** P2 | **Status:** Resolved
**Service:** SLA Reporting Dashboard | **Duration:** 2h
**Affected Users:** SDM team + customers with SLA visibility
**Reported By:** Service Delivery Manager
**Resolver Group:** Data Engineering

**Description:** SLA compliance dashboard showing 0% compliance for all metrics. Data clearly incorrect.

**Root Cause:** Metrics aggregation query was dividing by total_incidents but the column was renamed to total_count in a schema migration. Division by null → metrics calculated as null → displayed as 0%.

**Resolution:** Query updated to use correct column name. Dashboard recalculated. Values restored to accurate figures.

**Lessons Learned:** Breaking database schema changes must include grep of all dependent queries. Schema migration testing must include dashboard smoke tests.

---

## INC-20241020-0032
**Date:** 2024-10-20 | **Priority:** P1 | **Status:** Resolved
**Service:** Kubernetes Cluster (Production) | **Duration:** 1h 15m
**Affected Users:** All services
**Business Impact:** Full service degradation – 60% capacity loss
**Reported By:** Automated monitoring
**Resolver Group:** Platform Engineering

**Description:** Production Kubernetes cluster lost 4 of 6 worker nodes simultaneously. Services degraded to 40% capacity. Several services completely down due to single-pod deployments.

**Root Cause:** Cloud provider (AWS) performed emergency spot instance reclamation. SDC was running 4 spot nodes in production without equivalent on-demand fallback configured.

**Resolution:** Spot nodes replaced with on-demand instances. PodDisruptionBudgets enforced for all critical services. Spot nodes limited to non-critical workloads.

**Lessons Learned:** Production critical workloads must not run exclusively on spot instances. DR runbook updated. Kubernetes cluster design reviewed.

---

## INC-20241105-0033
**Date:** 2024-11-05 | **Priority:** P3 | **Status:** Resolved
**Service:** User Management API | **Duration:** 2h 30m
**Affected Users:** Admins performing user management
**Reported By:** IT Admin team
**Resolver Group:** Application Engineering

**Description:** API calls to deactivate user accounts returning 200 but accounts remaining active in the system.

**Root Cause:** Deactivation endpoint updated to async processing (writes to queue) but the queue consumer was not deployed. Requests acknowledged but never processed.

**Resolution:** Queue consumer service deployed. Backlog of deactivation requests processed. All intended deactivations confirmed.

**Lessons Learned:** Consumer services must be deployed before or simultaneously with producer changes. Deployment dependency documented in RFC.

---

## INC-20241118-0034
**Date:** 2024-11-18 | **Priority:** P2 | **Status:** Resolved
**Service:** External API (OAuth2) | **Duration:** 2h 55m
**Affected Users:** ~600 API consumers using OAuth2
**Reported By:** Customer complaint
**Resolver Group:** Platform Engineering + IAM

**Description:** OAuth2 token issuance failing. All API consumers using OAuth2 unable to obtain tokens. API key authentication unaffected.

**Root Cause:** OAuth2 server private key used for JWT signing was rotated as part of security hardening (CHG-20241115-0033) but the new key was not distributed to all token validation nodes. Tokens issued by one node could not be validated by others.

**Resolution:** Private key distributed to all nodes. Rolling restart of validation service. All tokens reissued.

**Lessons Learned:** Cryptographic key rotation must include validation node distribution as part of the change procedure. Tested in staging first.

---

## INC-20241205-0035
**Date:** 2024-12-05 | **Priority:** P3 | **Status:** Resolved
**Service:** Customer Survey Tool | **Duration:** 1h 45m
**Affected Users:** 22 customers (survey recipients)
**Reported By:** Customer Success Manager
**Resolver Group:** Application Engineering

**Description:** NPS survey links in emails resulting in 404. Survey campaign failed to send correctly to 1,800 recipients.

**Root Cause:** Survey URL generation used production domain config. Deployment to staging overrode the URL config and was promoted to production without review of environment-specific settings.

**Resolution:** Production URL configuration restored. Survey resent to all recipients with corrected links.

**Lessons Learned:** Environment-specific configuration must be separated from application config. Twelve-factor app principles enforced for config management.

---

## INC-20241215-0036
**Date:** 2024-12-15 | **Priority:** P2 | **Status:** Resolved
**Service:** Payment Gateway | **Duration:** 1h 20m
**Affected Users:** ~950 checkout sessions
**Business Impact:** ~£8,500 estimated lost revenue
**Reported By:** Automated monitoring
**Resolver Group:** Payments Engineering

**Description:** 3DS (3D Secure) authentication failures for Visa cards. Mastercard unaffected. Customers unable to complete checkout requiring 3DS.

**Root Cause:** Visa 3DS2 protocol version changed from 2.1 to 2.2. SDC payment integration was pinned to 2.1 which Visa began rejecting.

**Resolution:** Payment integration updated to support 3DS2 v2.2. Deployed as emergency change.

**Lessons Learned:** Payment protocol version tracking added to vendor management calendar. Quarterly review of payment integration compatibility.

---

## INC-20250108-0037
**Date:** 2025-01-08 | **Priority:** P1 | **Status:** Resolved
**Service:** All Services | **Duration:** 45m
**Affected Users:** All
**Reported By:** Automated monitoring (multiple alerts)
**Resolver Group:** Platform Engineering

**Description:** Complete platform outage. All services returning 503. Kubernetes API server unreachable.

**Root Cause:** etcd cluster (Kubernetes state store) lost quorum. Two of three etcd nodes failed simultaneously due to same underlying SSD firmware bug causing data corruption.

**Resolution:** etcd cluster restored from hourly backup (22-minute data loss). Kubernetes cluster recovered. Services restarted.

**Lessons Learned:** etcd nodes must not share same hardware generation. Anti-affinity rules for etcd pods enforced. Recovery RTO achieved: 45 minutes (target: 1 hour).

---

## INC-20250120-0038
**Date:** 2025-01-20 | **Priority:** P2 | **Status:** Resolved
**Service:** Billing Service | **Duration:** 3h
**Affected Users:** Finance team
**Reported By:** Finance Director
**Resolver Group:** Finance Tech Team

**Description:** January invoice run produced duplicate invoices for 340 accounts. Each affected customer received two invoices for the same period.

**Root Cause:** Invoice generation job ran twice. First run triggered by automated scheduler, second manually triggered by Finance team member who was unaware the automated run had completed (no visibility of job status).

**Resolution:** Duplicate invoices cancelled in billing system. Customer notification sent apologising for confusion. Manual trigger requires job status check added to UI.

**Lessons Learned:** Batch jobs must display current run status before allowing manual trigger. Idempotency key added to invoice job to prevent duplicate runs.

---

## INC-20250202-0039
**Date:** 2025-02-02 | **Priority:** P3 | **Status:** Resolved
**Service:** Internal Ticketing Integration | **Duration:** 4h
**Affected Users:** L2/L3 support teams
**Reported By:** Support Team Lead
**Resolver Group:** Integration Engineering

**Description:** ITSM tickets not syncing to Jira. Support engineers losing track of tickets requiring development team input.

**Root Cause:** Jira webhook signing key was rotated during a Jira Cloud admin operation. SDC integration was validating webhook signatures against the old key.

**Resolution:** Webhook signing key updated in SDC integration config. Sync resumed. Missed tickets manually synced.

**Lessons Learned:** Webhook integration keys must be managed in secrets manager with rotation alerts to integration owners.

---

## INC-20250215-0040
**Date:** 2025-02-15 | **Priority:** P2 | **Status:** Resolved
**Service:** Machine Learning Recommendation Engine | **Duration:** 2h 40m
**Affected Users:** All users (degraded recommendations)
**Reported By:** Data Science Team
**Resolver Group:** ML Engineering

**Description:** Recommendation engine returning default/fallback recommendations for all users. Personalisation completely absent.

**Root Cause:** Feature store (Redis cluster serving ML features) ran out of memory and evicted all cached features. Eviction policy was allkeys-lru but the model expected all features present.

**Resolution:** Redis memory increased. Feature store repopulated from training data pipeline. TTL reduced to manage memory growth.

**Lessons Learned:** Feature store must have memory usage alerts. Model must gracefully degrade when features are partially available rather than returning defaults.

---

## INC-20250301-0041
**Date:** 2025-03-01 | **Priority:** P1 | **Status:** Resolved
**Service:** Core API Platform | **Duration:** 58m
**Affected Users:** All
**Business Impact:** Full API outage
**Reported By:** Automated monitoring
**Resolver Group:** Platform Engineering

**Description:** Core API returning 502 for all endpoints. Services unable to process requests.

**Root Cause:** Rate of TLS handshakes exceeded nginx worker process limits. Sudden spike in new connections (from a customer running a large batch job with poor connection pooling) caused nginx to drop connections.

**Resolution:** nginx worker_connections limit increased. Customer's batch job connection pooling fixed. nginx configuration reviewed and tuned for expected peak load.

**Lessons Learned:** nginx connection limits not tracked as capacity metric. Added to Dash0 monitoring dashboard. Customer API usage policy updated to require connection pooling.

---

## INC-20250315-0042
**Date:** 2025-03-15 | **Priority:** P3 | **Status:** Resolved
**Service:** Log Aggregation (Internal) | **Duration:** 3h 30m
**Affected Users:** Engineering + Operations (internal)
**Reported By:** On-call engineer
**Resolver Group:** Platform Engineering

**Description:** Kibana/Elastic search not returning recent logs (logs older than 4 hours not visible). Engineers unable to diagnose issues.

**Root Cause:** Elasticsearch index template changed the number of shards for new indices. New day's index created with 1 shard instead of 5, causing write throughput to fall behind ingest rate. Ingest backed up, indexing delayed.

**Resolution:** Index recreated with correct shard count. Logstash pipeline restarted. Backlog of logs indexed within 2 hours.

**Lessons Learned:** Index template changes must be tested against peak ingest rates. Logstash backpressure monitoring added.

---

## INC-20250325-0043
**Date:** 2025-03-25 | **Priority:** P2 | **Status:** Resolved
**Service:** Multi-Region Failover | **Duration:** 1h 50m
**Affected Users:** EU-West users (~1,600)
**Reported By:** Automated monitoring
**Resolver Group:** Network + Platform Engineering

**Description:** EU-West region users experiencing >8s page load times. Traffic routing correctly but latency unacceptably high.

**Root Cause:** EU-West primary database replica fell behind by 28 minutes due to high replication load from a batch migration. Read traffic was being served from a stale replica.

**Resolution:** Read traffic re-routed to EU-Central replica (lower lag). EU-West replica lag resolved after batch migration completed.

**Lessons Learned:** Replica lag must be monitored with read-traffic routing. Maximum acceptable read lag policy defined: 30 seconds.

---

## INC-20250408-0044
**Date:** 2025-04-08 | **Priority:** P1 | **Status:** Resolved
**Service:** Payment Processing | **Duration:** 33m
**Affected Users:** ~1,800 active checkout sessions
**Business Impact:** ~£14,000 lost revenue
**Reported By:** Automated monitoring (error rate 98%)
**Resolver Group:** Payments Engineering + Vendor (Stripe)

**Description:** All payment processing failing. Stripe dashboard showing SDC as suspended.

**Root Cause:** SDC Stripe account was temporarily suspended by Stripe fraud detection due to an unusual spike in cross-border transactions (legitimate — new enterprise customer onboarded). Stripe support resolved after verification.

**Resolution:** Stripe support contacted via emergency line. Account unsuspended after identity verification. Payments resumed.

**Lessons Learned:** Large customer onboarding with unusual transaction patterns must be pre-notified to payment processor. Added payment processor notification to enterprise onboarding checklist.

---

## INC-20250418-0045
**Date:** 2025-04-18 | **Priority:** P3 | **Status:** Resolved
**Service:** Backup & Recovery (Automated Backups) | **Duration:** 6h
**Affected Users:** Operations team
**Reported By:** On-call engineer (routine backup check)
**Resolver Group:** Platform Engineering + DBA

**Description:** Automated database backups had been silently failing for 11 days. Discovery during routine backup verification audit.

**Root Cause:** Backup service AWS IAM role permission for S3 PutObject was removed during a security policy tightening exercise. Backup job returned exit code 0 but wrote to a temporary local path instead of S3 (fallback behaviour not documented).

**Resolution:** IAM role permissions restored. 11 days of missed backups recreated. Backup monitoring now validates S3 object count, not just job exit code.

**Lessons Learned:** Backup success must be validated by checking the backup target, not just job exit code. Backup job now sends test restore verification weekly.

---

## INC-20250423-0046
**Date:** 2025-04-23 | **Priority:** P2 | **Status:** Resolved
**Service:** Customer API (v2) | **Duration:** 1h 45m
**Affected Users:** 15 enterprise customers using API v2
**Reported By:** Customer (Enterprise)
**Resolver Group:** Platform Engineering

**Description:** API v2 responses missing pagination metadata fields. Customers' API clients breaking on response parsing.

**Root Cause:** API v2 response serializer updated to align with v3 format (CHG-20250421-0018). Field names changed from `total_count` and `page_size` to `meta.total` and `meta.per_page`. Change was not flagged as breaking.

**Resolution:** Serializer rolled back to v2 format. Versioned API contract documentation updated. Breaking change process reinforced.

**Lessons Learned:** API versioning must guarantee backward compatibility within a version. Any field rename is a breaking change and requires a major version bump or deprecation period.
