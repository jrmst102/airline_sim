from __future__ import annotations

from dataclasses import dataclass


SIMULATION_STATES: tuple[str, ...] = ("CREATED", "STARTED", "ENDED")
ROUND_STATES: tuple[str, ...] = ("PLANNED", "OPEN", "CLOSED", "LOCKED")

SIMULATION_TRANSITIONS: dict[str, set[str]] = {
	"CREATED": {"STARTED", "ENDED"},
	"STARTED": {"ENDED"},
	"ENDED": {"STARTED"},
}

ROUND_TRANSITIONS: dict[str, set[str]] = {
	"PLANNED": {"OPEN", "LOCKED"},
	"OPEN": {"CLOSED", "PLANNED"},
	"CLOSED": {"OPEN"},
	"LOCKED": set(),
}


@dataclass(frozen=True)
class TransitionCheck:
	from_state: str
	to_state: str
	is_allowed: bool
	reason: str


def validate_simulation_state(state: str) -> None:
	if state not in SIMULATION_STATES:
		raise ValueError(f"Invalid simulation state '{state}'")


def validate_round_state(state: str) -> None:
	if state not in ROUND_STATES:
		raise ValueError(f"Invalid round state '{state}'")


def can_transition_simulation(from_state: str, to_state: str) -> bool:
	validate_simulation_state(from_state)
	validate_simulation_state(to_state)
	if from_state == to_state:
		return True
	return to_state in SIMULATION_TRANSITIONS.get(from_state, set())


def can_transition_round(from_state: str, to_state: str) -> bool:
	validate_round_state(from_state)
	validate_round_state(to_state)
	if from_state == to_state:
		return True
	return to_state in ROUND_TRANSITIONS.get(from_state, set())


def check_simulation_transition(from_state: str, to_state: str) -> TransitionCheck:
	allowed = can_transition_simulation(from_state, to_state)
	reason = "allowed" if allowed else f"Transition {from_state} -> {to_state} is not permitted"
	return TransitionCheck(from_state=from_state, to_state=to_state, is_allowed=allowed, reason=reason)


def check_round_transition(from_state: str, to_state: str) -> TransitionCheck:
	allowed = can_transition_round(from_state, to_state)
	reason = "allowed" if allowed else f"Transition {from_state} -> {to_state} is not permitted"
	return TransitionCheck(from_state=from_state, to_state=to_state, is_allowed=allowed, reason=reason)


def require_simulation_transition(from_state: str, to_state: str) -> None:
	check = check_simulation_transition(from_state, to_state)
	if not check.is_allowed:
		raise ValueError(check.reason)


def require_round_transition(from_state: str, to_state: str) -> None:
	check = check_round_transition(from_state, to_state)
	if not check.is_allowed:
		raise ValueError(check.reason)


def can_enter_decisions(simulation_state: str, round_state: str) -> bool:
	validate_simulation_state(simulation_state)
	validate_round_state(round_state)
	return simulation_state == "STARTED" and round_state == "OPEN"


def can_move_next_round(simulation_state: str, open_round_count: int) -> bool:
	validate_simulation_state(simulation_state)
	if open_round_count < 0:
		raise ValueError("open_round_count must be >= 0")
	return simulation_state == "STARTED" and open_round_count == 1


def can_undo_round(simulation_state: str) -> bool:
	validate_simulation_state(simulation_state)
	return simulation_state in {"STARTED", "ENDED"}


def can_end_simulation(simulation_state: str) -> bool:
	validate_simulation_state(simulation_state)
	return simulation_state in {"CREATED", "STARTED"}
