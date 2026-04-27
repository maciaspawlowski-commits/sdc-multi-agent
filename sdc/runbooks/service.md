# SDC Service Request Runbook

## Overview and Purpose
This runbook covers the full lifecycle of service requests raised via the SDC Service Catalog. It defines fulfillment procedures, approval workflows, SLA targets, and quality standards for all catalog items. Every service request must be logged in the ITSM portal with reference format SR-YYYYMMDD-NNNN.

## Definitions
- **Service Request**: A formal request for something new — access, hardware, software, information — as opposed to a report of a failure.
- **Service Catalog**: The published list of services SDC offers with their fulfillment procedures and SLAs.
- **Fulfillment Team**: The team responsible for completing the request.
- **Approver**: The person authorised to approve a request before fulfillment begins.
- **Role Template**: A predefined set of access and software entitlements mapped to a job role.

## Service Catalog Categories and SLAs

### Category 1: Access Management
**Scope**: User accounts, role/permission assignments, VPN, MFA, privileged access, API keys, shared accounts

**SLA targets**:
| Item | Fulfillment SLA |
|---|---|
| Standard role assignment | 3 business days |
| Privileged/admin access | 5 business days |
| VPN access | 2 business days |
| MFA setup | 1 business day |
| Emergency access (P1-linked) | 2 hours |
| Access removal (leaver) | Same day |
| Temporary access (<30 days) | 3 business days |

**Approval workflow**:
- Standard access → Line manager only
- Privileged/admin access → Line manager + IT Security + Data Owner
- Bulk access (>10 users) → Service Delivery Manager
- Temporary access (>30 days) → Line manager + SDM review

**Fulfillment steps**:
1. Validate request completeness (employee ID, manager, specific access, justification)
2. Check for duplicate access (is this already assigned?)
3. Obtain approval(s) — clock pauses pending approval
4. Provision access per access control policy (principle of least privilege)
5. Test access from the requester's account
6. Notify requester with access confirmation and instructions
7. Update CMDB access register
8. Close SR with completion notes

### Category 2: Hardware and Equipment
**Scope**: Laptops, desktops, monitors, peripherals, mobile phones, tablets, loaner devices, equipment replacement

**SLA targets**:
| Item | Fulfillment SLA |
|---|---|
| Standard laptop (in stock) | 3 business days |
| Standard laptop (procurement required) | 15 business days |
| Monitor/peripheral (in stock) | 2 business days |
| Mobile device (in stock) | 5 business days |
| Emergency replacement (P1-linked) | 1 business day |

**Required information**:
- Employee name, ID, and office location
- Device type, specification, and quantity
- Existing asset tag if replacement
- Manager approval
- Cost centre and budget code
- Delivery address if remote worker

**Fulfillment steps**:
1. Check asset inventory in CMDB for available stock
2. If stock available: configure device per role template (see below)
3. If stock unavailable: raise purchase order — notify requester of delay with new ETA
4. Pre-configuration checklist: OS provisioned, MDM enrolled, encryption enabled, required software installed, security baseline applied
5. Asset registered in CMDB before delivery (assign asset tag)
6. Ship or arrange collection — obtain signed delivery confirmation
7. For replacements: arrange return of old device, update CMDB, decommission or reassign
8. Confirm with requester that device works as expected
9. Close SR

### Category 3: Software and Licensing
**Scope**: New software installation, license allocation, SaaS account provisioning, software removal, license reclamation

**SLA targets**:
| Item | Fulfillment SLA |
|---|---|
| In-catalogue software | 2 business days |
| New software (not in catalogue) | 5 business days |
| SaaS account provisioning | 1 business day |
| License reclamation (leaver) | Same day |

**Approval workflow**:
- In-catalogue software → Line manager
- New software (<£500/year) → Line manager + Security review
- New software (>£500/year) → Line manager + Security review + Procurement approval
- Open-source software → Line manager + Security (licence compatibility check mandatory)

