# SDC Historical Change Records

---

## CHG-20240110-0001
**Date:** 2024-01-10 | **Type:** Normal Major | **Status:** Completed
**Service:** Payment Gateway | **RFC Owner:** James Whitmore (Payments Lead)
**CAB Approval:** 2024-01-08 Thursday CAB | **Implementation Window:** Saturday 02:00–05:00 UTC
**Risk Rating:** High | **CMDB CIs Updated:** payment-gateway-app v2.3.1, db-connection-pool config

**Description:** Deploy payment gateway v2.3.1 to fix connection pool exhaustion (see INC-20240103-0001). Increase DB connection pool limit from 50 to 150. Apply hotfix for connection leak on exception paths.

**Implementation Steps:**
1. Take snapshot of payment-gateway nodes (02:00 UTC)
2. Deploy v2.3.1 via Helm: `helm upgrade payment-gateway ./charts/payment-gateway --set image.tag=2.3.1`
3. Update connection pool configuration in ConfigMap
4. Rolling restart of payment-gateway pods
5. Smoke test: 50 test transactions via staging payment flow
6. Monitor error rate and connection pool metrics for 30 minutes

**Outcome:** Successful. Deployed at 02:14 UTC. Smoke tests passed at 02:45 UTC. Connection pool stable at 45/150 under normal load.

**PIR:** Completed 2024-01-15. Monitoring parity checklist updated. Lessons learned fed into staging environment standards.

**Deviations:** None.

---

## CHG-20240115-0002
**Date:** 2024-01-15 | **Type:** Standard (SC-002) | **Status:** Completed
**Service:** Customer Portal | **RFC Owner:** Sarah Chen (Security Team)
**Approver:** Security Team Lead (pre-approved)

**Description:** Renew TLS certificate for portal.sdc.com. Certificate expiring 2024-01-28. Renewed via Let's Encrypt automated renewal.

**Outcome:** Successful. Certificate renewed without service interruption. New expiry: 2025-01-15. SSL Labs scan: A+ rating confirmed.

**Deviations:** None.

---

## CHG-20240122-0003
**Date:** 2024-01-22 | **Type:** Normal Minor | **Status:** Completed
**Service:** Authentication Service | **RFC Owner:** David Kim (IAM Team)
**CAB Approval:** 2024-01-16 Tuesday CAB

**Description:** Increase JWT token TTL from 1 hour to 4 hours for improved user experience. Refresh token TTL unchanged (30 days).

**Outcome:** Successful. Token TTL updated in auth config. No adverse effects observed in 48-hour monitoring window. Session abandonment rate decreased 12%.

**PIR:** Completed 2024-01-29. No issues. Change noted as successful improvement.

---

## CHG-20240205-0004
**Date:** 2024-02-05 | **Type:** Normal Major | **Status:** Rolled Back
**Service:** Database Cluster | **RFC Owner:** Anna Patel (DBA Team)
**CAB Approval:** 2024-02-01 Thursday CAB | **Implementation Window:** Sunday 01:00–05:00 UTC
**Risk Rating:** High

**Description:** PostgreSQL version upgrade from 14.8 to 15.4. Includes new query planner improvements. Full pg_upgrade with logical replication cutover.

**Implementation Steps:**
1. Logical replication setup from v14 to v15 instance
2. Monitor replication lag until <1s
3. Stop writes, allow replica to catch up
4. Promote v15 instance to primary
5. Update connection strings in all application configs

**Outcome:** Rolled back. During step 5, discovered 3 stored procedures used deprecated PL/pgSQL syntax removed in v15. Application errors detected in smoke tests. Rollback completed within 45 minutes. v14 instance retained as primary.

**PIR:** Completed 2024-02-12. Stored procedure compatibility check added to upgrade runbook. Rescheduled for 2024-04-14 after code remediation.

**Deviations:** Rollback executed. Stakeholders notified at 03:30 UTC.

---

## CHG-20240215-0005
**Date:** 2024-02-15 | **Type:** Normal Minor | **Status:** Completed
**Service:** API Gateway (nginx ingress) | **RFC Owner:** Tom Bradley (Platform Team)
**CAB Approval:** 2024-02-13 Tuesday CAB

