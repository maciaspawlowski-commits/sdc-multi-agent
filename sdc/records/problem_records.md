# SDC Historical Problem Records

---

## PRB-20240103-0001
**Created:** 2024-01-03 | **Status:** Resolved | **Closed:** 2024-01-15
**Priority:** Critical | **Problem Manager:** James Whitmore
**Linked Incidents:** INC-20240103-0001
**Category:** Application
**Affected Services:** Payment Gateway

**Problem Statement:** Payment gateway periodically exhausting database connection pool, causing complete checkout outages.

**Root Cause Confirmed:** Connection leak in payment-gateway v2.3.0. Exception handler on payment failure path did not close database connections. Connections accumulated until pool (max 50) exhausted. Reproducible in load test environment.

**RCA Method:** 5-Whys
1. Why did API fail? → Connection pool exhausted
2. Why pool exhausted? → Connections not closed on exception paths in v2.3.0
3. Why not caught in testing? → No connection pool metric in staging monitoring
4. Why no staging monitoring parity? → Monitoring setup process does not require staging parity
5. Why no parity requirement? → Deployment checklist does not include monitoring parity step

**Workaround (KEDB KE-0001):** Increase connection pool limit to 150 as temporary mitigation. Applied via ConfigMap change without deployment.

**Permanent Fix:** Code fix in v2.3.2: connections closed in finally block on all exception paths. Deployed CHG-20240110-0001.

**Fix Verified:** 30-day monitoring (2024-01-10 to 2024-02-10). No recurrence. Zero connection pool exhaustion events.

**Lessons Learned:** Monitoring parity requirement added to deployment checklist. Staging connection pool monitoring implemented.

---

## PRB-20240108-0002
**Created:** 2024-01-08 | **Status:** Resolved | **Closed:** 2024-02-10
**Priority:** High | **Problem Manager:** David Kim
**Linked Incidents:** INC-20240108-0002
**Category:** Vendor / Infrastructure
**Affected Services:** Customer Portal (SSO)

**Problem Statement:** Azure AD certificate auto-rotation causes SDC SSO federation to fail annually with no automated detection.

**Root Cause Confirmed:** Azure AD automatically rotates tenant token signing certificates annually. SDC IdP metadata references the certificate thumbprint. When Azure rotates the certificate, SDC's IdP becomes out of sync. No monitoring for certificate mismatch between Azure AD and SDC IdP.

**Workaround:** Manual update of IdP metadata after detecting federation failure.

**Permanent Fix:** Implemented automated certificate metadata sync from Azure AD federation metadata endpoint. Daily sync job checks certificate validity. Alert fires if certificate mismatch detected >24 hours before expiry.

**KEDB Entry:** KE-0002 (Resolved 2024-02-10)

**Fix Verified:** Tested with certificate rotation simulation. Auto-sync correctly detected and applied new certificate without service interruption.

---

## PRB-20240210-0003
**Created:** 2024-02-10 | **Status:** Resolved | **Closed:** 2024-03-20
**Priority:** Critical | **Problem Manager:** Anna Patel
**Linked Incidents:** INC-20240210-0007
**Category:** Infrastructure
**Affected Services:** All services (Database Primary)

**Problem Statement:** PostgreSQL primary node susceptible to disk I/O saturation causing node failure. Automatic failover functional but replica lag creates data consistency risk.

**Root Cause Confirmed (composite):**
1. autovacuum configured with aggressive settings for small database — inappropriate for current scale
2. No I/O saturation monitoring on database nodes
3. Replica lag was not monitored, making failover risk assessment blind

**RCA Method:** Fishbone (Ishikawa)
- **Technology:** autovacuum settings not tuned for scale; I/O saturation not monitored
- **Process:** No capacity review cadence for database; no replica lag SLO
- **Data:** Database size grew 4x in 2023 without autovacuum review

**Workaround:** None required after failover. Replica promoted successfully.

**Permanent Fix (multi-part):**
1. autovacuum settings tuned: cost_delay, cost_limit, nap_time reconfigured for current DB scale
2. Disk I/O saturation alert added to Dash0 (>85% I/O wait)
3. Replica lag monitoring added: alert if lag >60 seconds during normal operations

**KEDB Entry:** KE-0003 (Resolved 2024-03-20)

**Fix Verified:** 30-day monitoring. No disk I/O saturation events. Replica lag alert tested — fires correctly. autovacuum completing within scheduled windows.