**Security review checklist for new software**:
- [ ] EULA/licence reviewed — compatible with SDC usage
- [ ] Data residency confirmed (where does data go?)
- [ ] Privacy policy reviewed (GDPR compliance)
- [ ] Vendor security assessment completed (or waived for low-risk)
- [ ] Integration requirements reviewed (SSO, API access)
- [ ] Exit strategy documented

**Fulfillment steps**:
1. Validate request and obtain approval(s)
2. Check existing licence inventory — is a spare licence available?
3. If no licence available: initiate procurement (PO raised, delivery time varies)
4. Install or provision per vendor installation guide
5. Configure SSO integration if applicable
6. Provide user with access credentials/instructions
7. Update licence register in ITSM
8. Update software register in CMDB
9. Close SR

### Category 4: New Starter Onboarding
**Scope**: Complete onboarding bundle for new employees

**SLA**: 5 business days fulfillment — request MUST be raised minimum 5 business days before start date

**Required information**:
- Full legal name (exactly as per employment contract)
- Personal email (for pre-start communication)
- Job title, department, and team
- Line manager name and employee ID
- Start date and office location (or remote)
- Cost centre and employee ID (from HR — must be confirmed before processing)
- Role template (from HR-approved role list)
- Any non-standard access requirements (with written justification)
- Whether laptop required or BYOD

**Onboarding bundle components**:
1. Active Directory account (username: firstname.lastname, auto-generated if conflict)
2. Microsoft 365 mailbox (format: firstname.lastname@sdc.com)
3. Distribution group memberships per role template
4. Microsoft Teams channel memberships per role template
5. Laptop provisioned per role specification (or access to VDI if remote)
6. Software installed per role template
7. Building access card (office workers only — liaise with Facilities)
8. MFA enrolled (instructions sent to personal email pre-start)
9. Self-service password reset configured
10. SaaS applications provisioned per role template (Jira, GitHub, Slack, etc.)

**Role Templates (examples)**:
| Role | Applications Included |
|---|---|
| Software Engineer | GitHub, Jira, Confluence, Slack, AWS dev, IntelliJ IDEA, Datadog |
| Service Desk Agent | ITSM, Confluence, Slack, Teams, Zendesk, basic Jira |
| Data Analyst | PowerBI, Databricks read-only, Jira, Confluence, Slack |
| Finance Analyst | Finance ERP, Excel/M365, Jira, Confluence, Slack, read-only BI |
| Manager | Full Jira, Confluence, Slack, Teams, HR system manager view |

**Step-by-step onboarding checklist**:
1. Validate HR confirmation (employee ID confirmed, contract signed)
2. Check start date vs request date — escalate to SDM if <5 days
3. Create AD account per naming convention
4. Create M365 mailbox — assign appropriate licence tier
5. Apply role template: distribution groups, Teams memberships
6. Raise hardware SR (if applicable) — link to this SR
7. Raise software SR for non-template applications — link to this SR
8. Provision SaaS accounts per role template
9. Generate welcome pack: credentials, IT guide, contact list
10. Send welcome email to personal email address 2 days before start
11. Book 30-minute IT orientation call for day 1
12. Confirm building access card is ready (Facilities sign-off)
13. Post-start (day 2): follow-up with new starter to confirm all access working
14. Close SR with completion notes

**Late Requests** (raised <5 business days before start):
- Escalate immediately to Service Delivery Manager
- Basic access (AD + email) prioritised for day 1
- Full bundle completed within 3 days of start
- Manager notified of what will be ready vs delayed
- Reason for late request documented in SR for process review

### Category 5: Offboarding
**Scope**: Account deactivation, equipment return, licence reclamation, data archival, access removal for leavers

**SLA**: Request raised minimum 5 business days before last working day; execution on last working day

**Immediate offboarding** (disciplinary/security risk):
- Same-day execution regardless of notice
- Requires HR Director written authorisation
- Accounts disabled BEFORE notifying employee
- Full procedure completed within 4 hours

