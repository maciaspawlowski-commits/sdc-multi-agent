"""Domain tools for the Incident Response Agent.

Tools cover the three most useful deterministic operations the LLM cannot
reliably do on its own: priority classification, SLA deadline calculation,
and escalation path lookup — all derived from the SDC incident runbook rules.
"""

from datetime import datetime, timedelta
from langchain_core.tools import tool
from .rag_tools import make_rag_tools


@tool
def classify_priority(
    service_name: str,
    users_affected: int,
    has_workaround: bool,
    revenue_impact: bool,
) -> str:
    """Classify the correct incident priority (P1–P4) based on SDC's impact/urgency
    matrix. Use this whenever you need to determine or confirm a priority level.

    Args:
        service_name: Name of the affected service (e.g. 'Payment Gateway').
        users_affected: Estimated number of users impacted.
        has_workaround: True if a workaround is available that restores service.
        revenue_impact: True if the incident is causing direct revenue loss.

    Returns a priority label, SLA targets, and the immediate actions required.
    """
    # P1: complete outage or revenue-impacting with no workaround
    if revenue_impact and not has_workaround:
        priority, resolution, response = "P1", "1 hour", "15 minutes"
        actions = [
            "Open #incident-bridge war room immediately",
            "Page Duty Manager now",
            "Notify CTO if not resolved within 30 minutes",
            "15-minute update cadence required",
            "Post-mortem mandatory after resolution",
        ]
    elif users_affected > 500 and not has_workaround:
        priority, resolution, response = "P1", "1 hour", "15 minutes"
        actions = [
            "Open #incident-bridge war room",
            "Page Duty Manager",
            "15-minute update cadence",
            "Post-mortem mandatory",
        ]
    # P2: significant impact, workaround unavailable or large user count
    elif users_affected > 100 or (not has_workaround and users_affected > 50):
        priority, resolution, response = "P2", "4 hours", "30 minutes"
        actions = [
            "Escalate to Team Lead within 30 minutes",
            "Notify Service Delivery Manager",
            "30-minute update cadence",
            "Post-mortem if this is a repeat P2",
        ]
    # P3: partial degradation with workaround or small user count
    elif users_affected > 10 or not has_workaround:
        priority, resolution, response = "P3", "8 business hours", "2 hours"
        actions = [
            "Assign to correct resolver group",
            "Team Lead review within 4 hours",
            "Communicate workaround to affected users if available",
        ]
    # P4: minimal impact
    else:
        priority, resolution, response = "P4", "3 business days", "4 hours"
        actions = ["Standard ticket queue", "No immediate escalation required"]

    availability_sla = {
        "P1": "99.99% (max 4.3 min/month downtime)",
        "P2": "99.9%  (max 43.8 min/month downtime)",
        "P3": "99.5%  (max 3.6 hr/month downtime)",
        "P4": "99.0%  (max 7.3 hr/month downtime)",
    }[priority]

    return (
        f"PRIORITY: {priority}\n"
        f"Service: {service_name}\n"
        f"Users affected: {users_affected}\n"
        f"Workaround available: {'Yes' if has_workaround else 'No'}\n"
        f"Revenue impact: {'Yes' if revenue_impact else 'No'}\n"
        f"\nSLA Targets:\n"
        f"  First response: {response}\n"
        f"  Resolution target: {resolution}\n"
        f"  Availability SLA: {availability_sla}\n"
        f"\nImmediate actions required:\n"
        + "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions))
    )


