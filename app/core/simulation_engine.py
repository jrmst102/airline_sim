from __future__ import annotations

from dataclasses import dataclass

from app.core.cost_model import compute_total_cost
from app.core.demand_model import DemandInputs, allocate_market_demand
from app.core.indices_model import TeamIndexInput, compute_market_share_indices
from app.core.pricing_model import TeamPricingInput, compute_pricing_results


@dataclass(frozen=True)
class SimulationParameters:
	days_per_round: int
	seats_per_flight: int
	base_demand_business: float
	base_demand_leisure: float
	base_fuel_cost_per_flight: float
	base_fixed_cost_per_round: float
	base_variable_cost_per_pax: float
	brand_effectiveness: float


@dataclass(frozen=True)
class TeamDecisionInput:
	team_id: str
	flights_per_day: int
	price_premium: float
	price_economy: float
	brand_investment: float


@dataclass(frozen=True)
class TeamRoundResult:
	team_id: str
	capacity: float
	carried_business: float
	carried_leisure: float
	revenue: float
	cost: float
	profit: float
	market_share_volume: float
	market_share_profit: float


@dataclass(frozen=True)
class MarketRoundResult:
	total_capacity: float
	total_carried: float
	avg_price_premium: float
	avg_price_economy: float
	total_revenue: float
	total_cost: float
	total_profit: float


@dataclass(frozen=True)
class RoundComputationResult:
	team_results: list[TeamRoundResult]
	market_result: MarketRoundResult


def _validate_parameters(parameters: SimulationParameters) -> None:
	if parameters.days_per_round < 1:
		raise ValueError("days_per_round must be >= 1")
	if parameters.seats_per_flight < 1:
		raise ValueError("seats_per_flight must be >= 1")
	if parameters.base_demand_business < 0:
		raise ValueError("base_demand_business must be >= 0")
	if parameters.base_demand_leisure < 0:
		raise ValueError("base_demand_leisure must be >= 0")
	if parameters.base_fuel_cost_per_flight < 0:
		raise ValueError("base_fuel_cost_per_flight must be >= 0")
	if parameters.base_fixed_cost_per_round < 0:
		raise ValueError("base_fixed_cost_per_round must be >= 0")
	if parameters.base_variable_cost_per_pax < 0:
		raise ValueError("base_variable_cost_per_pax must be >= 0")
	if parameters.brand_effectiveness < 0:
		raise ValueError("brand_effectiveness must be >= 0")


def _validate_decision(decision: TeamDecisionInput) -> None:
	if not decision.team_id:
		raise ValueError("team_id is required")
	if decision.flights_per_day < 0:
		raise ValueError(f"flights_per_day must be >= 0 for team '{decision.team_id}'")
	if decision.price_premium <= 0:
		raise ValueError(f"price_premium must be > 0 for team '{decision.team_id}'")
	if decision.price_economy <= 0:
		raise ValueError(f"price_economy must be > 0 for team '{decision.team_id}'")
	if decision.brand_investment < 0:
		raise ValueError(f"brand_investment must be >= 0 for team '{decision.team_id}'")


