"""Domain tools for the Change Management Agent.

Covers the three operations most prone to error or ambiguity:
checking freeze windows, classifying change type, and finding the
next available CAB meeting — all derived from the SDC change runbook.
"""

from datetime import date, datetime, timedelta
import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)
from .rag_tools import make_rag_tools


@tool
def check_freeze_window(date_iso: str) -> str:
    """Check whether a specific date falls within an SDC change freeze window.
    Use this before scheduling any change to confirm it is permitted.

    Args:
        date_iso: The proposed implementation date in ISO format: 'YYYY-MM-DD'.

    Returns whether the date is frozen, the freeze reason, and what change
    types (if any) are still permitted.
    """
    try:
        target = date.fromisoformat(date_iso.strip())
    except ValueError:
        return f"Invalid date format '{date_iso}'. Use YYYY-MM-DD, e.g. 2025-04-28."

    year = target.year

    # Compute freeze windows for the target year
    def _last_n_business_days(year: int, month: int, n: int) -> tuple[date, date]:
        """Return (start, end) of last N business days in given month."""
        # Last day of month
        if month == 12:
            last = date(year, 12, 31)
        else:
            last = date(year, month + 1, 1) - timedelta(days=1)
        end = last
        # Walk back to find N business days
        count, cur = 0, last
        while count < n:
            if cur.weekday() < 5:  # Mon–Fri
                count += 1
                if count == n:
                    start = cur
            cur -= timedelta(days=1)
        return start, end

    q1_start, q1_end = _last_n_business_days(year, 3, 5)
    q2_start, q2_end = _last_n_business_days(year, 6, 5)
    q3_start, q3_end = _last_n_business_days(year, 9, 5)
    q4_start, q4_end = _last_n_business_days(year, 12, 10)
    xmas_start = date(year, 12, 24)
    xmas_end = date(year + 1, 1, 2)

    freeze_periods = [
        (q1_start, q1_end, "Q1 Quarter-End freeze (last 5 business days of March)"),
        (q2_start, q2_end, "Q2 Quarter-End freeze (last 5 business days of June)"),
        (q3_start, q3_end, "Q3 Quarter-End freeze (last 5 business days of September)"),
        (q4_start, q4_end, "Q4/Year-End freeze (last 10 business days of December)"),
        (xmas_start, xmas_end, "Christmas/New Year holiday freeze"),
    ]

    for start, end, reason in freeze_periods:
        if start <= target <= end:
            stricter = "Q4" in reason or "Year-End" in reason or "Christmas" in reason
            approvers = "SDM + CTO + CISO" if stricter else "SDM"
            logger.info(
                "sdc.tool.check_freeze_window date=%s frozen=True reason=%s approvers=%s",
                date_iso, reason, approvers,
            )
            return (
                f"⛔ FREEZE WINDOW — {date_iso} is frozen.\n"
                f"Reason: {reason}\n"
                f"Freeze period: {start.isoformat()} to {end.isoformat()}\n"
                f"\nPermitted during this freeze:\n"
                f"  • Emergency Changes only\n"
                f"  • Approval required: {approvers}\n"
                f"  • Must have specific financial or regulatory justification\n"
                f"\nStandard and Normal changes are NOT permitted."
            )

    logger.info("sdc.tool.check_freeze_window date=%s frozen=False", date_iso)
    return (
        f"✓ {date_iso} is NOT in a freeze window — changes are permitted.\n"
        f"\nFreeze windows for {year}:\n"
        f"  Q1: {q1_start.isoformat()} – {q1_end.isoformat()}\n"
        f"  Q2: {q2_start.isoformat()} – {q2_end.isoformat()}\n"
        f"  Q3: {q3_start.isoformat()} – {q3_end.isoformat()}\n"
        f"  Q4: {q4_start.isoformat()} – {q4_end.isoformat()}\n"
        f"  Christmas: {xmas_start.isoformat()} – {xmas_end.isoformat()}"
    )


