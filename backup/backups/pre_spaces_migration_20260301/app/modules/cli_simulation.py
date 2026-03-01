import argparse
from pathlib import Path

import pandas as pd


REQUIRED_SHEETS = ["decisions"]


def read_params(xls: pd.ExcelFile) -> dict[str, float]:
    params = {
        "base_demand_per_flight": 90.0,
        "marketing_factor": 0.01,
        "fixed_cost_per_flight": 3500.0,
        "seat_cost": 12.0,
    }

    if "sim_params" not in xls.sheet_names:
        return params

    df = pd.read_excel(xls, sheet_name="sim_params")
    if not {"key", "value"}.issubset(df.columns):
        return params

    for _, row in df.iterrows():
        key = str(row["key"]).strip()
        try:
            value = float(row["value"])
        except Exception:
            continue
        if key:
            params[key] = value

    return params


def validate_decisions(df: pd.DataFrame) -> None:
    required_cols = {
        "round",
        "route",
        "flight",
        "planned_flights",
        "seats_per_flight",
        "avg_fare",
        "bag_fee",
        "marketing_budget",
    }
    missing = sorted(required_cols - set(df.columns))
    if missing:
        raise ValueError(f"Missing required columns in 'decisions': {', '.join(missing)}")


def run_simulation(decisions: pd.DataFrame, params: dict[str, float]) -> pd.DataFrame:
    out = decisions.copy()

    out["planned_flights"] = pd.to_numeric(out["planned_flights"], errors="coerce").fillna(0)
    out["seats_per_flight"] = pd.to_numeric(out["seats_per_flight"], errors="coerce").fillna(0)
    out["avg_fare"] = pd.to_numeric(out["avg_fare"], errors="coerce").fillna(0.0)
    out["bag_fee"] = pd.to_numeric(out["bag_fee"], errors="coerce").fillna(0.0)
    out["marketing_budget"] = pd.to_numeric(out["marketing_budget"], errors="coerce").fillna(0.0)

    base_demand = float(params["base_demand_per_flight"])
    marketing_factor = float(params["marketing_factor"])
    fixed_cost_per_flight = float(params["fixed_cost_per_flight"])
    seat_cost = float(params["seat_cost"])

    out["capacity"] = out["planned_flights"] * out["seats_per_flight"]
    out["demand"] = base_demand * out["planned_flights"] + (out["marketing_budget"] * marketing_factor)
    out["pax"] = out[["capacity", "demand"]].min(axis=1).round(0).astype(int)

    out["revenue"] = out["pax"] * (out["avg_fare"] + out["bag_fee"])
    out["cost"] = (out["planned_flights"] * fixed_cost_per_flight) + (out["capacity"] * seat_cost)
    out["profit"] = out["revenue"] - out["cost"]

    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Run airline simulation from an Excel input file.")
    parser.add_argument("--input", required=True, help="Path to input .xlsx")
    parser.add_argument("--output", required=True, help="Path to output .xlsx")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    xls = pd.ExcelFile(input_path)
    for sheet in REQUIRED_SHEETS:
        if sheet not in xls.sheet_names:
            raise ValueError(f"Missing required sheet: '{sheet}'")

    decisions = pd.read_excel(xls, sheet_name="decisions")
    validate_decisions(decisions)
    params = read_params(xls)

    results = run_simulation(decisions, params)
    summary = (
        results.groupby("round", as_index=False)[["revenue", "cost", "profit", "pax"]]
        .sum()
        .sort_values("round")
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        results.to_excel(writer, index=False, sheet_name="results")
        summary.to_excel(writer, index=False, sheet_name="summary")
        pd.DataFrame([params]).to_excel(writer, index=False, sheet_name="params_used")

    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()