def compute_round_results(
	decisions: list[TeamDecisionInput],
	parameters: SimulationParameters,
	active_team_ids: list[str] | None = None,
) -> RoundComputationResult:
	_validate_parameters(parameters)

	if not decisions:
		raise ValueError("At least one team decision is required")

	for decision in decisions:
		_validate_decision(decision)

	decision_by_team = {decision.team_id: decision for decision in decisions}
	if len(decision_by_team) != len(decisions):
		raise ValueError("Duplicate team decisions are not allowed")

	team_ids = active_team_ids[:] if active_team_ids is not None else [decision.team_id for decision in decisions]
	if not team_ids:
		raise ValueError("No active teams available for computation")

	missing = [team_id for team_id in team_ids if team_id not in decision_by_team]
	if missing:
		raise ValueError(f"Missing decisions for active team(s): {', '.join(missing)}")

	capacities: dict[str, float] = {}

	for team_id in team_ids:
		decision = decision_by_team[team_id]
		capacity = decision.flights_per_day * parameters.days_per_round * parameters.seats_per_flight
		capacities[team_id] = capacity

	demand_inputs = [
		DemandInputs(
			team_id=team_id,
			capacity=capacities[team_id],
			price_premium=decision_by_team[team_id].price_premium,
			price_economy=decision_by_team[team_id].price_economy,
			brand_investment=decision_by_team[team_id].brand_investment,
		)
		for team_id in team_ids
	]
	demand_results = allocate_market_demand(
		teams=demand_inputs,
		base_demand_business=parameters.base_demand_business,
		base_demand_leisure=parameters.base_demand_leisure,
		brand_effectiveness=parameters.brand_effectiveness,
	)
	demand_by_team = {result.team_id: result for result in demand_results}

	pricing_inputs = [
		TeamPricingInput(
			team_id=team_id,
			price_premium=decision_by_team[team_id].price_premium,
			price_economy=decision_by_team[team_id].price_economy,
			carried_business=demand_by_team[team_id].carried_business,
			carried_leisure=demand_by_team[team_id].carried_leisure,
		)
		for team_id in team_ids
	]
	pricing_results, pricing_summary = compute_pricing_results(pricing_inputs)
	pricing_by_team = {result.team_id: result for result in pricing_results}

	team_costs: dict[str, float] = {}
	team_profits: dict[str, float] = {}
	index_inputs: list[TeamIndexInput] = []
	total_cost = 0.0
	total_profit = 0.0
	for team_id in team_ids:
		decision = decision_by_team[team_id]
		demand_result = demand_by_team[team_id]
		pricing_result = pricing_by_team[team_id]
		cost_breakdown = compute_total_cost(
			flights_per_day=decision.flights_per_day,
			days_per_round=parameters.days_per_round,
			carried_passengers=demand_result.carried_total,
			brand_investment=decision.brand_investment,
			base_fuel_cost_per_flight=parameters.base_fuel_cost_per_flight,
			base_fixed_cost_per_round=parameters.base_fixed_cost_per_round,
			base_variable_cost_per_pax=parameters.base_variable_cost_per_pax,
		)
		cost = cost_breakdown.total_cost
		revenue = pricing_result.revenue
		profit = revenue - cost

		team_costs[team_id] = cost
		team_profits[team_id] = profit
		total_cost += cost
		total_profit += profit
		index_inputs.append(
			TeamIndexInput(
				team_id=team_id,
				carried_total=demand_result.carried_total,
				profit=profit,
			)
		)

	team_indices, indices_summary = compute_market_share_indices(index_inputs)
	indices_by_team = {index.team_id: index for index in team_indices}

	team_results: list[TeamRoundResult] = []
	for team_id in team_ids:
		demand_result = demand_by_team[team_id]
		pricing_result = pricing_by_team[team_id]
		index_result = indices_by_team[team_id]
		profit = team_profits[team_id]
		team_results.append(
			TeamRoundResult(
				team_id=team_id,
				capacity=capacities[team_id],
				carried_business=demand_result.carried_business,
				carried_leisure=demand_result.carried_leisure,
				revenue=pricing_result.revenue,
				cost=team_costs[team_id],
				profit=profit,
				market_share_volume=index_result.market_share_volume,
				market_share_profit=index_result.market_share_profit,
			)
		)

	total_capacity = sum(result.capacity for result in team_results)
	total_carried = indices_summary.total_carried
	total_revenue = pricing_summary.total_revenue
	avg_price_premium = pricing_summary.avg_price_premium
	avg_price_economy = pricing_summary.avg_price_economy

	market_result = MarketRoundResult(
		total_capacity=total_capacity,
		total_carried=total_carried,
		avg_price_premium=avg_price_premium,
		avg_price_economy=avg_price_economy,
		total_revenue=total_revenue,
		total_cost=total_cost,
		total_profit=total_profit,
	)

	return RoundComputationResult(team_results=team_results, market_result=market_result)
