"""
Simulation Engine – Airlines Competitive Strategy Simulation
=============================================================
Computes round results from team decisions using the rules from:
"Airlines Competitive Game – Turbulence at 30,000 Feet:
 Competition on the JFK–Boston Corridor" (Spring 2026).

Cost formulas, fare lookups, and penalty rules follow the Case Appendix.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.modules.setup_simulation import (
	get_parameter_float,
	get_parameter_int,
)


# ═══════════════════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class SimulationParameters:
	"""Parameters loaded from key-value parameters.csv (Case Appendix)."""
	total_demand_passengers: int       # 120,000
	business_demand: int               # 48,000
	leisure_demand: int                # 72,000
	seats_per_flight: int              # 200
	fixed_cost_per_flight: int         # 18,000
	days_per_month: int                # 30
	discount_penalty_threshold: int    # 3  (kept for possible future use)
	discount_penalty_rate: float       # 0.08
	branding_costs: dict[str, int]     # level -> monthly cost
	product_costs: dict[str, int]      # strategy -> monthly cost
	fare_multiplier: float             # avg monthly trips per passenger (Case Appendix)


@dataclass(frozen=True)
class TeamDecisionInput:
	"""One team's decision for a round."""
	team_id: str
	flights_per_day: int               # 0–5
	price_business: float              # team-set business seat price ($)
	price_leisure: float               # team-set leisure seat price ($)
	branding_level: str                # "Low" | "Medium" | "High"
	product_strategy: str              # "High" | "Medium" | "Low"
	variable_cost_per_passenger: float  # airline-specific (Case Appendix)


@dataclass(frozen=True)
class TeamRoundResult:
	team_id: str
	passengers: int
	revenue: float
	variable_cost: float
	fixed_cost: float
	branding_cost: float
	product_cost: float
	total_cost: float
	profit: float
	market_share_volume: float
	market_share_profit: float
	load_factor: float
	avg_revenue_per_flight: float
	avg_cost_per_flight: float
	avg_profit_per_flight: float
	price_business: float
	price_leisure: float


@dataclass(frozen=True)
class MarketRoundResult:
	total_demand: int
	total_passengers: int
	total_revenue: float
	total_cost: float
	total_profit: float


@dataclass(frozen=True)
class RoundComputationResult:
	team_results: list[TeamRoundResult]
	market_result: MarketRoundResult


# ═══════════════════════════════════════════════════════════════════════════
# Build parameters from key-value CSV
# ═══════════════════════════════════════════════════════════════════════════

def build_parameters_from_csv(params: dict[str, str]) -> SimulationParameters:
	"""Construct SimulationParameters from a key-value dict (parameters.csv)."""
	branding_costs = {
		"Low": get_parameter_int(params, "branding_cost_low"),
		"Medium": get_parameter_int(params, "branding_cost_medium"),
		"High": get_parameter_int(params, "branding_cost_high"),
	}
	product_costs = {
		"High": get_parameter_int(params, "product_cost_high"),
		"Medium": get_parameter_int(params, "product_cost_medium"),
		"Low": get_parameter_int(params, "product_cost_low"),
	}
	return SimulationParameters(
		total_demand_passengers=get_parameter_int(params, "total_demand_passengers"),
		business_demand=get_parameter_int(params, "business_demand"),
		leisure_demand=get_parameter_int(params, "leisure_demand"),
		seats_per_flight=get_parameter_int(params, "seats_per_flight"),
		fixed_cost_per_flight=get_parameter_int(params, "fixed_cost_per_flight"),
		days_per_month=get_parameter_int(params, "days_per_month"),
		discount_penalty_threshold=get_parameter_int(params, "discount_penalty_threshold"),
		discount_penalty_rate=get_parameter_float(params, "discount_penalty_rate"),
		branding_costs=branding_costs,
		product_costs=product_costs,
		fare_multiplier=get_parameter_float(params, "fare_multiplier"),
	)


