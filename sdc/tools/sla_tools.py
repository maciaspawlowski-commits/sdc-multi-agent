"""Domain tools for the SLA Monitoring Agent.

Covers the three most common SLA calculations: availability percentage,
breach penalty/credit amount, and breach urgency status — all based on
SDC's SLA framework and contract terms.
"""

from langchain_core.tools import tool
from .rag_tools import make_rag_tools


@tool
def calculate_availability(
    total_minutes_in_period: int,
    downtime_minutes: int,
    service_name: str,
) -> str:
    """Calculate service availability percentage for a given period and determine
    whether it meets the SDC SLA target. Use this when analysing incident impact
    on availability or producing SLA compliance reports.

    Args:
        total_minutes_in_period: Total minutes in the measurement period.
            Use 43200 for a 30-day month, 10080 for a week, 1440 for a day.
        downtime_minutes: Total minutes of confirmed service unavailability.
        service_name: Name of the service (used to look up its SLA target).
    """
    if total_minutes_in_period <= 0:
        return "Error: total_minutes_in_period must be greater than 0."
    if downtime_minutes < 0:
        return "Error: downtime_minutes cannot be negative."
    if downtime_minutes > total_minutes_in_period:
        return "Error: downtime_minutes cannot exceed total_minutes_in_period."

    uptime = total_minutes_in_period - downtime_minutes
    availability_pct = (uptime / total_minutes_in_period) * 100

    # SLA targets by service type (simplified — based on SDC framework)
    sla_name_lower = service_name.lower()
    if any(kw in sla_name_lower for kw in ["payment", "checkout", "auth", "authentication", "core api", "database"]):
        sla_target = 99.95
        tier = "Critical (P1-class services)"
    elif any(kw in sla_name_lower for kw in ["portal", "api", "platform", "kubernetes"]):
        sla_target = 99.9
        tier = "High (P2-class services)"
    elif any(kw in sla_name_lower for kw in ["email", "notification", "webhook", "search"]):
        sla_target = 99.5
        tier = "Standard"
    elif any(kw in sla_name_lower for kw in ["report", "analytics", "internal", "hr"]):
        sla_target = 99.0
        tier = "Internal / Low-criticality"
    else:
        sla_target = 99.9
        tier = "Standard (defaulting to 99.9% — verify actual SLA contract)"

    sla_allowance_min = total_minutes_in_period * (1 - sla_target / 100)
    breach = availability_pct < sla_target
    breach_excess_min = downtime_minutes - sla_allowance_min if breach else 0

    status_icon = "✗ BREACH" if breach else "✓ MET"

    return (
        f"Availability Report: {service_name}\n"
        f"\nPeriod: {total_minutes_in_period:,} minutes "
        f"({total_minutes_in_period // 1440} days {(total_minutes_in_period % 1440) // 60}h)\n"
        f"Downtime: {downtime_minutes} minutes\n"
        f"Uptime: {uptime:,} minutes\n"
        f"\nAvailability: {availability_pct:.4f}%\n"
        f"SLA Target: {sla_target}% ({tier})\n"
        f"SLA allowance: {sla_allowance_min:.1f} minutes/period\n"
        f"\nResult: {status_icon}\n"
        + (
            f"Breach excess: {breach_excess_min:.1f} minutes beyond SLA allowance\n"
            f"Action required: SDM notification, breach report, penalty calculation"
            if breach else
            f"Margin to SLA: {(sla_allowance_min - downtime_minutes):.1f} minutes remaining"
        )
    )