**Description:** Update nginx ingress configuration: increase worker connections, add gzip compression for API responses >1KB, update rate limiting rules for unauthenticated endpoints.

**Outcome:** Partially successful. gzip and rate limiting applied correctly. However, client_max_body_size was inadvertently reset to nginx default (10MB) — linked to INC-20240218-0008. Hotfix CHG-20240218-0006 raised.

**PIR:** Completed 2024-02-22. Upload size testing added to ingress change verification checklist.

---

## CHG-20240218-0006
**Date:** 2024-02-18 | **Type:** Emergency | **Status:** Completed
**Service:** API Gateway | **RFC Owner:** Tom Bradley (Platform Team)
**ECAB Approval:** SDM + Technical Lead | **Triggered By:** INC-20240218-0008

**Description:** Emergency fix: restore nginx client_max_body_size to 100MB. Regression introduced in CHG-20240215-0005.

**Outcome:** Successful. Deployed in 15 minutes. File uploads restored. INC-20240218-0008 resolved.

**Post-Emergency Documentation:** RFC completed within 24 hours. PIR combined with CHG-20240215-0005 PIR.

---

## CHG-20240301-0007
**Date:** 2024-03-01 | **Type:** Normal Major | **Status:** Completed
**Service:** Core API Platform | **RFC Owner:** Rachel Torres (Platform Lead)
**CAB Approval:** 2024-02-26 Thursday CAB | **Implementation Window:** Sunday 02:00–06:00 UTC
**Risk Rating:** High

**Description:** Redis cluster upgrade from v6.2 to v7.2. Includes new memory management improvements and AOF log rotation policies. Three-node cluster rolling upgrade.

**Implementation Steps:**
1. Upgrade replica nodes one at a time (zero downtime rolling)
2. Promote one upgraded replica to primary
3. Upgrade original primary as new replica
4. Apply new maxmemory-policy and AOF rotation configuration
5. Validate cluster health: `redis-cli cluster info`

**Outcome:** Successful. All three nodes upgraded without service interruption. AOF rotation policy applied (AOF rotated at 64MB, retained 7 days). Memory usage stable.

**PIR:** Completed 2024-03-08. Disk usage monitoring added for Redis data directory. Lessons applied to Redis monitoring runbook.

---

## CHG-20240315-0008
**Date:** 2024-03-15 | **Type:** Normal Minor | **Status:** Completed
**Service:** Monitoring (Dash0) | **RFC Owner:** Operations Team
**CAB Approval:** 2024-03-12 Tuesday CAB

**Description:** Add new Dash0 alert rules: disk usage >75% and >85% (warning/critical), Redis disk usage alert, replica lag alert for primary database. Implement following post-incident reviews from January/February.

**Outcome:** Successful. 6 new alert rules deployed. Test fires confirmed correct routing. No false positives in 7-day observation period.

---

## CHG-20240402-0009
**Date:** 2024-04-02 | **Type:** Normal Major | **Status:** Completed
**Service:** S3 Bucket Access Policies | **RFC Owner:** Security Team
**CAB Approval:** 2024-03-28 Thursday CAB

**Description:** Security hardening: restrict S3 bucket policies to least-privilege access per service account. Apply AWS IAM policy boundaries. Review and tighten 28 S3 bucket policies.

**Outcome:** Partially successful. Most bucket policies correctly applied. Invoice service S3 bucket policy was over-restricted, removing the service account's read permission — linked to INC-20240405-0013. Hotfix applied 2024-04-05.

**PIR:** Completed 2024-04-10. Service account permissions now mandatory checklist item in security hardening changes. Integration tests required post-IAM changes.

---

## CHG-20240414-0010
**Date:** 2024-04-14 | **Type:** Normal Major | **Status:** Completed
**Service:** Database Cluster | **RFC Owner:** Anna Patel (DBA Team)
**CAB Approval:** 2024-04-08 Thursday CAB | **Implementation Window:** Sunday 01:00–06:00 UTC
**Risk Rating:** High

**Description:** PostgreSQL upgrade from 14.8 to 15.4 (rescheduled from CHG-20240205-0004 after stored procedure remediation).

**Pre-Requisites:** All stored procedures validated for PL/pgSQL v15 compatibility. Full regression test suite passed on v15 clone.