---

## PRB-20240215-0004
**Created:** 2024-02-15 | **Status:** Resolved | **Closed:** 2024-03-01
**Priority:** Medium | **Problem Manager:** Tom Bradley
**Linked Incidents:** INC-20240218-0008
**Category:** Process
**Affected Services:** File Upload Service (via nginx ingress)

**Problem Statement:** Configuration changes to nginx ingress are not tested with file upload scenarios, resulting in regression to default body size limits.

**Root Cause Confirmed:** nginx configuration change process does not include a test case for file upload beyond the default 10MB limit. Change CHG-20240215-0005 reset client_max_body_size inadvertently and this was not caught before production deployment.

**RCA Method:** Change Analysis
- Change deployed: ingress configuration update
- Failure: client_max_body_size reset to nginx default
- Root cause: no upload size test in post-change verification checklist
- Contributing factor: nginx configuration stored as flat file, not as IaC with explicit default override documentation

**Permanent Fix:**
1. Upload size test (50MB file) added to post-change verification checklist for all ingress changes
2. nginx configuration migrated to Helm values with explicit client_max_body_size (not relying on default)

**Fix Verified:** Tested with deliberate ingress change — upload size test correctly detected missing parameter.

---

## PRB-20240405-0005
**Created:** 2024-04-05 | **Status:** Resolved | **Closed:** 2024-05-10
**Priority:** High | **Problem Manager:** Operations Lead
**Linked Incidents:** INC-20240405-0013
**Category:** Process
**Affected Services:** Billing & Invoicing

**Problem Statement:** IAM/S3 security hardening changes can break service account access without detection until the affected service runs.

**Root Cause Confirmed:** IAM policy changes are applied in bulk without integration testing. Service account permissions removed during security hardening were not included in the change impact assessment. The invoice job runs once monthly — the error was not discovered until the next scheduled run.

**RCA Method:** 5-Whys
1. Why did invoice job fail? → Service account lost S3 read permission
2. Why? → S3 bucket policy hardening removed the permission
3. Why wasn't it caught? → IAM change testing did not include integration tests for each affected service
4. Why no integration tests? → IAM changes were assumed to only affect access (not break existing services)
5. Why that assumption? → Change management process did not classify IAM changes as "service impact" changes

**Permanent Fix:**
1. IAM changes must include integration test run against affected services
2. Service account permission matrix added to CMDB — all changes checked against matrix
3. Monthly billing job moved to test environment where it can be triggered on demand for validation

---

## PRB-20240412-0006
**Created:** 2024-04-12 | **Status:** Resolved | **Closed:** 2024-05-15
**Priority:** Medium | **Problem Manager:** Data Engineering Lead
**Linked Incidents:** INC-20240412-0014
**Category:** Infrastructure / Application
**Affected Services:** Search Service (Elasticsearch)

**Problem Statement:** Kafka consumer groups for search indexing susceptible to rebalance loops, causing silent index staleness.

**Root Cause Confirmed:** Kafka consumer max.poll.interval.ms was set to 30 seconds. Processing-heavy Elasticsearch index write operations could take >30 seconds, causing consumer to be removed from the group (timeout). New consumer takes over but also times out. Results in perpetual rebalance loop with no offset commits.

**Workaround:** Increase max.poll.interval.ms and restart consumer group.

**Permanent Fix:**
1. max.poll.interval.ms increased to 300 seconds for index sync consumers
2. Consumer lag monitoring alert added at 100k messages
3. Consumer group health check added to Dash0 monitoring (offset commit rate)

**Fix Verified:** Load test with simulated large index writes. Consumer group stable. No rebalance loops.

---

## PRB-20240502-0007
**Created:** 2024-05-02 | **Status:** Resolved | **Closed:** 2024-06-02
**Priority:** Critical | **Problem Manager:** Network Engineering Lead
**Linked Incidents:** INC-20240502-0016
**Category:** Infrastructure / Vendor
**Affected Services:** All (BGP routing)

**Problem Statement:** BGP failover to secondary ISP path takes too long (5 minutes) to protect against primary ISP outages.

**Root Cause Confirmed:** BGP failover detection threshold configured at 5 minutes (300 seconds hold-down timer). During the incident, 18 minutes elapsed before traffic routed to secondary ISP. Threshold was set conservatively to avoid false failovers but was too slow for service continuity.