**Standard offboarding checklist**:
1. Receive HR notification with confirmed last working day
2. Validate employee ID and last working day
3. Day of last working — execute at 17:00 (end of business):
   - Disable AD account (do not delete — archive for 90 days)
   - Revoke VPN, MFA, and remote access certificates immediately
   - Revoke all cloud access (AWS, Azure, GCP)
4. Set up email forwarding to line manager (30 days default; extend on request)
5. Remove from all distribution groups and Teams channels
6. Remove from all SaaS applications (run leaver checklist below)
7. Collect equipment (in-office: return to IT desk; remote: courier label sent)
8. Log equipment return in CMDB — update status to "Returned"
9. Reclaim software licences — update licence register
10. Archive mailbox per retention policy (default 7 years)
11. Remove building access card — notify Facilities
12. After 90 days: delete AD account (retain mailbox per policy)
13. Generate leaver completion report for HR

**SaaS Leaver Checklist**:
- [ ] GitHub: remove from org, transfer any owned repos
- [ ] Jira/Confluence: deactivate account, reassign open issues to manager
- [ ] Slack: deactivate workspace account, export DMs if legal hold
- [ ] AWS: remove IAM user, rotate any shared credentials they had access to
- [ ] Datadog/monitoring tools: deactivate
- [ ] Password manager: remove membership
- [ ] Any other SaaS: run discovery query in MDM for installed apps

### Category 6: Infrastructure Requests
**Scope**: VM provisioning, cloud resources, storage, DNS changes, firewall rules, SSL certificates, load balancer config

**SLA**: Standard 5 business days; urgent (P2-linked) 2 business days

**Required information**:
- Technical specification (CPU cores, RAM, storage GB, OS type and version)
- Environment (development / staging / production)
- Network zone and VLAN requirements
- Security classification (Public / Internal / Confidential / Restricted)
- Business justification and application owner
- Backup and DR requirements
- Expected lifespan (permanent / temporary — if temporary, decommission date)
- Cost centre and budget approval (for cloud resources: estimated monthly cost)

**Cloud Resource Request**:
- Include: AWS account ID or Azure subscription, region preference, resource tags required
- Infrastructure-as-Code preferred: requester provides Terraform module if available
- Cost estimate reviewed by FinOps team for resources >£500/month
- Tagging policy mandatory: Environment, CostCentre, Owner, Application, Team

### Category 7: Communication and Collaboration
**Scope**: Distribution lists, shared mailboxes, Teams channel/team creation, Zoom rooms, conference room calendars

**SLA**: 2 business days

**Distribution list request**:
- Owner name (mandatory — someone must own all DLs)
- Initial membership list
- Purpose/description
- External visibility (internal-only or external-facing)
- Moderated or unmoderated

**Shared mailbox request**:
- Business purpose
- Owner and team members who need access
- Mailbox naming convention: team-function@sdc.com

### Category 8: Report and Data Requests
**Scope**: ITSM reports, data exports, BI dashboard access, custom report development, data extraction from operational systems

**SLA**: Standard reports 1 business day; Custom reports 5 business days; BI dashboard access 2 business days

**Data request governance**:
- All data requests must include: business purpose and legal basis for processing
- Requests for personally identifiable data require DPO sign-off
- Data exports must go to approved storage only (not personal email or consumer cloud)

## Bulk Request Processing

### Definition
Any request affecting >10 users simultaneously (e.g. mass access provisioning, department onboarding, office move).

### Process
1. Requester downloads bulk request CSV template from ITSM portal
2. Complete template with one row per user
3. Attach completed CSV to SR — single SR covers all users
4. Service Delivery Manager approval required (in addition to standard approvals)
5. Fulfillment team processes CSV in batches of 10
6. Progress updated in SR daily until complete
7. Exception report generated for any users that failed processing

