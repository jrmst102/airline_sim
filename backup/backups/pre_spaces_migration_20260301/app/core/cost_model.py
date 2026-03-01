from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostBreakdown:
	fuel_cost: float
	fixed_cost: float
	variable_cost: float
	brand_cost: float
	total_cost: float


def _require_non_negative(name: str, value: float) -> None:
	if value < 0:
		raise ValueError(f"{name} must be >= 0")


def compute_fuel_cost(
	flights_per_day: int,
	days_per_round: int,
	base_fuel_cost_per_flight: float,
) -> float:
	if flights_per_day < 0:
		raise ValueError("flights_per_day must be >= 0")
	if days_per_round < 1:
		raise ValueError("days_per_round must be >= 1")
	_require_non_negative("base_fuel_cost_per_flight", base_fuel_cost_per_flight)
	return float(flights_per_day) * float(days_per_round) * float(base_fuel_cost_per_flight)


def compute_variable_cost(
	carried_passengers: float,
	base_variable_cost_per_pax: float,
) -> float:
	_require_non_negative("carried_passengers", carried_passengers)
	_require_non_negative("base_variable_cost_per_pax", base_variable_cost_per_pax)
	return float(carried_passengers) * float(base_variable_cost_per_pax)


def compute_total_cost(
	*,
	flights_per_day: int,
	days_per_round: int,
	carried_passengers: float,
	brand_investment: float,
	base_fuel_cost_per_flight: float,
	base_fixed_cost_per_round: float,
	base_variable_cost_per_pax: float,
) -> CostBreakdown:
	"""
	Compute per-team round cost using the simulation cost formula:
	Cost = FuelCost + FixedCost + VarCost + BrandCost
	"""
	_require_non_negative("base_fixed_cost_per_round", base_fixed_cost_per_round)
	_require_non_negative("brand_investment", brand_investment)

	fuel_cost = compute_fuel_cost(
		flights_per_day=flights_per_day,
		days_per_round=days_per_round,
		base_fuel_cost_per_flight=base_fuel_cost_per_flight,
	)
	variable_cost = compute_variable_cost(
		carried_passengers=carried_passengers,
		base_variable_cost_per_pax=base_variable_cost_per_pax,
	)
	fixed_cost = float(base_fixed_cost_per_round)
	brand_cost = float(brand_investment)
	total_cost = fuel_cost + fixed_cost + variable_cost + brand_cost

	return CostBreakdown(
		fuel_cost=fuel_cost,
		fixed_cost=fixed_cost,
		variable_cost=variable_cost,
		brand_cost=brand_cost,
		total_cost=total_cost,
	)