**RCA Method:** Timeline Analysis
- ISP BGP withdrawal: 00s
- Detection by SDC router: 5s
- Hold-down timer starts: 5s
- Traffic failover: 305s (5 minutes 5 seconds)
- Service restored: 305s

**Permanent Fix:** BGP hold-down timer reduced from 300s to 90s. BFD (Bidirectional Forwarding Detection) enabled on both ISP links for sub-second failure detection. ISP maintenance window communication protocol established (ISP must notify SDC NOC 24h before).

**Fix Verified:** BGP failover test conducted (primary ISP link deliberately failed). Failover completed in 92 seconds (within SLO).

---

## PRB-20240710-0008
**Created:** 2024-07-10 | **Status:** Resolved | **Closed:** 2024-08-10
**Priority:** High | **Problem Manager:** Data Engineering Lead
**Linked Incidents:** INC-20240710-0023
**Category:** Application / Process
**Affected Services:** Real-time Data Pipeline

**Problem Statement:** Bulk data imports can overwhelm Kafka consumer pipeline, causing multi-hour processing delays affecting all real-time downstream services.

**Root Cause Confirmed:** No rate limiting on bulk data import ingestion path. A single customer importing 8 years of historical data created a 2.4M event burst that exceeded consumer group processing capacity (6 pods). Consumer lag grew to 2.4M messages with 88-minute clearance time.

**Workaround:** Scale consumer group from 6 to 24 pods temporarily.

**Permanent Fix:**
1. Rate limiting added to bulk import API: maximum 10,000 events per minute per account
2. Consumer lag alert threshold set at 100k messages
3. HPA for Kafka consumer group (auto-scales 6–24 pods based on consumer lag metric)
4. Bulk import status page added so customers can see import progress

**Fix Verified:** Load test with 3M event burst. Rate limiting correctly throttled import. Consumer lag never exceeded 50k messages. HPA scaled pods appropriately.

---

## PRB-20240718-0009
**Created:** 2024-07-18 | **Status:** Resolved | **Closed:** 2024-08-01
**Priority:** High | **Problem Manager:** Infrastructure Lead
**Linked Incidents:** INC-20240718-0024
**Category:** Infrastructure
**Affected Services:** Multi-factor Authentication

**Problem Statement:** NTP synchronisation failure on MFA service host causes TOTP verification failure with no user-visible error.

**Root Cause Confirmed:** MFA service host NTP client (chronyd) failed silently after a network configuration change removed access to the NTP server IP. Clock drifted 4 minutes over 6 hours. TOTP requires clock within ±30 seconds. No monitoring for clock drift.

**Permanent Fix:**
1. Clock drift alert added to Dash0: alert if drift exceeds ±10 seconds
2. NTP configuration validated as part of server provisioning checklist
3. Multiple NTP sources configured (3 upstream servers) for resilience

**Fix Verified:** NTP source disconnection test: drift alert fired within 3 minutes of NTP failure. Resolution confirmed within 30 seconds of NTP restoration.

---

## PRB-20240901-0010
**Created:** 2024-09-01 | **Status:** Resolved | **Closed:** 2024-09-30
**Priority:** Critical | **Problem Manager:** DBA Team Lead
**Linked Incidents:** INC-20240905-0028
**Category:** Infrastructure
**Affected Services:** Core Database

**Problem Statement:** WAL archiving failure silently fills database disk, causing complete write outage.

**Root Cause Confirmed:** PostgreSQL WAL archiving to S3 failed silently when S3 target became unavailable. PostgreSQL continued writing WAL locally. Disk usage alert threshold was 95% — insufficient warning time. Disk filled to 100% causing all writes to fail.

**RCA Method:** Fault Tree Analysis
- Top event: Database write failure
  - AND: Disk full (required)
    - AND: WAL accumulation (required)
      - OR: Archiving failed + WAL not purged
    - AND: No timely alert (required)
      - OR: Alert threshold too high (95%)

**Permanent Fix:**
1. WAL archive failure alert added: fires within 5 minutes of archiving failure
2. Disk usage alert thresholds: 70% warning, 85% critical (down from 95%)
3. WAL retention policy: local WAL purged after confirmed archive (pg_archivecleanup)
4. S3 archiving target health check added to monitoring

**Fix Verified:** 30-day monitoring. WAL archiving failure test: alert fired in 3 minutes. Disk usage alerts operating at correct thresholds.