## Request Validation Checklist
Before processing any request:
- [ ] Requester identity confirmed (employee ID matches HR record)
- [ ] Manager approval obtained — not self-approved
- [ ] Cost centre valid and active (Finance confirmation if >£500)
- [ ] Required date is achievable within SLA (escalate if not)
- [ ] Duplicate check: no existing active SR for same item and user
- [ ] For access: principle of least privilege applied
- [ ] Licence availability confirmed (or procurement raised if not)
- [ ] For hardware: asset inventory checked first

## SLA Clock Rules for Service Requests
- Clock starts: SR creation timestamp
- Clock pauses: awaiting approval (documented in SR), awaiting information from requester, awaiting procurement delivery
- Clock restarts: approval received, information provided, goods received
- Clock stops: requester confirms fulfillment complete, or 24h auto-close after "Fulfilled" status set

## Fulfillment Quality Assurance
Within 1 business day of marking a request as Fulfilled:
- Confirm with requester that access/item works as expected (call or email)
- Verify CMDB updated with new asset/access record
- Attach completion evidence to SR ticket (screenshot of provisioned access, delivery confirmation, etc.)
- Verify licence register updated
- Close SR with fulfillment notes including exact steps taken

## Common Exceptions and Escalations

### Request Raised After Required Date
- Flag immediately to Service Delivery Manager
- Assess urgency and business impact
- If business-critical: treat as urgent (2 business day SLA)
- Document reason for late request and lessons for requester's manager

### Requester Left Company Before Fulfillment
- Cancel SR and document in ticket
- Notify manager of cancellation
- Reclaim any provisioned resources immediately

### Licence Unavailable — Requester Waiting
- Notify requester immediately with expected delivery date
- SDM informed if wait >5 business days
- Consider temporary alternative from catalogue while waiting

## SaaS Application Provisioning Procedures

### GitHub Enterprise Provisioning
1. Navigate to GitHub org admin panel → People → Invite member
2. Enter employee email address (must match corporate email)
3. Set role: Member (default) or Owner (requires IT Security approval)
4. Assign to correct teams based on role template (e.g., backend-engineers, platform-team)
5. For repository access: add user to relevant repos with appropriate permission level (Read/Write/Admin)
6. For private repo access beyond role template: requires repo owner approval
7. Notify user via email with org name and acceptance link
8. Confirm user has accepted invite within 5 days (re-send if not)

### AWS IAM Provisioning
1. Log in to AWS Management Console with IAM admin credentials
2. Navigate to IAM → Users → Create User
3. Username format: firstname.lastname (same as AD)
4. Set permissions: attach policies per role template (never grant AdministratorAccess without Security approval)
5. For console access: set temporary password, enforce reset at first login
6. For programmatic access: generate access key, deliver securely via password manager (never email)
7. Tag user: Team=X, CostCentre=X, Environment=X
8. For privilege escalation (e.g., Admin on dev account): requires IT Security + Data Owner sign-off

### Jira and Confluence Provisioning
1. Navigate to site admin → User management → Invite users
2. Enter corporate email address
3. Set product access: Jira Software / Jira Service Management / Confluence (as per role template)
4. Assign to relevant groups (maps to project permissions automatically)
5. For Jira project admin role: requires project owner approval
6. Notify user with workspace URL and login instructions
7. Verify user can log in and access expected projects within 1 business day

### Slack Provisioning
1. Navigate to Slack admin → Members → Invite people
2. Enter corporate email
3. Set role: Member (default) or Workspace Admin (requires SDM approval)
4. User will receive email invitation and can self-enrol
5. Add to mandatory channels: #general, #announcements, #team-[dept]
6. Add to role-specific channels per role template
7. For external Slack Connect: requires separate approval process (SDM + Security)

### Microsoft 365 / Teams Provisioning
1. User account created in Azure AD (part of onboarding process)
2. Assign M365 licence tier (E3 standard; E5 for senior roles or special requirements)
3. Teams: add to relevant team via Teams admin centre or direct team settings
4. SharePoint: add to relevant site collections with appropriate permission level
5. OneDrive: auto-provisioned with account (10TB default)
6. For shared drives/SharePoint sites: site owner must add user