**Outcome:** Successful. Upgrade completed by 04:15 UTC. Query planner improvements resulted in 18% reduction in p99 query latency. No application errors. All services validated.

**PIR:** Completed 2024-04-21. Upgrade runbook updated with stored procedure compatibility check step. Successful migration documented as reference implementation.

---

## CHG-20240430-0011
**Date:** 2024-04-30 | **Type:** Normal Major | **Status:** Completed
**Service:** Email Infrastructure | **RFC Owner:** Rachel Torres
**CAB Approval:** 2024-04-25 Thursday CAB | **Implementation Window:** Tuesday 22:00–02:00 UTC
**Risk Rating:** Medium

**Description:** Migrate outbound email infrastructure from on-premise Postfix relay to dedicated cloud provider (AWS SES + primary SendGrid). Update SPF, DKIM, and DMARC DNS records.

**Outcome:** Successful. DNS records updated. Email deliverability validated from 5 external email providers. However, SPF record for new mail IP range was incomplete — linked to INC-20240510-0017. Hotfix SPF update applied 2024-05-10.

**PIR:** Completed 2024-05-08. Email deliverability test added to post-change checklist for all email infrastructure changes.

---

## CHG-20240515-0012
**Date:** 2024-05-15 | **Type:** Normal Major | **Status:** Completed
**Service:** Kubernetes Cluster | **RFC Owner:** Tom Bradley (Platform Lead)
**CAB Approval:** 2024-05-09 Thursday CAB | **Implementation Window:** Saturday 01:00–07:00 UTC
**Risk Rating:** High

**Description:** Kubernetes cluster upgrade from v1.27 to v1.29. Includes control plane upgrade (3 nodes) then worker node rolling upgrade (12 nodes). Full cluster upgrade with zero-downtime target.

**Implementation Steps:**
1. Upgrade control plane nodes one at a time
2. Validate kube-apiserver health between each node
3. Cordon and drain worker nodes in batches of 3
4. Upgrade kubelet and kubeadm on each drained node
5. Uncordon and validate pod scheduling
6. Full smoke test of all services

**Outcome:** Successful. Upgrade completed by 06:10 UTC. All 12 worker nodes upgraded. No service disruption. PodDisruptionBudgets worked correctly. Performance metrics unchanged.

---

## CHG-20240601-0013
**Date:** 2024-06-01 | **Type:** Normal Minor | **Status:** Completed
**Service:** CDN Configuration | **RFC Owner:** Network Team
**CAB Approval:** 2024-05-28 Tuesday CAB

**Description:** Configure CDN multi-PoP failover routing. Add Hong Kong PoP as failover for Singapore PoP. Add Sydney PoP for Australian users. Implement automatic health-check based routing.

**Outcome:** Successful. Three PoPs configured with automatic failover. Failover tested: Singapore PoP disabled, traffic correctly routed to Hong Kong within 45 seconds.

---

## CHG-20240612-0014
**Date:** 2024-06-12 | **Type:** Normal Major | **Status:** Completed (with incident)
**Service:** Database Schema | **RFC Owner:** DBA Team
**CAB Approval:** 2024-06-06 Thursday CAB

**Description:** Schema migration v2.7.0: add new columns to orders table, create reporting views, add indexes for query optimisation.

**Outcome:** Partially successful. Main migration completed. However, payroll reporting view was accidentally dropped during cleanup step — linked to INC-20240614-0020. View recreated same day from version control.

**PIR:** Completed 2024-06-19. Migration scripts must explicitly protect dependent views. Rollback scripts must include view recreation.

---

## CHG-20240705-0015
**Date:** 2024-07-05 | **Type:** Normal Major | **Status:** Completed
**Service:** Application Platform (all services) | **RFC Owner:** Platform Engineering
**CAB Approval:** 2024-07-01 Thursday CAB | **Implementation Window:** Saturday 00:00–06:00 UTC
**Risk Rating:** High

**Description:** Implement PodDisruptionBudgets (PDBs) for all production Kubernetes deployments. Minimum availability: 50% of replicas. Prevents mass eviction during spot instance reclamation.

**Outcome:** Successful. PDBs applied to 34 production deployments. Test eviction confirmed PDBs respected. Spot instance reclamation test passed.

