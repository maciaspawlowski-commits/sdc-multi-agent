"""Domain tools for the Problem Management Agent.

Covers: determining whether a problem record is warranted, recommending
the right RCA technique, and generating a correctly formatted KEDB entry.
"""

from langchain_core.tools import tool
from .rag_tools import make_rag_tools


@tool
def check_problem_trigger(
    incident_count: int,
    days_window: int,
    highest_priority: str,
    same_root_cause: bool,
) -> str:
    """Determine whether the given incident pattern meets SDC's threshold for
    creating a Problem Record. Use this when a user describes recurring incidents
    and asks whether a problem record should be opened.

    Args:
        incident_count: Number of incidents with the same apparent cause.
        days_window: Time window in calendar days over which these occurred.
        highest_priority: Highest priority seen — one of 'P1', 'P2', 'P3', 'P4'.
        same_root_cause: Whether the incidents share a confirmed or suspected root cause.

    Returns whether to create a problem record, the trigger that applies, and
    the SLA for creating the record.
    """
    p = highest_priority.upper()
    triggers = []
    sla_days = None

    # Reactive trigger: 3+ same-cause incidents in 30 days
    if incident_count >= 3 and days_window <= 30 and same_root_cause:
        triggers.append("Reactive: 3+ incidents with same cause within 30 calendar days")
        sla_days = 2

    # Any P1 post-mortem with unresolved root cause
    if p == "P1":
        triggers.append("Reactive: P1 incident — problem record mandatory from post-mortem")
        sla_days = 1

    # P2 recurring within 30 days
    if p == "P2" and incident_count >= 2 and days_window <= 30:
        triggers.append("Reactive: P2 occurring for the second time within 30 days (same root cause)")
        sla_days = sla_days or 2

    # Workaround-only resolution
    if incident_count >= 1 and p in ("P1", "P2"):
        triggers.append("Reactive: Incident resolved by workaround only — permanent fix not applied")
        sla_days = sla_days or 2

    if not triggers:
        return (
            f"Problem record NOT required based on current data:\n"
            f"  Incidents: {incident_count} over {days_window} days, highest priority: {p}\n"
            f"\nThresholds not yet met:\n"
            f"  • 3+ same-cause incidents within 30 days (have {incident_count})\n"
            f"  • P1 incident (have {p})\n"
            f"  • P2 recurring ×2 within 30 days\n"
            f"\nContinue monitoring. Consider proactive problem record if pattern continues."
        )

    trigger_str = "\n".join(f"  ✓ {t}" for t in triggers)
    priority_label = {
        1: "Critical (recurring P1 — immediate investigation)",
        2: "High (recurring P2 — significant business impact)",
        3: "Medium (recurring P3 — workaround adequate)",
        4: "Low (occasional P3/P4 — minimal impact)",
    }.get(["P1", "P2", "P3", "P4"].index(p) + 1 if p in ["P1","P2","P3","P4"] else 4, "Medium")

    return (
        f"⚠ PROBLEM RECORD REQUIRED\n"
        f"\nTriggers met:\n{trigger_str}\n"
        f"\nProblem priority: {priority_label}\n"
        f"Create problem record within: {sla_days} business day(s)\n"
        f"\nNext steps:\n"
        f"  1. Create PRB-{{}}-NNNN in ITSM\n"
        f"  2. Link all related incident IDs (mandatory)\n"
        f"  3. Document affected services and CIs from CMDB\n"
        f"  4. Assign Problem Manager (typically L3 team lead)\n"
        f"  5. Begin root cause investigation"
    )