---

## PRB-20241001-0011
**Created:** 2024-10-01 | **Status:** Resolved | **Closed:** 2024-11-01
**Priority:** High | **Problem Manager:** Mobile Engineering Lead
**Linked Incidents:** INC-20240925-0030
**Category:** Vendor / Process
**Affected Services:** Push Notification Service (Android)

**Problem Statement:** External API deprecations not tracked, causing service outages when deprecated APIs are shut down.

**Root Cause Confirmed:** FCM legacy API deprecation was announced by Google 12 months before shutdown. The migration task existed in the backlog but was not prioritised. When the API was shut down, Android push notifications stopped immediately.

**RCA Method:** 5-Whys
1. Why Android push broken? → FCM legacy API shut down
2. Why not migrated? → Migration task deprioritised in sprint planning
3. Why deprioritised? → No escalation mechanism for upcoming deprecations
4. Why no escalation? → No formal process for tracking external API lifecycle
5. Why no process? → API vendor management was informal and undocumented

**Permanent Fix:**
1. External API deprecation register created in Confluence
2. All external API dependencies catalogued with version and deprecation date
3. Alert policy: 180-day notice creates backlog item; 90-day triggers escalation to SDM; 30-day triggers mandatory action
4. Quarterly vendor API review added to operations calendar

**Fix Verified:** Register populated with 47 external API dependencies. Three upcoming deprecations identified and migration work planned.

---

## PRB-20241010-0012
**Created:** 2024-10-10 | **Status:** Resolved | **Closed:** 2024-11-10
**Priority:** Medium | **Problem Manager:** Data Engineering Lead
**Linked Incidents:** INC-20241010-0031
**Category:** Application
**Affected Services:** SLA Reporting Dashboard

**Problem Statement:** Database schema migrations can silently break dependent queries and dashboards.

**Root Cause Confirmed:** Column rename in schema migration v3.0.1 (total_incidents → total_count) was not propagated to the SLA metrics aggregation query. Division by null caused all SLA metrics to show 0%.

**Permanent Fix:**
1. Schema migration process now requires: grep of all codebase for affected column names
2. Dashboard smoke tests added to post-migration validation
3. Migrations must include "dependent query validation" section in RFC
4. Database column rename treated as breaking change requiring version bump

---

## PRB-20241020-0013
**Created:** 2024-10-20 | **Status:** Resolved | **Closed:** 2024-11-20
**Priority:** Critical | **Problem Manager:** Platform Engineering Lead
**Linked Incidents:** INC-20241020-0032
**Category:** Infrastructure / Process
**Affected Services:** All (Kubernetes Cluster)

**Problem Statement:** Spot instances in production cluster create unacceptable risk of mass simultaneous eviction.

**Root Cause Confirmed:** 4 of 6 Kubernetes worker nodes were AWS spot instances in the same availability zone and instance family. When AWS reclaimed spot capacity, all 4 were evicted simultaneously. No PodDisruptionBudgets enforced. Critical services had single-pod deployments.

**RCA Method:** Fault Tree Analysis
- Top event: 60% capacity loss
  - AND: 4 nodes evicted simultaneously
    - AND: All 4 nodes were spot instances
    - AND: No PDB to protect running pods
  - AND: Services without replicas became unavailable
    - OR: Single-pod deployments in production

**Permanent Fix:**
1. Spot instances prohibited for production-critical workloads (policy enforced via OPA/Gatekeeper)
2. PodDisruptionBudgets (minimum 50% availability) applied to all 34 production deployments
3. Production nodes: minimum 6 on-demand nodes across 3 AZs
4. Single-pod deployments in production prohibited via admission controller

**Fix Verified:** Spot instance eviction test (3 nodes simultaneously evicted). Services maintained 100% availability. PDBs correctly prevented simultaneous pod termination.

---

## PRB-20241101-0014
**Created:** 2024-11-01 | **Status:** Resolved | **Closed:** 2024-12-01
**Priority:** High | **Problem Manager:** Security Team Lead
**Linked Incidents:** INC-20241118-0034
**Category:** Process / Security
**Affected Services:** External API (OAuth2)

**Problem Statement:** Cryptographic key rotation procedure does not include distribution verification, causing partial rollouts that break services.

**Root Cause Confirmed:** OAuth2 JWT signing key rotation procedure documented only key generation and activation steps. Distribution to token validation nodes was assumed but not verified. Three of eight validation nodes were still using the old key when the new signing key was activated.