### Datadog / Monitoring Tools Provisioning
1. Navigate to Datadog org settings → Team → Invite members
2. Enter corporate email
3. Set role: Read Only (default for analysts) / Standard (engineers) / Admin (team leads only)
4. Assign to relevant teams and dashboards
5. For custom dashboard creation: Standard role required
6. Notify user with org name and login instructions (SSO via Okta)

### VPN Access Provisioning
1. Verify line manager approval in SR
2. Create VPN profile in [VPN solution: Cisco AnyConnect / GlobalProtect]
3. Assign to correct VPN group (employee-standard / contractor-restricted / admin-full)
4. Generate certificate or configure MFA push for authentication
5. Send setup guide to user with VPN server address and credentials
6. Confirm user can connect successfully before closing SR
7. For elevated VPN access (admin networks): IT Security approval required

### MFA Setup Procedure
1. Verify user AD account is active
2. Send user self-service MFA enrolment link via corporate email
3. User installs Microsoft Authenticator or Google Authenticator
4. User scans QR code and registers TOTP device
5. Configure backup method: secondary email or backup codes (stored securely by user)
6. Test: user completes MFA challenge to confirm setup
7. For hardware tokens (FIDO2/YubiKey): physical delivery required; register in MDM

## Device Provisioning Procedures

### Laptop Build Specification by Role
| Role | CPU | RAM | Storage | OS |
|---|---|---|---|---|
| Software Engineer | Apple M3 Pro or i7 | 32GB | 512GB SSD | macOS / Windows 11 |
| Data Analyst | i5 or M2 | 16GB | 256GB SSD | Windows 11 / macOS |
| Service Desk | i5 | 8GB | 256GB SSD | Windows 11 |
| Executive | Apple M3 Pro | 32GB | 512GB SSD | macOS |
| Standard Employee | i5 | 16GB | 256GB SSD | Windows 11 |

### Laptop Pre-Configuration Checklist
- [ ] OS installed and fully patched
- [ ] MDM (Intune/Jamf) enrolled and policy applied
- [ ] Full-disk encryption enabled (BitLocker/FileVault)
- [ ] Security baseline applied (CIS Level 1 minimum)
- [ ] Endpoint protection installed and active (CrowdStrike/Defender)
- [ ] Required software installed per role template
- [ ] Browser configured with SSO bookmarks
- [ ] Asset tag applied (physical label + CMDB entry)
- [ ] Serial number recorded in CMDB against employee record

### Remote Employee Laptop Delivery
1. Package laptop securely with all accessories
2. Generate courier label via preferred courier portal
3. Send tracking number to employee personal email
4. Employee confirms receipt and condition in SR ticket
5. Employee connects to VPN and MDM checks-in automatically
6. Follow up within 1 business day to confirm setup complete

### Mobile Device Provisioning (Corporate)
1. Raise MDM enrolment request in ITSM
2. Assign device to employee in MDM console (Intune)
3. Push corporate email profile and required apps
4. Configure device passcode policy and remote wipe capability
5. Employee accepts MDM enrolment on device
6. Confirm corporate email and apps accessible
7. Register device in CMDB with IMEI

### BYOD (Bring Your Own Device) Enrolment
1. Employee raises BYOD SR with device type and OS version
2. IT Security approves/rejects based on OS version (minimum: iOS 16, Android 12)
3. Employee installs Intune Company Portal app
4. Employee completes self-service enrolment (personal data untouched)
5. Corporate email profile pushed to device
6. Conditional Access policy applied: compliant device required for corporate data

## Access Reviews and Recertification

### Quarterly Access Review
- Run quarterly access report from ITSM and AD for all active users
- Distribute to line managers: list of all access their direct reports hold
- Managers confirm or request removal for each access item within 10 business days
- IT team removes any access confirmed as no longer required
- Access review completion documented in SR; overdue managers escalated to SDM

