"""Domain tools for the Service Request Agent.

Covers: SLA lookup by request type, approval chain determination, and
request completeness validation — the three most common friction points
in service request handling.
"""

from langchain_core.tools import tool
from .rag_tools import make_rag_tools


# SLA data keyed by request type keyword → (fulfillment_days, description)
_SLA_TABLE = {
    "onboarding":        (5,  "New starter onboarding bundle"),
    "new starter":       (5,  "New starter onboarding bundle"),
    "offboarding":       (0,  "Same day (leavers — immediate access revocation required)"),
    "leaver":            (0,  "Same day (leavers — immediate access revocation required)"),
    "access removal":    (0,  "Same day for leavers; 24 hours for role changes"),
    "emergency access":  (0,  "2 hours (P1/P2-linked, manager approval required)"),
    "hardware":          (5,  "Hardware procurement / replacement"),
    "laptop":            (5,  "Hardware procurement / replacement"),
    "software":          (3,  "Standard software installation / SaaS provisioning"),
    "licence":           (3,  "Software licence allocation"),
    "license":           (3,  "Software licence allocation"),
    "access":            (1,  "Standard access grant/change (business hours)"),
    "permission":        (1,  "Permission / role change"),
    "dns":               (1,  "DNS change (standard catalogue entry SC-003)"),
    "certificate":       (1,  "SSL certificate renewal (standard catalogue entry SC-002)"),
    "firewall":          (2,  "Firewall rule change (standard template)"),
    "report":            (3,  "Standard report or data export"),
    "data export":       (3,  "Data export (standard)"),
    "gdpr":              (4,  "GDPR Subject Access Request — 30-day statutory deadline; internal SLA 4 business days"),
    "sar":               (4,  "GDPR SAR — 30-day statutory deadline; internal SLA 4 business days"),
    "erasure":           (5,  "GDPR Right to Erasure — 30-day statutory; internal SLA 5 business days"),
    "vm":                (3,  "Virtual machine provisioning"),
    "storage":           (3,  "Storage allocation"),
    "dr test":           (3,  "DR / business continuity test"),
    "vulnerability":     (2,  "CVE / vulnerability assessment and remediation"),
    "patch":             (1,  "Security patch (standard SC-001 if on approved list)"),
    "training":          (5,  "Training / certification request"),
    "audit":             (10, "Compliance audit evidence package"),
    "complex":           (5,  "Complex multi-team request"),
}

_REQUIRED_FIELDS = {
    "access":        ["requester_name", "employee_id", "manager_name", "cost_centre", "access_required", "justification"],
    "onboarding":    ["requester_name", "new_hire_name", "start_date", "role_title", "manager_name", "cost_centre", "required_systems"],
    "offboarding":   ["requester_name", "leaver_name", "last_working_day", "manager_name", "equipment_return_date"],
    "hardware":      ["requester_name", "employee_id", "manager_name", "cost_centre", "device_spec", "business_justification"],
    "software":      ["requester_name", "employee_id", "manager_name", "software_name", "version", "cost_centre"],
    "data_export":   ["requester_name", "data_description", "date_range", "business_justification", "manager_name"],
    "gdpr":          ["customer_reference", "verification_method", "data_categories_requested", "legal_team_sign_off"],
    "firewall":      ["requester_name", "source_ip_range", "destination_ip_range", "port", "protocol", "business_justification", "manager_name"],
    "default":       ["requester_name", "manager_name", "cost_centre", "description", "required_date"],
}


@tool
def get_request_sla(request_type: str) -> str:
    """Look up the SLA fulfillment target and approval chain for a given service
    request type. Use this to tell requesters how long their request will take
    and what approvals are needed.

    Args:
        request_type: Free-text description of the request type, e.g.
            'new starter onboarding', 'software installation', 'GDPR SAR',
            'VPN access', 'hardware replacement', 'firewall rule'.
    """
    rt_lower = request_type.lower()

    matched_days, matched_desc = 3, "Standard service request"
    for keyword, (days, desc) in _SLA_TABLE.items():
        if keyword in rt_lower:
            matched_days = days
            matched_desc = desc
            break

    if matched_days == 0:
        sla_str = "Same day / immediate"
    elif matched_days == 1:
        sla_str = "1 business day"
    else:
        sla_str = f"{matched_days} business days"

    # Approval chain
    if "gdpr" in rt_lower or "sar" in rt_lower or "erasure" in rt_lower:
        approval = "Legal Team sign-off + Data Protection Officer notification"
    elif "emergency" in rt_lower and "access" in rt_lower:
        approval = "Manager approval (verbal + ticket) + IT Security notification"
    elif "privileged" in rt_lower or "admin" in rt_lower or "root" in rt_lower:
        approval = "Line manager + IT Security + Data Owner (3-way approval)"
    elif "bulk" in rt_lower or ">10" in rt_lower:
        approval = "Service Delivery Manager approval (bulk requests >10 users)"
    elif any(kw in rt_lower for kw in ["software", "licence", "license"]):
        approval = "Line manager + Procurement if cost >£500/year"
    else:
        approval = "Line manager approval"

    return (
        f"Service Request SLA: {matched_desc}\n"
        f"\nFulfillment target: {sla_str}\n"
        f"Approval required: {approval}\n"
        f"\nMeasurement: Business hours (08:00–18:00 Mon–Fri) unless emergency\n"
        f"SLA clock starts: On ticket creation / receipt of all required information\n"
        f"\nNote: SLA clock pauses if waiting for customer-provided information "
        f"(e.g. manager approval, verification documents)."
    )