**Permanent Fix:**
1. Key rotation runbook updated: distribution verification step added (check all nodes hold new key before activation)
2. Key distribution monitored via Dash0 metric: nodes_serving_old_key_count (alert if >0 after rotation)
3. Canary test added: issue one test token with new key, validate against all nodes before full activation

**Fix Verified:** Key rotation drill conducted. Distribution verification step caught one node that failed to receive new key. Activation held until all nodes confirmed. Zero service disruption.

---

## PRB-20241201-0015
**Created:** 2024-12-01 | **Status:** Resolved | **Closed:** 2025-01-05
**Priority:** High | **Problem Manager:** Platform Engineering Lead
**Linked Incidents:** INC-20241205-0035 (survey), INC-20240810-0026 (API timeout)
**Category:** Process
**Affected Services:** Multiple

**Problem Statement:** Environment-specific configuration is being promoted to production incorrectly, causing service misbehaviour.

**Root Cause Confirmed (pattern across multiple incidents):** Configuration values (URLs, timeouts, connection limits) that differ between environments are stored in the same configuration files as application code. Staging deployments override production values. Promotion pipelines do not validate environment-specific config is correctly set.

**RCA Method:** Fishbone
- **Process:** No config validation in promotion pipeline; staging config changes can bleed to production
- **Technology:** Environment config mixed with application config (violates 12-factor app)
- **People:** Engineers assume staging-to-production promotion is safe for config

**Permanent Fix:**
1. Environment-specific config separated from application config across all services (12-factor compliance)
2. Config promotion gate added to CI/CD: environment config diff check before production deployment
3. Helm values files per environment — production values locked in separate repo with restricted access
4. Config validation tests added: each service has a smoke test that verifies critical config values on startup

---

## PRB-20250108-0016
**Created:** 2025-01-08 | **Status:** Resolved | **Closed:** 2025-02-10
**Priority:** Critical | **Problem Manager:** Platform Engineering Lead
**Linked Incidents:** INC-20250108-0037
**Category:** Infrastructure
**Affected Services:** All (etcd cluster failure)

**Problem Statement:** etcd cluster nodes sharing same hardware generation creates single point of failure for entire Kubernetes cluster.

**Root Cause Confirmed:** All 3 etcd nodes were on servers with the same SSD hardware generation, affected by the same firmware bug (data corruption under high write load). Two nodes corrupted simultaneously, causing quorum loss.

**RCA Method:** Fault Tree Analysis
- Top event: etcd quorum loss
  - AND: 2+ nodes fail simultaneously
    - AND: Same firmware bug on all nodes
    - AND: Same SSD hardware generation across all etcd nodes
  - AND: Recovery requires backup restore (data loss)
    - AND: Backup frequency was 60 minutes (too long)

**Permanent Fix:**
1. etcd node anti-affinity enforced: no two etcd nodes on same hardware generation
2. etcd backup frequency increased from 60 minutes to 15 minutes
3. etcd node firmware audit procedure added to quarterly infrastructure review
4. etcd restore drill added to quarterly DR testing calendar

**Fix Verified:** etcd restore drill completed in 18 minutes (target: 30 minutes). Data loss window: 12 minutes (within 15-minute RPO).

---

## PRB-20250201-0017
**Created:** 2025-02-01 | **Status:** Resolved | **Closed:** 2025-03-01
**Priority:** Medium | **Problem Manager:** DBA Team Lead
**Linked Incidents:** INC-20250108-0037 (secondary: data loss), INC-20240905-0028 (backup failure)
**Category:** Process
**Affected Services:** All (backup strategy)

**Problem Statement:** Backup validation relies on job exit code rather than target verification, allowing silent backup failures to persist for extended periods.

**Root Cause Confirmed:** Two separate incidents (September 2024, January 2025) involved backup jobs appearing to succeed (exit code 0) while not actually writing to the backup target. In both cases, the failure was not discovered until a restore was needed.

**Permanent Fix:**
1. Backup validation now checks backup target: S3 object count, object age, and minimum size
2. Weekly automated test restore to isolated environment
3. Backup health dashboard added to Dash0 with: last successful backup age, backup size trend, restore test result
4. Backup success defined as: job exit 0 AND target object created AND object size >minimum threshold

**Fix Verified:** Intentional backup target misconfiguration test: alert fired within 25 minutes of next scheduled backup run.