@tool
def calculate_resolution_deadline(priority: str, incident_start_iso: str) -> str:
    """Calculate the SLA resolution deadline for an incident given its priority
    and start time. Use this to tell responders exactly when the SLA clock expires.

    Args:
        priority: Incident priority — one of 'P1', 'P2', 'P3', 'P4'.
        incident_start_iso: ISO 8601 datetime when the incident started,
            e.g. '2025-04-27T14:30:00'. If timezone unspecified, UTC assumed.

    Returns the deadline datetime and minutes remaining from now.
    """
    resolution_minutes = {"P1": 60, "P2": 240, "P3": 480, "P4": 4320}
    priority_upper = priority.upper()

    if priority_upper not in resolution_minutes:
        return f"Unknown priority '{priority}'. Use P1, P2, P3, or P4."

    try:
        # Parse permissively — accept with or without seconds
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                start = datetime.strptime(incident_start_iso.strip(), fmt)
                break
            except ValueError:
                continue
        else:
            return f"Could not parse start time '{incident_start_iso}'. Use ISO format, e.g. 2025-04-27T14:30:00"
    except Exception as e:
        return f"Date parse error: {e}"

    minutes = resolution_minutes[priority_upper]
    deadline = start + timedelta(minutes=minutes)
    now = datetime.utcnow()
    remaining = deadline - now
    remaining_min = int(remaining.total_seconds() / 60)

    status = (
        f"⚠ BREACHED ({abs(remaining_min)} minutes ago)" if remaining_min < 0
        else f"✓ {remaining_min} minutes remaining"
    )

    return (
        f"Priority: {priority_upper}\n"
        f"Incident started: {start.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"SLA window: {minutes} minutes\n"
        f"Resolution deadline: {deadline.strftime('%Y-%m-%d %H:%M UTC')}\n"
        f"Status: {status}\n"
        f"\nNote: P3/P4 SLAs are measured in business hours (08:00–18:00 Mon–Fri). "
        f"This calculation uses wall-clock time — adjust for business hours if applicable."
    )


@tool
def get_escalation_path(priority: str) -> str:
    """Return the full escalation path and communication cadence for a given
    incident priority. Use this to tell responders exactly who to contact
    and when during incident response.

    Args:
        priority: Incident priority — one of 'P1', 'P2', 'P3', 'P4'.
    """
    paths = {
        "P1": {
            "cadence": "15-minute updates",
            "bridge": "Teams channel #incident-bridge (open immediately)",
            "chain": [
                "T+0:  Service Desk acknowledges, opens P1 bridge",
                "T+0:  Duty Manager paged immediately",
                "T+15: CTO notified if not resolved",
                "T+30: Executive sponsor notified if no clear ETA",
                "T+60: SLA breach — SDM prepares customer communication",
            ],
            "template": (
                "INC-[number] declared P1 at [time] UTC. "
                "Impact: [description]. "
                "Resolver: [team]. "
                "Bridge: #incident-bridge. "
                "Next update: [time+15min]."
            ),
        },
        "P2": {
            "cadence": "30-minute updates",
            "bridge": "Teams channel #incident-bridge (open if no workaround)",
            "chain": [
                "T+0:  Service Desk acknowledges",
                "T+30: Escalate to Team Lead if not progressing",
                "T+60: Notify Service Delivery Manager",
                "T+4h: SLA breach — SDM and customer notification required",
            ],
            "template": (
                "INC-[number] declared P2 at [time] UTC. "
                "Impact: [description]. "
                "Resolver: [team]. "
                "ETA: [estimate]. "
                "Next update: [time+30min]."
            ),
        },
        "P3": {
            "cadence": "As needed (at least daily)",
            "bridge": "Not required",
            "chain": [
                "T+0:  Assigned to resolver group queue",
                "T+4h: Team Lead reviews if not picked up",
                "T+8h: SLA breach risk — SDM visibility",
            ],
            "template": (
                "INC-[number] P3 — [summary]. "
                "Resolver: [team]. "
                "Workaround: [if available]. "
                "Resolution ETA: [estimate]."
            ),
        },
        "P4": {
            "cadence": "Weekly",
            "bridge": "Not required",
            "chain": [
                "T+0:  Logged in standard queue",
                "T+3d: SLA breach risk if not resolved",
            ],
            "template": "INC-[number] P4 — [summary]. Resolver: [team].",
        },
    }

    p = priority.upper()
    if p not in paths:
        return f"Unknown priority '{priority}'. Use P1, P2, P3, or P4."

    info = paths[p]
    chain_str = "\n".join(f"  {step}" for step in info["chain"])
    return (
        f"Escalation path for {p}:\n"
        f"\nUpdate cadence: {info['cadence']}\n"
        f"War room: {info['bridge']}\n"
        f"\nTimeline:\n{chain_str}\n"
        f"\nNotification template:\n  \"{info['template']}\""
    )


def get_incident_tools() -> list:
    """Return the full tool list for the Incident Response Agent."""
    return make_rag_tools("incident") + [
        classify_priority,
        calculate_resolution_deadline,
        get_escalation_path,
    ]