@tool
def classify_change_type(
    description: str,
    services_affected_count: int,
    tested_in_staging: bool,
    involves_data_changes: bool,
    is_urgent_incident_fix: bool,
) -> str:
    """Classify a proposed change into the correct SDC change type: Standard,
    Normal Minor, Normal Major, or Emergency. Use this to determine which
    approval process and lead time applies.

    Args:
        description: Brief description of what the change does.
        services_affected_count: Number of production services affected.
        tested_in_staging: Whether the change has been fully tested in staging.
        involves_data_changes: Whether the change modifies or migrates data.
        is_urgent_incident_fix: Whether this is required to resolve an active P1/P2.

    Returns the change type, required approvals, minimum lead time, and key
    documentation requirements.
    """
    # Emergency: active incident requires it
    if is_urgent_incident_fix:
        return (
            "Change Type: EMERGENCY\n"
            "\nTrigger: Active P1/P2 incident or critical security vulnerability\n"
            "\nApproval process:\n"
            "  1. Contact Change Manager via emergency phone line\n"
            "  2. ECAB convened within 2 hours (SDM + Technical Lead + Security Lead)\n"
            "  3. Majority vote required\n"
            "  4. Implementation can begin immediately after ECAB approval\n"
            "\nPost-implementation (mandatory within 24 hours):\n"
            "  • Full RFC created retrospectively\n"
            "  • PIR mandatory\n"
            "  • Review: was this genuinely an emergency?"
        )

    # Risk scoring
    risk_score = 0
    risk_factors = []
    if services_affected_count > 3:
        risk_score += 2
        risk_factors.append(f"{services_affected_count} services affected (high blast radius)")
    elif services_affected_count > 1:
        risk_score += 1
        risk_factors.append(f"{services_affected_count} services affected")
    if involves_data_changes:
        risk_score += 2
        risk_factors.append("Data migration/modification (harder to roll back)")
    if not tested_in_staging:
        risk_score += 2
        risk_factors.append("Not tested in staging (higher risk)")

    # Standard: pre-approved catalogue items
    standard_keywords = [
        "ssl certificate renewal", "certificate renew", "dns a-record",
        "os patch", "security patch", "monitoring threshold", "user role",
        "password reset", "firewall rule standard",
    ]
    desc_lower = description.lower()
    is_standard_candidate = any(kw in desc_lower for kw in standard_keywords)

    if is_standard_candidate and risk_score == 0:
        return (
            "Change Type: STANDARD\n"
            "\nThis matches a pre-approved standard change catalogue entry.\n"
            "\nRequirements:\n"
            "  • Log in ITSM (audit trail required)\n"
            "  • Follow the exact catalogue procedure — any deviation requires reclassification\n"
            "  • No CAB approval needed\n"
            "  • Pre-approved by catalogue entry approver\n"
            "\nLead time: None (can implement immediately per catalogue schedule)\n"
            "\nVerify: confirm which catalogue entry (SC-001 to SC-005) applies."
        )

    if risk_score <= 1:
        change_type = "NORMAL MINOR"
        lead_time = "72 hours minimum notice"
        cab = "Tuesday CAB (14:00 UTC) — submit 48 hours before"
        docs = [
            "RFC form (all mandatory fields)",
            "Risk assessment (Low/Medium rating expected)",
            "Rollback plan",
            "Stakeholder sign-off",
        ]
    else:
        change_type = "NORMAL MAJOR"
        lead_time = "5 business days minimum for CAB submission"
        cab = "Thursday CAB (10:00 UTC) — submit 48 hours before"
        docs = [
            "RFC form (all mandatory fields)",
            "Detailed risk assessment",
            "Full test evidence from staging",
            "Rollback plan (tested in staging)",
            "Communication plan",
            "Business owner + Technical lead sign-off",
            "CMDB impact assessment",
        ]

    risk_str = "\n".join(f"  • {f}" for f in risk_factors) if risk_factors else "  • Low risk factors identified"
    docs_str = "\n".join(f"  • {d}" for d in docs)

    logger.info(
        "sdc.tool.classify_change_type type=%s risk_score=%d services=%d staged=%s data=%s urgent=%s",
        change_type, risk_score, services_affected_count,
        tested_in_staging, involves_data_changes, is_urgent_incident_fix,
    )
    return (
        f"Change Type: {change_type}\n"
        f"\nRisk factors:\n{risk_str}\n"
        f"\nApproval: {cab}\n"
        f"Lead time: {lead_time}\n"
        f"\nRequired documentation:\n{docs_str}\n"
        f"\nPost-implementation: PIR due within 5 business days."
    )


@tool
def next_cab_meeting(after_date_iso: str, change_type: str = "minor") -> str:
    """Find the next available CAB meeting after a given date, and calculate
    the submission deadline. Use this to help plan change scheduling.

    Args:
        after_date_iso: Date to search from, in 'YYYY-MM-DD' format.
        change_type: 'minor' (Tuesday CAB) or 'major' (Thursday CAB).
            Default is 'minor'. Both are checked if unspecified.

    Returns the next CAB date, time, submission deadline, and any freeze conflicts.
    """
    try:
        start = date.fromisoformat(after_date_iso.strip())
    except ValueError:
        return f"Invalid date '{after_date_iso}'. Use YYYY-MM-DD."

    cab_day = 1 if change_type.lower() == "minor" else 3  # Tuesday=1, Thursday=3

    # Find next occurrence of the target weekday
    days_ahead = (cab_day - start.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7  # If today is CAB day, use next week's
    next_cab = start + timedelta(days=days_ahead)

    cab_time = "14:00 UTC" if change_type.lower() == "minor" else "10:00 UTC"
    submission_deadline = next_cab - timedelta(days=2)

    # Check if next_cab is in a freeze window (reuse logic inline)
    year = next_cab.year
    q4_dec_start = next_cab.replace(month=12, day=19)  # approximate
    xmas_start = date(year, 12, 24)
    xmas_end = date(year + 1, 1, 2)
    freeze_note = ""
    if xmas_start <= next_cab <= xmas_end:
        freeze_note = "\n⛔ NOTE: This CAB date falls in Christmas freeze — Emergency Changes only."

    logger.info(
        "sdc.tool.next_cab_meeting after=%s type=%s next_cab=%s deadline=%s frozen=%s",
        after_date_iso, change_type, next_cab.isoformat(),
        submission_deadline.isoformat(), bool(freeze_note),
    )
    return (
        f"Next {change_type.title()} CAB meeting:\n"
        f"  Date: {next_cab.strftime('%A %d %B %Y')} at {cab_time}\n"
        f"  Submission deadline: {submission_deadline.strftime('%A %d %B %Y')} (48 hours before)\n"
        f"{freeze_note}"
        f"\nTo ensure your change is reviewed:\n"
        f"  1. Submit RFC in ITSM by {submission_deadline.strftime('%d %b %Y')}\n"
        f"  2. Complete all mandatory fields and attach documentation\n"
        f"  3. Change Coordinator will validate within 1 business day of submission"
    )


def get_change_tools() -> list:
    """Return the full tool list for the Change Management Agent."""
    return make_rag_tools("change") + [
        check_freeze_window,
        classify_change_type,
        next_cab_meeting,
    ]
