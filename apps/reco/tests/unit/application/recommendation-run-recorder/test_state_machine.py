"""MOD-RECO-002 state machine unit tests (module spec §14 No.9)."""

from __future__ import annotations

import pytest

from reco.application.recommendation_run_recorder import RunStateConflictError
from reco.application.recommendation_run_recorder.state_machine import (
    is_terminal,
    validate_transition,
)
from reco.domain.recommendation.run import RunStatus


@pytest.mark.parametrize(
    "status",
    [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED],
)
def test_is_terminal_returns_true_for_terminal_statuses(status: RunStatus) -> None:
    assert is_terminal(status) is True


@pytest.mark.parametrize(
    "status",
    [RunStatus.ACCEPTED, RunStatus.RUNNING],
)
def test_is_terminal_returns_false_for_non_terminal_statuses(status: RunStatus) -> None:
    assert is_terminal(status) is False


def test_accepted_to_running_is_allowed() -> None:
    validate_transition(RunStatus.ACCEPTED, RunStatus.RUNNING)


@pytest.mark.parametrize(
    "target",
    [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED],
)
def test_running_to_terminal_is_allowed(target: RunStatus) -> None:
    validate_transition(RunStatus.RUNNING, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (RunStatus.ACCEPTED, RunStatus.SUCCEEDED),
        (RunStatus.ACCEPTED, RunStatus.FAILED),
        (RunStatus.ACCEPTED, RunStatus.CANCELED),
        (RunStatus.RUNNING, RunStatus.ACCEPTED),
        (RunStatus.RUNNING, RunStatus.RUNNING),
    ],
)
def test_invalid_transition_raises_grs_rec_201(
    current: RunStatus,
    target: RunStatus,
) -> None:
    with pytest.raises(RunStateConflictError) as exc_info:
        validate_transition(current, target)

    assert exc_info.value.error_code == "GRS-REC-201"


@pytest.mark.parametrize(
    "terminal",
    [RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELED],
)
def test_terminal_status_rejects_any_update(terminal: RunStatus) -> None:
    with pytest.raises(RunStateConflictError) as exc_info:
        validate_transition(terminal, RunStatus.RUNNING)

    assert exc_info.value.error_code == "GRS-REC-201"
    assert "terminal" in exc_info.value.message
