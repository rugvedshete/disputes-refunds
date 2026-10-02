from .errors import InvalidTransition
from .models import Status

# opened -> evidence_submitted -> under_review -> resolved (refund | reject)
ALLOWED: dict[Status, set[Status]] = {
    Status.opened: {Status.evidence_submitted},
    Status.evidence_submitted: {Status.under_review},
    Status.under_review: {Status.resolved},
    Status.resolved: set(),
}

# Customers may keep adding evidence until an agent picks the case up.
EVIDENCE_OPEN = {Status.opened, Status.evidence_submitted}


def assert_transition(current: Status | str, target: Status) -> None:
    cur = Status(current)
    if target not in ALLOWED[cur]:
        raise InvalidTransition(f"Cannot move a dispute from '{cur.value}' to '{target.value}'")


def can_add_evidence(current: Status | str) -> bool:
    return Status(current) in EVIDENCE_OPEN