@tool
def calculate_sla_credit(
    service_name: str,
    breach_downtime_minutes: int,
    sla_allowance_minutes: float,
    customer_hourly_rate_gbp: float,
) -> str:
    """Calculate the SLA credit/penalty owed to a customer for an availability
    breach, based on SDC's standard penalty clause. Use this when a breach is
    confirmed and credit needs to be calculated for customer communication.

    SDC standard penalty: credit = (excess_downtime_hours) × hourly_rate × 3

    Args:
        service_name: Name of the breached service.
        breach_downtime_minutes: Total downtime minutes in the breach period.
        sla_allowance_minutes: SLA-permitted downtime minutes for the period
            (e.g. 43.8 min for 99.9% monthly SLA on a 30-day month).
        customer_hourly_rate_gbp: Customer's contracted hourly service rate in GBP.

    Returns the credit amount and recommended communication approach.
    """
    if breach_downtime_minutes <= sla_allowance_minutes:
        return (
            f"No credit owed for {service_name}.\n"
            f"Downtime ({breach_downtime_minutes:.1f} min) is within SLA "
            f"allowance ({sla_allowance_minutes:.1f} min)."
        )

    excess_min = breach_downtime_minutes - sla_allowance_minutes
    excess_hours = excess_min / 60
    credit = excess_hours * customer_hourly_rate_gbp * 3  # SDC contract multiplier

    severity = (
        "CRITICAL — consecutive month breach may trigger contract review"
        if excess_min > 120 else
        "HIGH — significant breach requiring formal apology"
        if excess_min > 30 else
        "MODERATE — standard credit application"
    )

    return (
        f"SLA Credit Calculation: {service_name}\n"
        f"\nDowntime in period: {breach_downtime_minutes:.1f} minutes\n"
        f"SLA allowance: {sla_allowance_minutes:.1f} minutes\n"
        f"Excess beyond SLA: {excess_min:.1f} minutes ({excess_hours:.2f} hours)\n"
        f"\nCustomer hourly rate: £{customer_hourly_rate_gbp:,.2f}\n"
        f"Penalty multiplier: ×3 (SDC standard contract clause)\n"
        f"Credit amount: £{credit:,.2f}\n"
        f"\nSeverity: {severity}\n"
        f"\nRequired actions:\n"
        f"  1. SDM approves credit within 2 business days\n"
        f"  2. Formal written apology to customer\n"
        f"  3. Root cause summary provided (Problem Record reference)\n"
        f"  4. Improvement action plan with timeline\n"
        f"  {'5. Schedule contract review meeting' if excess_min > 120 else ''}"
    )


@tool
def sla_breach_warning(priority: str, elapsed_minutes: int) -> str:
    """Determine the current SLA breach risk level based on priority and how
    long the incident has been open. Use this during active incident management
    to trigger the right escalation actions at the right time.

    SDC escalation thresholds: warn at 50%, alert at 75%, escalate at 90%.

    Args:
        priority: Incident priority — 'P1', 'P2', 'P3', or 'P4'.
        elapsed_minutes: Minutes since the incident was first acknowledged.

    Returns the current SLA status, percentage elapsed, and required actions.
    """
    resolution_minutes = {"P1": 60, "P2": 240, "P3": 480, "P4": 4320}
    p = priority.upper()

    if p not in resolution_minutes:
        return f"Unknown priority '{priority}'. Use P1, P2, P3, or P4."

    sla_minutes = resolution_minutes[p]
    pct_elapsed = (elapsed_minutes / sla_minutes) * 100
    remaining = sla_minutes - elapsed_minutes

    if pct_elapsed >= 100:
        status = "🔴 SLA BREACHED"
        urgency = "CRITICAL"
        actions = [
            "Notify SDM immediately — breach report required",
            "Prepare customer communication",
            "Initiate penalty calculation",
            "Escalate to executive sponsor if P1",
            "Document breach cause in incident record",
        ]
    elif pct_elapsed >= 90:
        status = "🔴 SLA CRITICAL (90%+ elapsed)"
        urgency = "CRITICAL"
        actions = [
            "Escalate to Service Delivery Manager NOW",
            "Prepare customer breach notification (send if not resolved in 5 min)",
            "All hands on deck — every available resource on resolution",
        ]
    elif pct_elapsed >= 75:
        status = "🟠 SLA WARNING (75%+ elapsed)"
        urgency = "HIGH"
        actions = [
            "Alert Team Lead immediately",
            "Update customer with revised ETA",
            "Confirm resolver group is actively working",
            "Remove all blockers",
        ]
    elif pct_elapsed >= 50:
        status = "🟡 SLA WATCH (50%+ elapsed)"
        urgency = "MEDIUM"
        actions = [
            "Automated warning sent to resolver group",
            "Team Lead awareness required",
            "Confirm resolution plan is in place",
        ]
    else:
        status = "🟢 SLA HEALTHY"
        urgency = "LOW"
        actions = [
            "Continue normal resolution process",
            f"Next review at 50% threshold ({int(sla_minutes * 0.5)} minutes)",
        ]

    remaining_str = (
        f"{abs(remaining)} minutes ago (BREACHED)" if remaining < 0
        else f"{remaining} minutes remaining"
    )

    actions_str = "\n".join(f"  {i+1}. {a}" for i, a in enumerate(actions))

    return (
        f"SLA Status: {p} Incident\n"
        f"\nElapsed: {elapsed_minutes} minutes of {sla_minutes}-minute SLA\n"
        f"Percentage used: {pct_elapsed:.1f}%\n"
        f"Time remaining: {remaining_str}\n"
        f"\nStatus: {status}\n"
        f"Urgency: {urgency}\n"
        f"\nRequired actions:\n{actions_str}"
    )


def get_sla_tools() -> list:
    """Return the full tool list for the SLA Monitoring Agent."""
    return make_rag_tools("sla") + [
        calculate_availability,
        calculate_sla_credit,
        sla_breach_warning,
    ]
