"""Black Friday incident simulation scenario.

Ten sequential queries that walk through a realistic Black Friday meltdown:
  1.  Payment service P1 declared
  2.  Auth service cascade failure
  3.  SLA breach risk assessment (47 min in)
  4.  Freeze-window check + change type for the hotfix
  5.  Problem record trigger check (4th recurrence)
  6.  Emergency contractor access request
  7.  SLA availability calculation + credit owed
  8.  KEDB entry for DB pool exhaustion
  9.  Emergency RFC to raise pool size
  10. P1 closure checklist + post-incident review

Each step is sent as a real message into the SDC multi-agent graph using a
shared session, so later steps can naturally reference earlier context.
"""

from typing import TypedDict


class SimStep(TypedDict):
    description: str   # short label shown in the UI progress line
    query: str         # the message sent to the agent system


def get_black_friday_steps() -> list[SimStep]:
    """Return the ordered list of Black Friday simulation steps."""
    return [
        {
            "description": "P1 declared — payment service severe degradation",
            "query": (
                "Our payment service has been showing severe degradation since 06:00 UTC. "
                "Response times are above 8 seconds and growing, requests are timing out, "
                "approximately 450,000 customers are currently affected, revenue impact is "
                "confirmed, and there is no available workaround. "
                "What priority should we assign this incident, and what is our resolution deadline?"
            ),
        },
        {
            "description": "Auth service 503 cascade — escalation required",
            "query": (
                "Update: the auth service is now also returning 503 errors, affecting around "
                "180,000 users attempting to reach checkout. The payment P1 is already open. "
                "What escalation steps and stakeholder notifications do we need to send out "
                "right now for this combined outage?"
            ),
        },
        {
            "description": "SLA breach warning — 47 minutes elapsed on the P1",
            "query": (
                "The payment P1 incident has now been open for 47 minutes. "
                "Our SLA target for critical services is 99.95% availability and we are in "
                "November — a 30-day month. "
                "What urgency level does this trigger under our SLA framework, and are we "
                "approaching a breach threshold?"
            ),
        },
        {
            "description": "Freeze window check — can we deploy the hotfix today?",
            "query": (
                "Our engineers have identified and validated a hotfix for the payment service "
                "DB connection pool issue. It has been tested in staging. "
                "Today is 29 November. Is this date inside a change freeze window? "
                "What change type should we raise for an emergency production fix of this nature?"
            ),
        },
        {
            "description": "Problem record — is a 4th recurrence enough to trigger one?",
            "query": (
                "Deeper investigation shows this is the 4th time the payment DB connection pool "
                "has failed in the past 60 days, with all incidents rated P1 or P2 and sharing "
                "the same root cause pattern. "
                "Do we meet the threshold to open a formal problem record, and which RCA "
                "method should we use to investigate?"
            ),
        },
        {
            "description": "Emergency contractor onboarding — monitoring access",
            "query": (
                "We need to bring in 3 emergency contractors to support the Black Friday incident "
                "bridge. They each need read access to the monitoring platform and the incident "
                "management system. What is the fastest approval path for emergency contractor "
                "access, and what information do we need to provide?"
            ),
        },
        {
            "description": "SLA calculation — 154 min downtime, credit owed to top customer",
            "query": (
                "The payment service has now accumulated 154 minutes of downtime this month. "
                "Our SLA target is 99.95% for critical services in a 30-day month "
                "(43,200 total minutes in the period). "
                "Calculate our actual availability percentage, confirm whether we are in breach, "
                "and calculate the credit owed to our largest customer who is billed at £500 per hour."
            ),
        },
        {
            "description": "KEDB entry — DB connection pool exhaustion under Black Friday load",
            "query": (
                "Root cause is confirmed: the payment DB connection pool was exhausted by "
                "3× normal Black Friday traffic volume, hitting the hard limit of 100 connections. "
                "No existing KEDB entry covers this. "
                "Please create a KEDB entry for: problem ID PRB-20241129-0008, "
                "affected services: Payment and Auth, "
                "symptoms: request timeouts and 503 errors under peak load, "
                "root cause: DB connection pool exhaustion at the 100-connection hard cap, "
                "workaround: restart the DB proxy service to flush stale connections, "
                "permanent fix: increase the pool size limit to 500 connections, "
                "fix ETA: 2 hours."
            ),
        },
        {
            "description": "Emergency RFC — raise DB connection pool limit to 500",
            "query": (
                "We need to raise an emergency RFC to increase the payment DB connection pool "
                "from 100 to 500 connections. The change has not been tested in staging due to "
                "time pressure, it modifies a live database configuration parameter, and it is "
                "an urgent fix for the active P1 incident. "
                "What change type is this, and what is the fastest route through the CAB "
                "approval process for an emergency change of this kind?"
            ),
        },
        {
            "description": "P1 resolved — close incident and schedule PIR",
            "query": (
                "The payment service has fully recovered. Response times are back to normal "
                "as of 08:34 UTC. Total P1 downtime was 154 minutes from first alert to "
                "confirmed recovery. "
                "What are the required steps to formally close this P1 incident, and what "
                "post-incident review process and timeline applies for a P1 of this duration "
                "and business impact?"
            ),
        },
    ]