---

## CHG-20240720-0016
**Date:** 2024-07-20 | **Type:** Normal Minor | **Status:** Completed
**Service:** Kafka Configuration | **RFC Owner:** Data Engineering
**CAB Approval:** 2024-07-16 Tuesday CAB

**Description:** Reconfigure Kafka consumer group settings: increase max.poll.interval.ms from 30s to 300s for processing-intensive consumers. Add consumer lag monitoring. Set consumer group alert threshold at 100k messages.

**Outcome:** Successful. Consumer group configuration applied. Lag monitoring alert firing confirmed with test scenario. No spurious rebalances in 7-day observation period.

---

## CHG-20240801-0017
**Date:** 2024-08-01 | **Type:** Normal Major | **Status:** Completed
**Service:** Load Balancer Configuration | **RFC Owner:** Platform Engineering
**CAB Approval:** 2024-07-25 Thursday CAB

**Description:** Increase load balancer timeout for API tier from 60 seconds to 120 seconds. Implement per-route timeout configuration. Add long-request logging (>30s requests logged with trace ID).

**Outcome:** Successful. Timeout configuration applied. 504 errors for large requests eliminated in 7-day monitoring period. No unintended side effects.

---

## CHG-20240820-0018
**Date:** 2024-08-20 | **Type:** Normal Minor | **Status:** Completed
**Service:** Kubernetes Resource Limits | **RFC Owner:** Platform Engineering
**CAB Approval:** 2024-08-13 Tuesday CAB

**Description:** Increase memory limits for webhook worker pods from 256Mi to 512Mi. Increase replica count from 3 to 6. Add OOMKilled alert. Implement horizontal pod autoscaling (HPA) for webhook workers.

**Outcome:** Successful. Memory limit increased. HPA configured (min 6, max 20 replicas based on queue depth). OOMKilled alert tested and confirmed.

---

## CHG-20240905-0019
**Date:** 2024-09-05 | **Type:** Normal Major | **Status:** Completed
**Service:** Database (WAL Archiving & Monitoring) | **RFC Owner:** DBA Team
**CAB Approval:** 2024-08-29 Thursday CAB

**Description:** Implement WAL archiving to S3 for point-in-time recovery. Configure WAL archiving failure alerting. Adjust disk usage alert thresholds from 95% to 70%/85%.

**Outcome:** Successful. WAL archiving to S3 confirmed working. Archive failure alert tested. Disk alerts reconfigured. First PITR test recovery completed successfully.

---

## CHG-20240920-0020
**Date:** 2024-09-20 | **Type:** Normal Major | **Status:** Completed
**Service:** Firebase Cloud Messaging Integration | **RFC Owner:** Mobile Engineering
**CAB Approval:** 2024-09-12 Thursday CAB (scheduled after deprecation notice)

**Description:** Migrate Android push notifications from FCM legacy API to FCM v1 API. Legacy API end-of-life: 2024-09-20. Update server-side integration, credential rotation, response handling.

**Outcome:** Completed as emergency on 2024-09-25 due to migration not completing before deadline (linked to INC-20240925-0030). Subsequent planned deployment converted to emergency change.

**PIR:** Completed 2024-10-02. External API deprecation must be tracked 6 months in advance. Migration backlog prioritisation policy updated.

---

## CHG-20241015-0021
**Date:** 2024-10-15 | **Type:** Normal Major | **Status:** Completed
**Service:** Production Kubernetes Cluster | **RFC Owner:** Platform Engineering
**CAB Approval:** 2024-10-10 Thursday CAB | **Implementation Window:** Saturday 02:00–06:00 UTC

**Description:** Replace 4 spot instance worker nodes with on-demand instances. Convert non-critical workloads (batch jobs, non-production) to use new spot-specific node pool. Enforce spot instance usage limits.

**Outcome:** Successful. All production critical workloads now running on on-demand nodes. Spot nodes reserved for batch and dev workloads. Cost savings: 15% reduction in Kubernetes compute costs.

---

## CHG-20241101-0022
**Date:** 2024-11-01 | **Type:** Standard (SC-001) | **Status:** Completed
**Service:** All Linux Servers | **RFC Owner:** Patch Manager
**Implementation Window:** Saturday 02:00–06:00 UTC