# ═══════════════════════════════════════════════════════════════════════════
# Round computation
# ═══════════════════════════════════════════════════════════════════════════

VALID_BRANDING = {"Low", "Medium", "High"}
VALID_PRODUCTS = {"High", "Medium", "Low"}


def _validate_decision(d: TeamDecisionInput, p: SimulationParameters) -> None:
	if not d.team_id:
		raise ValueError("team_id is required")
	if d.flights_per_day < 0 or d.flights_per_day > 5:
		raise ValueError(f"flights_per_day must be 0–5 for team '{d.team_id}' (got {d.flights_per_day})")
	if d.price_business <= 0:
		raise ValueError(f"price_business must be > 0 for team '{d.team_id}' (got {d.price_business})")
	if d.price_leisure <= 0:
		raise ValueError(f"price_leisure must be > 0 for team '{d.team_id}' (got {d.price_leisure})")
	if d.branding_level not in VALID_BRANDING:
		raise ValueError(f"Invalid branding_level '{d.branding_level}' for team '{d.team_id}'")
	if d.product_strategy not in VALID_PRODUCTS:
		raise ValueError(f"Invalid product_strategy '{d.product_strategy}' for team '{d.team_id}'")
	if d.variable_cost_per_passenger < 0:
		raise ValueError(f"variable_cost_per_passenger must be >= 0 for team '{d.team_id}'")


