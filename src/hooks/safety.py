import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

_frozen_cache: set[str] | None = None

HIGH_RISK_ACTION_PATTERNS = re.compile(
    r"\b(admin|sudo|privilege|root|bypass|override|impersonate|escalate_privilege)\b",
    re.IGNORECASE,
)

PII_PATTERNS = [
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "SSN"),
    (re.compile(r"\b(?:password|passwd)\s*[=:]\s*\S+", re.IGNORECASE), "plaintext password"),
    (re.compile(r"\b4[0-9]{12}(?:[0-9]{3})?\b|\b5[1-5][0-9]{14}\b"), "payment card number"),
    (re.compile(r"\b\d{3}-\d{3}-\d{4}\b"), "phone number in description"),
]


def _load_frozen() -> set[str]:
    global _frozen_cache
    if _frozen_cache is None:
        data = json.loads((DATA_DIR / "frozen_accounts.json").read_text())
        _frozen_cache = {a["user_id"] for a in data["frozen_accounts"]}
        _frozen_cache |= {a["email"] for a in data["frozen_accounts"]}
    return _frozen_cache


class HookDecision:
    def __init__(self, allowed: bool, reason_code: str | None = None, reason: str | None = None):
        self.allowed = allowed
        self.reason_code = reason_code
        self.reason = reason

    def to_tool_error(self) -> dict:
        return {
            "isError": True,
            "reason_code": self.reason_code,
            "guidance": self.reason,
        }


def pre_tool_use(tool_name: str, tool_input: dict, submitter_id: str | None = None) -> HookDecision:
    """
    Hard-stop hook that runs before any write/action tool executes.

    Checks (in order):
    1. Frozen account — blocks any action targeting a suspended/terminated user
    2. PII in content — blocks ticket creation containing sensitive personal data
    3. High-risk action patterns — blocks execute_resolution with privilege-related actions
    """
    frozen = _load_frozen()

    # --- Frozen account check ---
    if tool_name in ("assign_to_team", "execute_resolution", "create_ticket"):
        targets = set()
        if submitter_id:
            targets.add(submitter_id)
        for field in ("submitter_id", "user_id", "employee_id"):
            if field in tool_input:
                targets.add(tool_input[field])

        for target in targets:
            if target in frozen:
                return HookDecision(
                    allowed=False,
                    reason_code="FROZEN_ACCOUNT",
                    reason=(
                        f"Account '{target}' is suspended or terminated. "
                        "No actions can be taken on behalf of or targeting this account. "
                        "If this is an error, contact HR and Security."
                    ),
                )

    # --- PII in ticket description ---
    if tool_name == "create_ticket":
        content = tool_input.get("description", "") + " " + tool_input.get("title", "")
        for pattern, label in PII_PATTERNS:
            if pattern.search(content):
                return HookDecision(
                    allowed=False,
                    reason_code="PII_DETECTED",
                    reason=(
                        f"Ticket content contains {label}. "
                        "Remove all sensitive personal data before creating the ticket. "
                        "Tickets are stored in the audit log and must not contain PII."
                    ),
                )

    # --- High-risk auto-resolution actions ---
    if tool_name == "execute_resolution":
        action = tool_input.get("action", "")
        if HIGH_RISK_ACTION_PATTERNS.search(action):
            return HookDecision(
                allowed=False,
                reason_code="HIGH_RISK_ACTION",
                reason=(
                    f"Action '{action}' contains a high-risk keyword and cannot be auto-executed. "
                    "Route to Security Operations or IAM team for human review."
                ),
            )

    return HookDecision(allowed=True)