**Description:** Monthly OS security patching. October 2024 approved patch list: kernel 5.15.0-122, OpenSSL 3.0.14, curl 8.9.1.

**Outcome:** Successful. 48 nodes patched. All services healthy post-reboot. 2 nodes required additional monitoring (slow disk I/O during reboot — cleared automatically).

---

## CHG-20241115-0023
**Date:** 2024-11-15 | **Type:** Normal Major | **Status:** Completed (with incident)
**Service:** OAuth2 / JWT Signing Infrastructure | **RFC Owner:** Security Team
**CAB Approval:** 2024-11-07 Thursday CAB

**Description:** Security hardening: rotate OAuth2 JWT signing private key. Update key distribution to all token validation nodes. Update API documentation with key rotation schedule.

**Outcome:** Partially successful. Key rotated successfully but distribution to all validation nodes was incomplete — linked to INC-20241118-0034. Distribution procedure updated; full rollout completed 2024-11-18.

**PIR:** Completed 2024-11-25. Key rotation procedure updated to include validation node distribution check before signing key activation.

---

## CHG-20241201-0024
**Date:** 2024-12-01 | **Type:** Normal Major | **Status:** Completed
**Service:** Backup Infrastructure | **RFC Owner:** Platform Engineering
**CAB Approval:** 2024-11-25 Thursday CAB

**Description:** Implement backup validation monitoring: S3 object count check after backup, weekly test restore to isolated environment, backup age alert if latest backup >25 hours old.

**Outcome:** Successful. Backup validation monitoring deployed. First test restore completed successfully in 34 minutes. Backup age alert confirmed working.

---

## CHG-20241215-0025
**Date:** 2024-12-15 | **Type:** Emergency | **Status:** Completed
**Service:** Payment Gateway (3DS) | **RFC Owner:** Payments Engineering
**ECAB Approval:** SDM + Payments Lead + Security Lead | **Triggered By:** INC-20241215-0036

**Description:** Emergency update: payment integration to support Visa 3DS2 protocol v2.2. Update payment library from v3.8.1 to v3.9.0.

**Outcome:** Successful. Deployed in 28 minutes. 3DS authentication for Visa cards restored. Checkout error rate returned to normal.

---

## CHG-20250110-0026
**Date:** 2025-01-10 | **Type:** Normal Major | **Status:** Completed
**Service:** etcd Cluster | **RFC Owner:** Platform Engineering
**CAB Approval:** 2025-01-06 Thursday CAB (emergency convened)

**Description:** Replace 2 failed etcd nodes with new hardware (different hardware generation to avoid SSD firmware issue). Restore etcd cluster to 3-node quorum. Apply anti-affinity rules.

**Outcome:** Successful. Cluster restored to full quorum. Anti-affinity policy enforced. Data loss: 22 minutes (between last backup and failure). RPO breach documented and reported to SDM.

**PIR:** Completed 2025-01-20. etcd backup frequency increased from hourly to every 15 minutes.

---

## CHG-20250120-0027
**Date:** 2025-01-20 | **Type:** Normal Minor | **Status:** Completed
**Service:** Billing Service (Invoice Job) | **RFC Owner:** Finance Tech Team
**CAB Approval:** 2025-01-14 Tuesday CAB

**Description:** Add idempotency key to invoice generation job. Add "job running" status check to manual trigger UI. Add job audit log for all invoice run executions.

**Outcome:** Successful. Idempotency key enforced (duplicate runs rejected with clear error). Manual trigger now shows last run status before allowing new trigger. Audit log operational.

---

## CHG-20250205-0028
**Date:** 2025-02-05 | **Type:** Normal Minor | **Status:** Completed
**Service:** ITSM-Jira Integration | **RFC Owner:** Integration Engineering
**CAB Approval:** 2025-02-04 Tuesday CAB (expedited)

**Description:** Migrate ITSM-Jira webhook integration to use secrets manager for webhook signing key. Implement rotation alert (notify integration owner 30 days before key expiry).

**Outcome:** Successful. Signing key in secrets manager. Rotation notification configured. Test rotation completed successfully in staging.

---