---

## PRB-20250301-0018
**Created:** 2025-03-01 | **Status:** Resolved | **Closed:** 2025-04-01
**Priority:** High | **Problem Manager:** Platform Engineering Lead
**Linked Incidents:** INC-20250301-0041
**Category:** Infrastructure / Capacity
**Affected Services:** Core API Platform

**Problem Statement:** nginx worker connection limits not tracked as capacity metric, creating risk of connection exhaustion under burst traffic.

**Root Cause Confirmed:** nginx worker_connections was set at system default without consideration for expected peak concurrent TLS connections. When a customer burst-created connections without connection pooling, the limit was hit and nginx dropped new connections.

**Permanent Fix:**
1. nginx worker_connections limit based on calculated peak (connections = worker_processes × worker_connections per process)
2. nginx connection count added to Dash0 capacity dashboard with 80%/90% threshold alerts
3. Customer API usage policy updated: connection pooling required for enterprise accounts
4. Per-customer connection rate limiting added at load balancer

**Fix Verified:** Load test at 5x normal peak connection rate. Capacity alert fired at 80% threshold. Rate limiting correctly throttled clients without pooling.

---

## PRB-20250315-0019
**Created:** 2025-03-15 | **Status:** Known Error | **KEDB:** KE-0019
**Priority:** Medium | **Problem Manager:** Platform Engineering Lead
**Linked Incidents:** INC-20250315-0042, INC-20241010-0031
**Category:** Infrastructure
**Affected Services:** Log Aggregation / Elasticsearch

**Problem Statement (recurring):** Elasticsearch index template changes silently reduce shard count for new indices, causing indexing throughput to fall below ingest rate.

**Root Cause Confirmed:** Index templates are modified via Kibana/Elasticsearch API with no change management gate. Template changes apply to next index created (daily rotation), not existing indices. The reduced shard count limits write parallelism.

**Workaround:** Recreate current day's index with correct shard count. Restart ingest pipeline.

**Permanent Fix (in progress):** RFC CHG-20250401-0036 raised. Plan: Elasticsearch IaC (Terraform provider), all index template changes go through change management. ETA: 2025-05-30.

**KEDB Status:** Active. Next review: 2025-05-15.

---

## PRB-20250401-0020
**Created:** 2025-04-01 | **Status:** Investigation | **Problem Manager:** API Platform Lead
**Linked Incidents:** INC-20250423-0046 (API v2 serializer), INC-20240308-0010 (rate limit config)
**Category:** Process
**Affected Services:** Customer API

**Problem Statement (recurring pattern):** Changes to shared API infrastructure components break backward compatibility for existing API consumers without being classified as breaking changes.

**Root Cause (suspected):** API change impact assessment does not include a step to verify backward compatibility with all current API versions. Engineers incorrectly classify field renames and response format changes as non-breaking.

**RCA Status:** Investigation in progress. Fishbone analysis scheduled for 2025-04-10.

**Initial Findings:**
- API contract tests existed but did not cover all response fields
- Breaking change definition was not formally documented
- CAB review did not flag field renames as breaking

**Next Steps:**
1. Complete Fishbone analysis
2. Propose API contract test expansion
3. Define formal breaking change criteria in RFC template

---

## PRB-20250410-0021
**Created:** 2025-04-10 | **Status:** Known Error | **KEDB:** KE-0021
**Priority:** Medium | **Problem Manager:** DBA Team Lead
**Linked Incidents:** INC-20250325-0043 (EU-West lag), INC-20240308-0010 (Redis config loss)
**Category:** Infrastructure / Process
**Affected Services:** Database Read Replicas (Multi-region)

**Problem Statement:** Database read replicas can fall significantly behind primary during batch operations, serving stale data to users without detection.

**Root Cause Confirmed:** Read traffic routing does not consider replica lag. During heavy batch operations (migrations, large imports), replica lag can grow to 20+ minutes. Application continues reading from degraded replica.

**Workaround:** Manually monitor replica lag (pg_stat_replication). If lag >30 seconds, route reads to alternative replica via ProxySQL manual override.

**Permanent Fix (deployed):** Lag-based routing implemented in CHG-20250325-0031. Maximum lag threshold: 30 seconds. Monitoring confirms routing works correctly.

**KEDB Status:** Resolved 2025-04-05 (fix deployed before problem record opened). Closed.
