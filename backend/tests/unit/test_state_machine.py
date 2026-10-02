import pytest

from app.errors import InvalidTransition
from app.models import Status
from app.state_machine import ALLOWED, assert_transition, can_add_evidence

HAPPY_PATH = [
    (Status.opened, Status.evidence_submitted),
    (Status.evidence_submitted, Status.under_review),
    (Status.under_review, Status.resolved),
]


@pytest.mark.parametrize("current,target", HAPPY_PATH)
def test_allowed_transitions_pass(current, target):
    assert_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [(c, t) for c in Status for t in Status if t not in ALLOWED[c]],
)
def test_every_other_transition_is_rejected(current, target):
    with pytest.raises(InvalidTransition):
        assert_transition(current, target)


def test_resolved_is_terminal():
    assert ALLOWED[Status.resolved] == set()


def test_accepts_raw_strings_from_the_db():
    assert_transition("opened", Status.evidence_submitted)


def test_evidence_window():
    assert can_add_evidence(Status.opened)
    assert can_add_evidence(Status.evidence_submitted)
    assert not can_add_evidence(Status.under_review)
    assert not can_add_evidence(Status.resolved)