@tool
def suggest_rca_method(
    incident_count: int,
    is_change_related: bool,
    is_vendor_related: bool,
    multiple_contributing_factors: bool,
) -> str:
    """Recommend the most appropriate Root Cause Analysis (RCA) technique
    based on the characteristics of the problem. Use this when starting
    a problem investigation to choose the right methodology.

    Args:
        incident_count: Number of linked incidents.
        is_change_related: Whether the problem appeared after a recent change.
        is_vendor_related: Whether a third-party vendor component is involved.
        multiple_contributing_factors: Whether multiple independent causes are suspected.

    Returns the recommended technique with rationale, process steps, and output format.
    """
    if is_change_related:
        return (
            "Recommended RCA Method: CHANGE ANALYSIS\n"
            "\nRationale: The problem appeared after a change — Change Analysis "
            "is the most direct path to root cause.\n"
            "\nProcess:\n"
            "  1. List all changes deployed in the 72 hours before first incident\n"
            "  2. For each change: assess whether it could cause the observed symptoms\n"
            "  3. Test rollback of suspected change in non-production if possible\n"
            "  4. Compare pre-change and post-change monitoring data (Dash0)\n"
            "  5. Check change test coverage: was this failure mode tested in staging?\n"
            "\nOutput: Change analysis table in Problem Record; link RFC to PRB\n"
            "\nAlso consider: Timeline Analysis as a complementary technique "
            "to establish exact sequence of events."
        )

    if multiple_contributing_factors:
        return (
            "Recommended RCA Method: FISHBONE (ISHIKAWA) DIAGRAM\n"
            "\nRationale: Multiple contributing factors suspected — Fishbone "
            "prevents tunnel vision on the most obvious cause.\n"
            "\nCategories to investigate:\n"
            "  • People: Skills gaps, staffing levels, communication failure\n"
            "  • Process: Missing procedures, testing gaps, approval gaps\n"
            "  • Technology: Hardware failure, software bugs, config errors, capacity limits\n"
            "  • Environment: Cloud provider issues, third-party dependencies\n"
            "  • Data: Incorrect config data, stale CMDB, missing documentation\n"
            "\nProcess: Draw central spine with problem at head; add branches "
            "for each category; brainstorm causes; identify evidence-supported causes.\n"
            "\nOutput: Fishbone diagram attached to Problem Record"
        )

    if incident_count >= 3:
        return (
            "Recommended RCA Method: FAULT TREE ANALYSIS (FTA)\n"
            "\nRationale: Multiple incidents and potential independent failure modes "
            "— FTA maps all combinations that lead to the top-level failure.\n"
            "\nProcess:\n"
            "  1. Start from the top-level failure event\n"
            "  2. Work backwards using AND gates (all inputs required) "
            "and OR gates (any input sufficient)\n"
            "  3. Build tree until reaching basic events\n"
            "  4. Identify minimal cut sets — fewest failures causing the top event\n"
            "  5. Prioritise fixing the smallest cut sets first\n"
            "\nOutput: Tree diagram saved to Problem Record; minimal cut sets listed\n"
            "\nAlso useful: Timeline Analysis to confirm the sequence of events."
        )

    if is_vendor_related:
        return (
            "Recommended RCA Method: 5-WHYS + VENDOR ENGAGEMENT\n"
            "\nRationale: Vendor component involved — start with 5-Whys to "
            "narrow scope, then engage vendor TAM with specific evidence.\n"
            "\nProcess:\n"
            "  1. Apply 5-Whys to identify exactly where the vendor boundary is\n"
            "  2. Document: exact symptoms, timestamps, error codes, versions\n"
            "  3. Check vendor support portal for known issues\n"
            "  4. Engage vendor TAM with evidence package\n"
            "  5. Track vendor fix ETA in KEDB\n"
            "\nEscalation: If vendor refuses to acknowledge — escalate to CTO\n"
            "\nOutput: 5-Whys chain + vendor reference number in Problem Record"
        )

    # Default: single factor, clear chain
    return (
        "Recommended RCA Method: 5-WHYS\n"
        "\nRationale: Single-factor failure with a likely clear cause-and-effect "
        "chain — 5-Whys is efficient and sufficient.\n"
        "\nProcess:\n"
        "  1. State the problem clearly as the starting point\n"
        "  2. Ask 'Why did this happen?' — document the answer\n"
        "  3. Ask 'Why?' of the answer — repeat until reaching a systemic cause\n"
        "  4. The final answer typically reveals a process, training, or design gap\n"
        "  5. Confirm root cause is reproducible or clearly evidenced\n"
        "\nExample structure:\n"
        "  Why did [service] fail? → [symptom]\n"
        "  Why [symptom]? → [cause-1]\n"
        "  Why [cause-1]? → [cause-2]\n"
        "  Why [cause-2]? → [root cause — process/design gap]\n"
        "\nOutput: 5-Whys chain documented in Problem Record"
    )


@tool
def format_kedb_entry(
    problem_id: str,
    affected_services: str,
    symptoms: str,
    root_cause: str,
    workaround: str,
    fix_description: str,
    fix_eta: str,
) -> str:
    """Generate a correctly formatted Known Error Database (KEDB) entry for a
    confirmed problem. Use this when root cause has been identified and the
    problem is being declared a Known Error.

    Args:
        problem_id: Problem Record ID, e.g. 'PRB-20250427-0001'.
        affected_services: Comma-separated list of affected services.
        symptoms: Observable symptoms — what users/monitoring see.
        root_cause: Confirmed root cause description (technical failure mechanism).
        workaround: Step-by-step workaround instructions.
        fix_description: Brief description of the permanent fix planned.
        fix_eta: Target date for permanent fix, e.g. '2025-05-15'.
    """
    from datetime import date
    today = date.today().isoformat()

    # Generate a KEDB ID from problem ID
    kedb_id = "KE-" + problem_id.replace("PRB-", "").replace("-", "")[:8]

    services_list = "\n".join(f"- {s.strip()}" for s in affected_services.split(","))
    symptoms_list = "\n".join(f"- {s.strip()}" for s in symptoms.split(";"))

    return f"""KEDB Entry — {kedb_id}
{'='*50}
KEDB ID: {kedb_id}
Problem Record: {problem_id}
Status: Active
Date Created: {today}
Last Reviewed: {today}
Next Review Due: (30 days from creation)

## Affected Services
{services_list}

## Symptoms
{symptoms_list}

## Root Cause
{root_cause}

## Workaround (step-by-step)
{workaround}
Note: Review workaround validity every 30 days.

## Permanent Fix
RFC: [To be raised — link after CAB approval]
ETA: {fix_eta}
Fix description: {fix_description}
Status: Pending RFC

## History
- {today}: Created

Next actions:
1. Raise RFC for permanent fix within 10 business days
2. Notify Service Desk with workaround instructions
3. Link this Known Error to all open incidents with matching symptoms
4. Schedule 30-day review: {fix_eta}
"""


def get_problem_tools() -> list:
    """Return the full tool list for the Problem Management Agent."""
    return make_rag_tools("problem") + [
        check_problem_trigger,
        suggest_rca_method,
        format_kedb_entry,
    ]
