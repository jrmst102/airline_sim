from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemandInputs:
	team_id: str
	capacity: float
	price_premium: float
	price_economy: float
	brand_investment: float


@dataclass(frozen=True)
class TeamDemandResult:
	team_id: str
	demand_business: float
	demand_leisure: float
	carried_business: float
	carried_leisure: float
	carried_total: float


def _require_non_negative(name: str, value: float) -> None:
	if value < 0:
		raise ValueError(f"{name} must be >= 0")


def _validate_team_input(item: DemandInputs) -> None:
	if not item.team_id:
		raise ValueError("team_id is required")
	_require_non_negative(f"capacity for team '{item.team_id}'", item.capacity)
	if item.price_premium <= 0:
		raise ValueError(f"price_premium must be > 0 for team '{item.team_id}'")
	if item.price_economy <= 0:
		raise ValueError(f"price_economy must be > 0 for team '{item.team_id}'")
	_require_non_negative(f"brand_investment for team '{item.team_id}'", item.brand_investment)


def compute_brand_factor(brand_investment: float, brand_effectiveness: float) -> float:
	_require_non_negative("brand_investment", brand_investment)
	_require_non_negative("brand_effectiveness", brand_effectiveness)
	return 1.0 + (float(brand_investment) * float(brand_effectiveness))


def compute_demand_scores(
	price_premium: float,
	price_economy: float,
	brand_investment: float,
	brand_effectiveness: float,
) -> tuple[float, float]:
	if price_premium <= 0:
		raise ValueError("price_premium must be > 0")
	if price_economy <= 0:
		raise ValueError("price_economy must be > 0")
	brand_factor = compute_brand_factor(brand_investment, brand_effectiveness)
	business_score = brand_factor / float(price_premium)
	leisure_score = brand_factor / float(price_economy)
	return business_score, leisure_score


def allocate_market_demand(
	*,
	teams: list[DemandInputs],
	base_demand_business: float,
	base_demand_leisure: float,
	brand_effectiveness: float,
) -> list[TeamDemandResult]:
	"""
	Allocate market demand proportionally by score, then apply capacity constraints.

	Business and leisure scores follow:
	- business_score = brand_factor / price_premium
	- leisure_score = brand_factor / price_economy
	- brand_factor = 1 + brand_investment * brand_effectiveness
	"""
	if not teams:
		raise ValueError("At least one team input is required")
	_require_non_negative("base_demand_business", base_demand_business)
	_require_non_negative("base_demand_leisure", base_demand_leisure)
	_require_non_negative("brand_effectiveness", brand_effectiveness)

	for team in teams:
		_validate_team_input(team)

	team_ids = [team.team_id for team in teams]
	if len(set(team_ids)) != len(team_ids):
		raise ValueError("Duplicate team_id values are not allowed")

	business_scores: dict[str, float] = {}
	leisure_scores: dict[str, float] = {}
	by_team: dict[str, DemandInputs] = {team.team_id: team for team in teams}

	for team in teams:
		business_score, leisure_score = compute_demand_scores(
			price_premium=team.price_premium,
			price_economy=team.price_economy,
			brand_investment=team.brand_investment,
			brand_effectiveness=brand_effectiveness,
		)
		business_scores[team.team_id] = business_score
		leisure_scores[team.team_id] = leisure_score

	total_business_score = sum(business_scores.values())
	total_leisure_score = sum(leisure_scores.values())

	results: list[TeamDemandResult] = []
	for team_id in team_ids:
		team = by_team[team_id]
		demand_business = (
			float(base_demand_business) * (business_scores[team_id] / total_business_score)
			if total_business_score > 0
			else 0.0
		)
		demand_leisure = (
			float(base_demand_leisure) * (leisure_scores[team_id] / total_leisure_score)
			if total_leisure_score > 0
			else 0.0
		)

		carried_business = min(float(team.capacity), demand_business)
		remaining_capacity = max(0.0, float(team.capacity) - carried_business)
		carried_leisure = min(remaining_capacity, demand_leisure)
		carried_total = carried_business + carried_leisure

		results.append(
			TeamDemandResult(
				team_id=team_id,
				demand_business=demand_business,
				demand_leisure=demand_leisure,
				carried_business=carried_business,
				carried_leisure=carried_leisure,
				carried_total=carried_total,
			)
		)

	return results
