from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TeamPricingInput:
	team_id: str
	price_premium: float
	price_economy: float
	carried_business: float
	carried_leisure: float


@dataclass(frozen=True)
class TeamPricingResult:
	team_id: str
	revenue: float
	avg_realized_fare: float


@dataclass(frozen=True)
class PricingSummary:
	avg_price_premium: float
	avg_price_economy: float
	total_revenue: float


def _require_non_negative(name: str, value: float) -> None:
	if value < 0:
		raise ValueError(f"{name} must be >= 0")


def compute_revenue(
	*,
	carried_business: float,
	carried_leisure: float,
	price_premium: float,
	price_economy: float,
) -> float:
	"""
	Revenue = (CarriedB * Pprem) + (CarriedL * Pecon)
	"""
	_require_non_negative("carried_business", carried_business)
	_require_non_negative("carried_leisure", carried_leisure)
	if price_premium <= 0:
		raise ValueError("price_premium must be > 0")
	if price_economy <= 0:
		raise ValueError("price_economy must be > 0")
	return (float(carried_business) * float(price_premium)) + (
		float(carried_leisure) * float(price_economy)
	)


def compute_pricing_results(
	team_inputs: list[TeamPricingInput],
) -> tuple[list[TeamPricingResult], PricingSummary]:
	if not team_inputs:
		raise ValueError("At least one team input is required")

	team_ids = [item.team_id for item in team_inputs]
	if any(not team_id for team_id in team_ids):
		raise ValueError("team_id is required for all inputs")
	if len(set(team_ids)) != len(team_ids):
		raise ValueError("Duplicate team_id values are not allowed")

	results: list[TeamPricingResult] = []
	total_revenue = 0.0

	for item in team_inputs:
		revenue = compute_revenue(
			carried_business=item.carried_business,
			carried_leisure=item.carried_leisure,
			price_premium=item.price_premium,
			price_economy=item.price_economy,
		)
		carried_total = float(item.carried_business) + float(item.carried_leisure)
		avg_realized_fare = revenue / carried_total if carried_total > 0 else 0.0
		results.append(
			TeamPricingResult(
				team_id=item.team_id,
				revenue=revenue,
				avg_realized_fare=avg_realized_fare,
			)
		)
		total_revenue += revenue

	avg_price_premium = sum(float(item.price_premium) for item in team_inputs) / len(team_inputs)
	avg_price_economy = sum(float(item.price_economy) for item in team_inputs) / len(team_inputs)

	summary = PricingSummary(
		avg_price_premium=avg_price_premium,
		avg_price_economy=avg_price_economy,
		total_revenue=total_revenue,
	)
	return results, summary
