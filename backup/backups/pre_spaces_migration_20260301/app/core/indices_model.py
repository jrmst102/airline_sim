from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamIndexInput:
	team_id: str
	carried_total: float
	profit: float


@dataclass(frozen=True)
class TeamIndices:
	team_id: str
	market_share_volume: float
	market_share_profit: float


@dataclass(frozen=True)
class IndicesSummary:
	total_carried: float
	total_positive_profit: float


def _require_non_negative(name: str, value: float) -> None:
	if value < 0:
		raise ValueError(f"{name} must be >= 0")


def _validate_inputs(team_inputs: list[TeamIndexInput]) -> None:
	if not team_inputs:
		raise ValueError("At least one team input is required")

	team_ids = [item.team_id for item in team_inputs]
	if any(not team_id for team_id in team_ids):
		raise ValueError("team_id is required for all inputs")
	if len(set(team_ids)) != len(team_ids):
		raise ValueError("Duplicate team_id values are not allowed")

	for item in team_inputs:
		_require_non_negative(f"carried_total for team '{item.team_id}'", item.carried_total)


def compute_market_share_indices(
	team_inputs: list[TeamIndexInput],
) -> tuple[list[TeamIndices], IndicesSummary]:
	"""
	Compute per-team market shares from totals:
	- MS_vol_i = Carried_i / sum(Carried_j)
	- MS_profit_i = max(Profit_i, 0) / sum(max(Profit_j, 0))
	"""
	_validate_inputs(team_inputs)

	total_carried = sum(float(item.carried_total) for item in team_inputs)
	total_positive_profit = sum(max(float(item.profit), 0.0) for item in team_inputs)

	team_indices: list[TeamIndices] = []
	for item in team_inputs:
		market_share_volume = (
			float(item.carried_total) / total_carried if total_carried > 0 else 0.0
		)
		market_share_profit = (
			max(float(item.profit), 0.0) / total_positive_profit
			if total_positive_profit > 0
			else 0.0
		)
		team_indices.append(
			TeamIndices(
				team_id=item.team_id,
				market_share_volume=market_share_volume,
				market_share_profit=market_share_profit,
			)
		)

	summary = IndicesSummary(
		total_carried=total_carried,
		total_positive_profit=total_positive_profit,
	)
	return team_indices, summary