### Privileged Access Review (Monthly)
- Monthly report of all admin/privileged accounts
- IT Security reviews: confirm each account is still required, still assigned to active employee
- Any privileged access without valid SR: immediately disabled pending review
- Just-in-time (JIT) privileged access preferred for admin tasks — review if permanent admin access can be converted to JIT

### Contractor Access Expiry
- All contractor accounts created with automatic expiry date matching contract end date
- 2 weeks before expiry: automated notification to contractor manager
- On expiry date: account auto-disabled
- Extension requires new SR with updated contract dates and manager re-approval

## Service Request Metrics and Reporting

### KPIs for Service Requests
| Metric | Target |
|---|---|
| On-time fulfillment rate | ≥95% |
| Request backlog age (>5 days old) | <5% of open queue |
| Requests awaiting approval >2 days | <10% of pending queue |
| Requester satisfaction score | ≥4.2/5.0 |
| Repeat requests (same user/item, second request within 30 days) | <3% |

### Monthly Service Request Report
- Total volume by category
- On-time fulfillment % by category
- Average fulfillment time by category
- Backlog analysis: aged items and reasons
- Top 5 most-requested items (feeds catalogue improvement)
- Exception report: late requests, rejected approvals, procurement delays

## Password and Credentials Management

### Password Policy for Provisioned Accounts
- Minimum length: 14 characters
- Complexity: upper, lower, number, special character
- No reuse of last 24 passwords
- Expiry: 90 days for standard; 30 days for privileged accounts
- Lockout: 5 failed attempts → 30-minute lockout

### Temporary Password Delivery
- Never send credentials via unencrypted email
- Use: password manager shared vault (1Password/Bitwarden), secure link (with expiry), or phone call
- Recipient must change password on first login (enforced by AD policy)
- For privileged accounts: in-person or encrypted email with PGP

### Service Account Credentials
- Service accounts registered in CMDB with owner and expiry date
- Credentials stored in HashiCorp Vault / AWS Secrets Manager — never in code
- Rotation schedule: every 90 days (automated where possible)
- For shared service accounts: any team member change triggers immediate rotation

## Printer and Peripheral Setup

### Office Printer Setup
- Printer setup raised as SR with office location and preferred printer
- IT team adds printer to employee's device via Group Policy (Windows) or CUPS (macOS)
- Default printer set per office floor mapping
- For colour printing rights: manager approval required

### Video Conferencing Equipment
- Conference room AV setup: raise SR with room name and requirement
- Personal webcam/headset: bundled with standard laptop order for remote workers
- Zoom Rooms provisioning: AV team handles hardware; IT handles software licence

## Remote Work Equipment and Access

### Remote Worker Standard Kit
| Item | Specification |
|---|---|
| Laptop | Role-appropriate spec (see hardware section) |
| Monitor | 27" 4K external display |
| Keyboard/Mouse | Wireless ergonomic set |
| Webcam | HD 1080p (if laptop camera insufficient) |
| Headset | Noise-cancelling for video calls |
| Home network | IT provides list of minimum router specs; no IT support for home network |

### Remote Access Requirements
- VPN mandatory for all access to internal systems
- VPN split-tunneling: corporate traffic via VPN; personal browsing direct
- Minimum home broadband: 50 Mbps down / 10 Mbps up (user's responsibility)
- For developers: SSH access to dev environments via bastion host (separate SR)

## Service Desk Escalation for Service Requests

### When to Escalate a Service Request
- Approval not received within 2 business days → chase manager directly
- Licence unavailable and procurement >10 business days → escalate to SDM
- Requester reports access not working after fulfillment → convert to incident (INC)
- Multiple SRs for same user repeatedly → flag to SDM (possible process training need)
- Request outside catalogue scope → route to SDM for assessment

### Rejected Service Requests
- Rejection reason must be documented in SR ticket
- Notify requester with reason and alternative options if available
- For access rejections: requester can appeal to their SDM's counterpart
- Rejected requests retained in ITSM for audit purposes (7-year retention)
