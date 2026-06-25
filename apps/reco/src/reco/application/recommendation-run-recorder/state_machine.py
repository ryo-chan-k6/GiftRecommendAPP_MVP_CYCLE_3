"""Run status transition rules (state machine)."""

from __future__ import annotations

from reco.domain.recommendation.run import RunStatus

from .errors import RunStateConflictError

TERMINAL_STATUSES: frozenset[RunStatus] = frozenset(
    {
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELED,
    }
)

_ALLOWED_TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    RunStatus.ACCEPTED: frozenset({RunStatus.RUNNING}),
    RunStatus.RUNNING: frozenset(
        {
            RunStatus.SUCCEEDED,
            RunStatus.FAILED,
            RunStatus.CANCELED,
        }
    ),
}


def is_terminal(status: RunStatus) -> bool:
    return status in TERMINAL_STATUSES


def validate_transition(
    current: RunStatus,
    target: RunStatus,
) -> None:
    if is_terminal(current):
        raise RunStateConflictError(
            f"cannot update terminal run_status={current.value}"
        )

    allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise RunStateConflictError(
            f"invalid transition from {current.value} to {target.value}"
        )