@tool
def validate_request_fields(request_type: str, provided_fields_csv: str) -> str:
    """Check whether a service request has all required fields to be processed.
    Use this before assigning a request to confirm it won't bounce back.

    Args:
        request_type: Type of service request, e.g. 'access', 'onboarding',
            'offboarding', 'hardware', 'software', 'gdpr', 'firewall'.
        provided_fields_csv: Comma-separated list of fields that have been
            provided, e.g. 'requester_name,manager_name,cost_centre'.

    Returns a list of missing required fields, or confirms the request is complete.
    """
    # Normalise request type to a category key
    rt_lower = request_type.lower()
    category = "default"
    for key in _REQUIRED_FIELDS:
        if key in rt_lower:
            category = key
            break

    required = _REQUIRED_FIELDS[category]
    provided = {f.strip().lower() for f in provided_fields_csv.split(",") if f.strip()}
    missing = [f for f in required if f.lower() not in provided]

    if not missing:
        return (
            f"✓ Request is COMPLETE — all required fields present for '{request_type}'.\n"
            f"\nRequired fields: {', '.join(required)}\n"
            f"Provided: {', '.join(sorted(provided))}\n"
            f"\nRequest can be assigned for fulfillment."
        )

    missing_str = "\n".join(f"  ✗ {f.replace('_', ' ').title()}" for f in missing)
    return (
        f"⚠ Request INCOMPLETE — missing required fields for '{request_type}':\n"
        f"\n{missing_str}\n"
        f"\nAll required fields: {', '.join(f.replace('_', ' ').title() for f in required)}\n"
        f"\nAction: Return to requester requesting missing information. "
        f"SLA clock should be paused until all fields are received."
    )


@tool
def check_approval_chain(request_type: str, estimated_cost_gbp: float) -> str:
    """Determine the complete approval chain required before fulfilling a
    service request. Use this to ensure correct sign-offs are obtained.

    Args:
        request_type: The type of service request being processed.
        estimated_cost_gbp: Estimated annual cost in GBP (0 if no cost).

    Returns the required approvers in order, any conditions, and the
    process to follow if an approver is unavailable.
    """
    rt_lower = request_type.lower()
    approvers = []
    notes = []

    # Line manager always required first
    approvers.append("1. Line Manager (mandatory for all requests)")

    # Cost threshold
    if estimated_cost_gbp > 500:
        approvers.append(f"2. Procurement (cost £{estimated_cost_gbp:,.0f}/year exceeds £500 threshold)")
    if estimated_cost_gbp > 5000:
        approvers.append(f"3. Finance Director (cost £{estimated_cost_gbp:,.0f}/year exceeds £5,000 threshold)")

    # Access type
    if any(kw in rt_lower for kw in ["privileged", "admin", "root", "sudo", "production"]):
        approvers.append("• IT Security Lead (privileged/production access)")
        approvers.append("• Data Owner (if accessing sensitive data)")
        notes.append("Privileged access requires quarterly review and just-in-time provisioning where possible.")

    if any(kw in rt_lower for kw in ["bulk", "all users", "department"]):
        approvers.append("• Service Delivery Manager (bulk requests >10 users)")

    if any(kw in rt_lower for kw in ["gdpr", "sar", "personal data", "erasure"]):
        approvers.append("• Legal Team (GDPR/data privacy requests)")
        approvers.append("• Data Protection Officer (notification required)")
        notes.append("Statutory deadline: 30 calendar days from verified request receipt.")

    if any(kw in rt_lower for kw in ["firewall", "network", "dns", "routing"]):
        approvers.append("• Network Security Lead (network configuration changes)")

    if any(kw in rt_lower for kw in ["emergency", "urgent", "p1", "p2"]):
        notes.append("Emergency access: verbal manager approval accepted; written confirmation required within 2 hours.")

    approvers_str = "\n".join(f"  {a}" for a in approvers)
    notes_str = "\n".join(f"  • {n}" for n in notes) if notes else "  • Standard approval flow applies."

    return (
        f"Approval chain for '{request_type}' (cost: £{estimated_cost_gbp:,.0f}/yr):\n"
        f"\n{approvers_str}\n"
        f"\nNotes:\n{notes_str}\n"
        f"\nIf approver is unavailable: delegate approval to their named deputy. "
        f"Document delegation in ticket. No self-approval permitted."
    )


def get_service_tools() -> list:
    """Return the full tool list for the Service Request Agent."""
    return make_rag_tools("service") + [
        get_request_sla,
        validate_request_fields,
        check_approval_chain,
    ]