def compute_round_results(
	decisions: list[TeamDecisionInput],
	parameters: SimulationParameters,
) -> RoundComputationResult:
	"""Compute results for one round given all team decisions.

	Demand allocation uses a score-based model proportional to each
	team's capacity weighted by inverse fare.  This is deterministic
	from the case inputs.
	"""
	if not decisions:
		raise ValueError("At least one team decision is required")

	# Validate
	team_ids_seen: set[str] = set()
	for d in decisions:
		_validate_decision(d, parameters)
		if d.team_id in team_ids_seen:
			raise ValueError(f"Duplicate decision for team '{d.team_id}'")
		team_ids_seen.add(d.team_id)

	# ── Capacity (Case Appendix) ──────────────────────────────────
	monthly_flights: dict[str, int] = {}
	capacities: dict[str, int] = {}
	for d in decisions:
		mf = d.flights_per_day * parameters.days_per_month
		monthly_flights[d.team_id] = mf
		capacities[d.team_id] = mf * parameters.seats_per_flight

	# ── Team-set prices ───────────────────────────────────────────
	biz_fares: dict[str, float] = {}
	lei_fares: dict[str, float] = {}
	for d in decisions:
		biz_fares[d.team_id] = d.price_business
		lei_fares[d.team_id] = d.price_leisure

	# ── Demand allocation ─────────────────────────────────────────
	# Score = capacity / fare  (higher capacity + lower fare → more demand)
	biz_scores: dict[str, float] = {}
	lei_scores: dict[str, float] = {}
	for d in decisions:
		cap = capacities[d.team_id]
		if cap > 0:
			biz_scores[d.team_id] = cap / biz_fares[d.team_id]
			lei_scores[d.team_id] = cap / lei_fares[d.team_id]
		else:
			biz_scores[d.team_id] = 0.0
			lei_scores[d.team_id] = 0.0

	total_biz_score = sum(biz_scores.values())
	total_lei_score = sum(lei_scores.values())

	biz_pax: dict[str, int] = {}
	lei_pax: dict[str, int] = {}
	tot_pax: dict[str, int] = {}

	for d in decisions:
		cap = capacities[d.team_id]
		# Business passengers
		if total_biz_score > 0 and cap > 0:
			biz_demand = parameters.business_demand * (biz_scores[d.team_id] / total_biz_score)
		else:
			biz_demand = 0.0
		biz_carried = min(int(biz_demand), cap)
		biz_pax[d.team_id] = biz_carried

		# Leisure passengers (remaining capacity)
		remaining = cap - biz_carried
		if total_lei_score > 0 and remaining > 0:
			lei_demand = parameters.leisure_demand * (lei_scores[d.team_id] / total_lei_score)
		else:
			lei_demand = 0.0
		lei_carried = min(int(lei_demand), remaining)
		lei_pax[d.team_id] = lei_carried

		tot_pax[d.team_id] = biz_carried + lei_carried

	# ── Revenue ───────────────────────────────────────────────────
	# Fares are per-ticket prices; multiply by fare_multiplier
	# (avg monthly trips per passenger on this corridor).
	revenues: dict[str, float] = {}
	for d in decisions:
		rev = float(
			biz_pax[d.team_id] * biz_fares[d.team_id]
			+ lei_pax[d.team_id] * lei_fares[d.team_id]
		) * parameters.fare_multiplier
		revenues[d.team_id] = rev

	# ── Costs (Case Appendix) ─────────────────────────────────────
	var_costs: dict[str, float] = {}
	fix_costs: dict[str, float] = {}
	brand_costs: dict[str, float] = {}
	prod_costs: dict[str, float] = {}
	total_costs: dict[str, float] = {}
	profits: dict[str, float] = {}

	for d in decisions:
		vc = float(tot_pax[d.team_id]) * d.variable_cost_per_passenger
		fc = float(monthly_flights[d.team_id]) * parameters.fixed_cost_per_flight
		bc = float(parameters.branding_costs[d.branding_level])
		pc = float(parameters.product_costs[d.product_strategy])
		tc = vc + fc + bc + pc
		pr = revenues[d.team_id] - tc

		var_costs[d.team_id] = vc
		fix_costs[d.team_id] = fc
		brand_costs[d.team_id] = bc
		prod_costs[d.team_id] = pc
		total_costs[d.team_id] = tc
		profits[d.team_id] = pr

	# ── Market shares ─────────────────────────────────────────────
	total_passengers = sum(tot_pax.values())
	total_positive_profit = sum(max(p, 0.0) for p in profits.values())
	total_profit = sum(profits.values())

	# ── Assemble team results ─────────────────────────────────────
	team_results: list[TeamRoundResult] = []
	for d in decisions:
		pax = tot_pax[d.team_id]
		cap = capacities[d.team_id]
		mf = monthly_flights[d.team_id]
		rev = revenues[d.team_id]
		tc = total_costs[d.team_id]
		pr = profits[d.team_id]

		load_factor = pax / cap if cap > 0 else 0.0
		avg_rev = rev / mf if mf > 0 else 0.0
		avg_cost = tc / mf if mf > 0 else 0.0
		avg_prof = pr / mf if mf > 0 else 0.0
		ms_vol = pax / total_passengers if total_passengers > 0 else 0.0
		if total_positive_profit > 0:
			ms_prof = max(pr, 0.0) / total_positive_profit
		elif total_profit != 0:
			# All profits non-positive: distribute proportionally
			ms_prof = pr / total_profit
		else:
			ms_prof = 1.0 / len(decisions)

		team_results.append(TeamRoundResult(
			team_id=d.team_id,
			passengers=pax,
			revenue=rev,
			variable_cost=var_costs[d.team_id],
			fixed_cost=fix_costs[d.team_id],
			branding_cost=brand_costs[d.team_id],
			product_cost=prod_costs[d.team_id],
			total_cost=tc,
			profit=pr,
			market_share_volume=ms_vol,
			market_share_profit=ms_prof,
			load_factor=load_factor,
			avg_revenue_per_flight=avg_rev,
			avg_cost_per_flight=avg_cost,
			avg_profit_per_flight=avg_prof,
			price_business=d.price_business,
			price_leisure=d.price_leisure,
		))

	market_result = MarketRoundResult(
		total_demand=parameters.total_demand_passengers,
		total_passengers=total_passengers,
		total_revenue=sum(revenues.values()),
		total_cost=sum(total_costs.values()),
		total_profit=sum(profits.values()),
	)

	return RoundComputationResult(team_results=team_results, market_result=market_result)
