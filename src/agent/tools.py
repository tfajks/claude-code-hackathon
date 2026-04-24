import json
import re
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

_ticket_store: list[dict] = []


def _load(filename: str):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def lookup_kb(query: str) -> dict:
    articles = _load("kb.json")
    query_lower = query.lower()
    scored = []
    for article in articles:
        score = sum(
            1 for kw in article.get("keywords", [])
            if kw.lower() in query_lower or query_lower in kw.lower()
        )
        if score > 0 or query_lower in article["title"].lower():
            scored.append((score, article))
    scored.sort(key=lambda x: x[0], reverse=True)
    results = [
        {
            "id": a["id"],
            "title": a["title"],
            "resolution_steps": a["resolution_steps"],
            "auto_resolvable": a["auto_resolvable"],
            "resolution_action": a.get("resolution_action"),
        }
        for _, a in scored[:3]
    ]
    return {"isError": False, "result": results}


def get_user_history(user_id: str) -> dict:
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b", user_id):
        return {
            "isError": True,
            "reason_code": "PII_IN_INPUT",
            "guidance": "user_id appears to contain an SSN. Use employee ID or email instead.",
        }
    history = _load("user_history.json")
    tickets = [t for t in history if t.get("user_id") == user_id][-5:]
    return {
        "isError": False,
        "result": {"user_id": user_id, "recent_tickets": tickets, "ticket_count_last_30d": len(tickets)},
    }


def create_ticket(title: str, description: str, submitter_id: str, priority: str, category: str) -> dict:
    if priority not in ("P1", "P2", "P3", "P4"):
        return {
            "isError": True,
            "reason_code": "INVALID_PRIORITY",
            "guidance": "priority must be one of P1, P2, P3, P4.",
        }
    pii_checks = [
        (r"\b\d{3}-\d{2}-\d{4}\b", "SSN"),
        (r"password\s*[=:]\s*\S+", "plaintext password"),
        (r"\b(?:credit|debit)\s*card\b.*\d{4}", "payment card number"),
    ]
    for pattern, label in pii_checks:
        if re.search(pattern, description, re.IGNORECASE):
            return {
                "isError": True,
                "reason_code": "PII_DETECTED",
                "guidance": f"Description contains {label}. Remove all sensitive data before creating the ticket.",
            }
    ticket_id = f"TKT-{str(uuid.uuid4())[:6].upper()}"
    _ticket_store.append(
        {
            "id": ticket_id,
            "title": title[:100],
            "description": description,
            "submitter_id": submitter_id,
            "priority": priority,
            "category": category,
            "status": "open",
            "created_at": datetime.now().isoformat(),
        }
    )
    return {"isError": False, "result": {"ticket_id": ticket_id, "status": "created"}}


def assign_to_team(ticket_id: str, team_id: str, priority: str) -> dict:
    teams = {t["id"]: t for t in _load("teams.json")}
    if team_id not in teams:
        return {
            "isError": True,
            "reason_code": "INVALID_TEAM",
            "guidance": f"Unknown team_id '{team_id}'. Valid values: {', '.join(teams.keys())}",
        }
    team = teams[team_id]
    sla = team["sla_hours"].get(priority, 24)
    return {
        "isError": False,
        "result": {
            "ticket_id": ticket_id,
            "assigned_to": team["name"],
            "queue": team["queue"],
            "priority": priority,
            "sla_hours": sla,
        },
    }


def execute_resolution(ticket_id: str, action: str, notify_user: bool = True) -> dict:
    allowed = ("send_sspr_link", "install_vpn_client", "provision_approved_software")
    if action not in allowed:
        return {
            "isError": True,
            "reason_code": "UNAUTHORIZED_ACTION",
            "guidance": f"'{action}' is not in the auto-resolve allowlist: {allowed}. Route to appropriate team for human review.",
        }
    messages = {
        "send_sspr_link": "Self-service password reset link sent to user's registered mobile/email.",
        "install_vpn_client": "VPN client package pushed to device via MDM.",
        "provision_approved_software": "License provisioned and installation instructions emailed to user.",
    }
    return {
        "isError": False,
        "result": {
            "ticket_id": ticket_id,
            "action": action,
            "status": "resolved",
            "message": messages[action],
            "notified": notify_user,
        },
    }


TOOL_SCHEMAS = [
    {
        "name": "lookup_kb",
        "description": (
            "Search the IT knowledge base for solutions, procedures, and self-service guides. "
            "Use for: finding resolution steps, checking if a ticket is auto-resolvable, "
            "identifying the correct team. "
            "Does NOT access live systems or modify anything. "
            "Example: lookup_kb('password reset') or lookup_kb('VPN setup')."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search terms (natural language or keywords)"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_user_history",
        "description": (
            "Retrieve a user's last 5 IT support tickets for context. "
            "Use for: spotting repeat issues, checking if a problem is new or recurring. "
            "Does NOT return passwords, PII, HR data, or other users' tickets. "
            "Pass employee ID (e.g. 'emp_10001') or work email. Never pass SSNs."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "Employee ID or work email address"}
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "create_ticket",
        "description": (
            "Create a new IT support ticket. Call this after classification is complete. "
            "Does NOT route, resolve, or notify—use assign_to_team or execute_resolution for those. "
            "IMPORTANT: Never include passwords, SSNs, or PII in description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Brief title (max 100 chars)"},
                "description": {"type": "string", "description": "Sanitized description, no PII"},
                "submitter_id": {"type": "string", "description": "Employee ID of the requestor"},
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
                "category": {"type": "string", "description": "Ticket category"},
            },
            "required": ["title", "description", "submitter_id", "priority", "category"],
        },
    },
    {
        "name": "assign_to_team",
        "description": (
            "Route an open ticket to the appropriate IT team queue. "
            "Valid team_ids: desktop, network, security, iam, email, data, exec, tier2. "
            "Does NOT notify users, modify ticket content, or resolve tickets. "
            "Will be blocked by safety hook for frozen/suspended accounts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string", "description": "Ticket ID from create_ticket"},
                "team_id": {
                    "type": "string",
                    "enum": ["desktop", "network", "security", "iam", "email", "data", "exec", "tier2"],
                },
                "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
            },
            "required": ["ticket_id", "team_id", "priority"],
        },
    },
    {
        "name": "execute_resolution",
        "description": (
            "Execute automated resolution for simple, pre-approved actions only. "
            "Allowed actions: send_sspr_link (password reset), install_vpn_client, provision_approved_software. "
            "Does NOT handle security incidents, change permissions, or act on frozen accounts. "
            "Will be blocked for: executive accounts, accounts flagged in security investigations, "
            "any action containing 'admin', 'sudo', or 'privilege'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["send_sspr_link", "install_vpn_client", "provision_approved_software"],
                },
                "notify_user": {"type": "boolean", "default": True},
            },
            "required": ["ticket_id", "action"],
        },
    },
]

TOOL_DISPATCH: dict[str, callable] = {
    "lookup_kb": lookup_kb,
    "get_user_history": get_user_history,
    "create_ticket": create_ticket,
    "assign_to_team": assign_to_team,
    "execute_resolution": execute_resolution,
}