## CHG-20250301-0029
**Date:** 2025-03-01 | **Type:** Normal Major | **Status:** Completed
**Service:** Redis Cluster (Feature Store) | **RFC Owner:** ML Engineering
**CAB Approval:** 2025-02-24 Thursday CAB

**Description:** Increase Feature Store Redis cluster memory from 8GB to 32GB. Configure memory usage alerts at 70%/85%. Implement graceful feature degradation in ML model when features partially missing.

**Outcome:** Successful. Memory increased. Model updated to handle partial feature availability gracefully (returns confidence score with available features). Alerts configured.

---

## CHG-20250315-0030
**Date:** 2025-03-15 | **Type:** Normal Major | **Status:** Completed
**Service:** Elasticsearch Cluster | **RFC Owner:** Platform Engineering
**CAB Approval:** 2025-03-10 Thursday CAB

**Description:** Update Elasticsearch index templates to ensure correct shard count for all new indices. Add Logstash backpressure monitoring. Test index creation with peak ingest rate load.

**Outcome:** Successful. Index templates updated. Load test confirmed correct sharding under 3x peak ingest rate. Logstash pipeline lag alert active.

---

## CHG-20250325-0031
**Date:** 2025-03-25 | **Type:** Normal Minor | **Status:** Completed
**Service:** Database Read Replicas | **RFC Owner:** DBA Team
**CAB Approval:** 2025-03-18 Tuesday CAB

**Description:** Implement read-traffic routing based on replica lag. Maximum acceptable read lag: 30 seconds. If lag exceeds threshold, route reads to alternative replica. Add replica lag monitoring per region.

**Outcome:** Successful. Lag-based routing implemented via ProxySQL. Test confirmed traffic correctly rerouted when replica lag exceeded 30 seconds. EU-West and EU-Central replicas both monitored.

---

## CHG-20250408-0032
**Date:** 2025-04-08 | **Type:** Normal Major | **Status:** Completed
**Service:** nginx Core API Configuration | **RFC Owner:** Platform Engineering
**CAB Approval:** 2025-04-03 Thursday CAB

**Description:** Tune nginx worker_connections for Core API: increase from 1024 to 4096. Add connection rate limiting for clients without active sessions. Add Dash0 dashboard for nginx connection metrics.

**Outcome:** Successful. worker_connections increased. Connection rate limiting tested (correctly throttles bad clients). Nginx dashboard live in Dash0.

---

## CHG-20250415-0033
**Date:** 2025-04-15 | **Type:** Normal Major | **Status:** Completed
**Service:** Customer API v2 | **RFC Owner:** Platform Engineering
**CAB Approval:** 2025-04-10 Thursday CAB

**Description:** Deprecation rollback: revert API v2 serializer to original field names (total_count, page_size). Add API contract tests. Implement formal breaking change policy document. v3 field format to be introduced in v3 only.

**Outcome:** Successful. v2 API backward compatibility restored. API contract tests added to CI pipeline (12 tests). Breaking change policy ratified by Platform lead and published.

---

## CHG-20250421-0034
**Date:** 2025-04-21 | **Type:** Normal Major | **Status:** Completed
**Service:** Stripe Payment Integration | **RFC Owner:** Payments Engineering
**CAB Approval:** 2025-04-17 Thursday CAB

**Description:** Update Stripe integration to latest stable API version. Implement Stripe API version monitoring (alert when current version is within 90 days of deprecation). Add enterprise customer onboarding notification to payment processor.

**Outcome:** Successful. Stripe API updated to 2024-12-18.acacia. Version monitoring alert active. Onboarding checklist updated.

---

## CHG-20250425-0035
**Date:** 2025-04-25 | **Type:** Normal Minor | **Status:** Completed
**Service:** Monitoring (Dash0) | **RFC Owner:** Platform Engineering + Operations
**CAB Approval:** 2025-04-22 Tuesday CAB

**Description:** Add comprehensive Dash0 monitoring: NTP clock drift alert (>10s), Kubernetes OOMKilled events alert, FCM delivery failure rate alert, WAL archive failure alert, replica lag per-region dashboard.

**Outcome:** Successful. 8 new alert rules deployed. All test-fired successfully. No false positives in 7-day observation period.
