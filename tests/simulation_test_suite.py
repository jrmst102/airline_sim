#!/usr/bin/env python3
"""
Airline Simulation Test Suite
==============================
Runs 32 scenarios against the simulation engine, comparing actual CSV
outputs to independently re-computed expected results.

Entry point
-----------
    python -m tests.simulation_test_suite [OPTIONS]

Options
-------
    --out PATH          Report file path (default: ./tests/reports/simulation_test_report.txt)
    --seed INT          RNG seed for random scenarios (default: 12345)
    --stop-on-fail      Stop after first failed scenario
    --keep-sim-folders  Keep temp simulation folders after run

Each scenario:
  1. Creates a fresh simulation (isolated temp folder)
  2. Starts simulation, writes scenario-specific decisions
  3. Calls move_next_round (engine computes results, writes CSVs)
  4. Re-computes expected results independently via engine pure functions
  5. Compares actual CSV values against expected values
  6. Checks structural invariants
  7. Records PASS/FAIL with detailed diffs
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import random
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── Ensure project root is on sys.path ────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from app.modules.enter_decisions import enter_decision
from app.modules.move_next_round import move_next_round
from app.modules.setup_simulation import setup_simulation, TEAM_LETTERS
from app.modules.start_simulation import start_simulation

from tests.helpers.comparator import ComparisonResult, compare_expected_actual
from tests.helpers.constraints import Constraints, get_constraints
from tests.helpers.expected_calculator import compute_expected
from tests.helpers.scenarios import (
    ALL_SCENARIOS,
    Decision,
    ScenarioSpec,
    build_baseline_decisions,
    _copy_decisions,
)


# ═══════════════════════════════════════════════════════════════════════════
# Result data structures
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class OverwriteCheckResult:
    """Result of the decision-overwrite regression check."""
    passed: bool
    detail: str = ""


@dataclass
class ScenarioResult:
    scenario_id: int
    scenario_name: str
    status: str          # "PASS" or "FAIL"
    failure_type: str = ""
    comparison: ComparisonResult | None = None
    overwrite_check: OverwriteCheckResult | None = None
    decisions_applied: list[Decision] = field(default_factory=list)
    exception: str = ""
    elapsed_seconds: float = 0.0


@dataclass
class Report:
    timestamp: str = ""
    seed: int = 12345
    git_commit: str = ""
    total_scenarios: int = 32
    passed: int = 0
    failed: int = 0
    results: list[ScenarioResult] = field(default_factory=list)
    total_runtime_seconds: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════════

def _git_commit_hash() -> str:
    """Try to get current git commit hash, or empty string."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
            cwd=_PROJECT_ROOT,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _check_decision_overwrites(
    sim_path: Path,
    simulation_id: str,
    round_number: int,
    intended_decisions: list[Decision],
) -> OverwriteCheckResult:
    """Regression check: verify decisions.csv has exactly 6 distinct teams
    for the round, each matching intended inputs."""
    rows = _load_csv_rows(sim_path / "decisions.csv")
    round_rows = [
        r for r in rows
        if r.get("simulation_id") == simulation_id
        and int(float(r.get("round_number", "0"))) == round_number
    ]

    # Check 6 distinct teams
    team_ids_found = [r.get("team_id", "") for r in round_rows]
    unique_teams = set(team_ids_found)
    if len(unique_teams) != 6:
        return OverwriteCheckResult(
            passed=False,
            detail=f"Expected 6 distinct teams, found {len(unique_teams)}: {sorted(unique_teams)}"
        )

    # Build lookup
    actual_by_team: dict[str, dict[str, str]] = {}
    for r in round_rows:
        actual_by_team[r["team_id"]] = r

    # Check each intended decision matches
    issues: list[str] = []
    for dec in intended_decisions:
        act = actual_by_team.get(dec.team_id)
        if act is None:
            issues.append(f"Team {dec.team_id}: MISSING from decisions.csv")
            continue
        # Compare key fields
        if int(float(act.get("flights_per_day", "0"))) != dec.flights_per_day:
            issues.append(
                f"Team {dec.team_id}: flights_per_day "
                f"expected={dec.flights_per_day} actual={act.get('flights_per_day')}"
            )
        if int(float(act.get("price_business", "0"))) != dec.price_business:
            issues.append(
                f"Team {dec.team_id}: price_business "
                f"expected={dec.price_business} actual={act.get('price_business')}"
            )
        if int(float(act.get("price_leisure", "0"))) != dec.price_leisure:
            issues.append(
                f"Team {dec.team_id}: price_leisure "
                f"expected={dec.price_leisure} actual={act.get('price_leisure')}"
            )
        if act.get("branding_level", "") != dec.branding_level:
            issues.append(
                f"Team {dec.team_id}: branding_level "
                f"expected={dec.branding_level} actual={act.get('branding_level')}"
            )
        if act.get("product_strategy", "") != dec.product_strategy:
            issues.append(
                f"Team {dec.team_id}: product_strategy "
                f"expected={dec.product_strategy} actual={act.get('product_strategy')}"
            )

    if issues:
        return OverwriteCheckResult(passed=False, detail="; ".join(issues))
    return OverwriteCheckResult(passed=True)


# ═══════════════════════════════════════════════════════════════════════════
# Scenario runner
# ═══════════════════════════════════════════════════════════════════════════

def run_scenario(
    spec: ScenarioSpec,
    seed: int,
    tmp_root: Path,
    keep_folder: bool = False,
) -> ScenarioResult:
    """Execute one scenario end-to-end and return the result."""
    start_time = time.monotonic()
    sim_id = f"TS_{spec.id:02d}"
    sim_path: Path | None = None

    try:
        # ── 1) Fresh simulation setup ──────────────────────────────
        sim_path = setup_simulation(
            simulation_id=sim_id,
            simulation_name=f"Scenario {spec.id}: {spec.name}",
            total_rounds=3,
            root_dir=tmp_root,
            overwrite=True,
        )

        # ── 2) Start simulation ───────────────────────────────────
        start_simulation(simulation_id=sim_id, root_dir=tmp_root)

        # ── 3) Build baseline decisions ────────────────────────────
        baseline = build_baseline_decisions()
        rng = random.Random(seed)

        # ── 4) Apply scenario modifications ────────────────────────
        decisions = _copy_decisions(baseline)
        decisions = spec.decision_overrides_fn(decisions, get_constraints(sim_path), rng)

        # ── 5) Write decisions via enter_decision module ───────────
        for dec in decisions:
            enter_decision(
                simulation_id=sim_id,
                team_id=dec.team_id,
                flights_per_day=dec.flights_per_day,
                price_business=float(dec.price_business),
                price_leisure=float(dec.price_leisure),
                branding_level=dec.branding_level,
                product_strategy=dec.product_strategy,
                root_dir=tmp_root,
            )

        # ── 6) Decision-overwrite regression check ─────────────────
        overwrite_check = _check_decision_overwrites(
            sim_path, sim_id, round_number=1, intended_decisions=decisions,
        )
        if not overwrite_check.passed:
            elapsed = time.monotonic() - start_time
            return ScenarioResult(
                scenario_id=spec.id,
                scenario_name=spec.name,
                status="FAIL",
                failure_type="Overwrite Bug",
                overwrite_check=overwrite_check,
                decisions_applied=decisions,
                elapsed_seconds=elapsed,
            )

        # ── 7) Advance round (engine computes + writes CSVs) ──────
        move_next_round(simulation_id=sim_id, root_dir=tmp_root)

        # ── 8) Compute expected results independently ──────────────
        expected = compute_expected(sim_path, round_number=1)

        # ── 9) Compare actual vs expected ──────────────────────────
        comparison = compare_expected_actual(expected, sim_path, round_number=1)

        elapsed = time.monotonic() - start_time
        if comparison.passed:
            return ScenarioResult(
                scenario_id=spec.id,
                scenario_name=spec.name,
                status="PASS",
                comparison=comparison,
                overwrite_check=overwrite_check,
                decisions_applied=decisions,
                elapsed_seconds=elapsed,
            )
        else:
            # Determine failure type
            if comparison.missing_teams or comparison.extra_teams:
                ftype = "Missing Row"
            elif comparison.diffs:
                ftype = "Mismatch"
            else:
                ftype = "Invariant Violation"
            return ScenarioResult(
                scenario_id=spec.id,
                scenario_name=spec.name,
                status="FAIL",
                failure_type=ftype,
                comparison=comparison,
                overwrite_check=overwrite_check,
                decisions_applied=decisions,
                elapsed_seconds=elapsed,
            )

    except Exception as exc:
        elapsed = time.monotonic() - start_time
        return ScenarioResult(
            scenario_id=spec.id,
            scenario_name=spec.name,
            status="FAIL",
            failure_type="Exception",
            exception=f"{type(exc).__name__}: {exc}",
            elapsed_seconds=elapsed,
        )
    finally:
        if sim_path and sim_path.exists() and not keep_folder:
            shutil.rmtree(sim_path, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════════
# Run all scenarios
# ═══════════════════════════════════════════════════════════════════════════

def run_all_scenarios(
    seed: int = 12345,
    stop_on_fail: bool = False,
    keep_sim_folders: bool = False,
) -> Report:
    """Execute all 32 scenarios and return the full report."""
    report = Report(
        timestamp=datetime.now(timezone.utc).isoformat(),
        seed=seed,
        git_commit=_git_commit_hash(),
        total_scenarios=len(ALL_SCENARIOS),
    )

    overall_start = time.monotonic()
    tmp_root = Path(tempfile.mkdtemp(prefix="airline_test_suite_"))

    try:
        for spec in ALL_SCENARIOS:
            result = run_scenario(spec, seed, tmp_root, keep_folder=keep_sim_folders)
            report.results.append(result)
            if result.status == "PASS":
                report.passed += 1
            else:
                report.failed += 1
            if stop_on_fail and result.status == "FAIL":
                break
    finally:
        if not keep_sim_folders:
            shutil.rmtree(tmp_root, ignore_errors=True)
        else:
            print(f"Simulation folders kept at: {tmp_root}")

    report.total_runtime_seconds = time.monotonic() - overall_start
    return report


# ═══════════════════════════════════════════════════════════════════════════
# Text report writer
# ═══════════════════════════════════════════════════════════════════════════

_MAX_DIFFS_PER_SCENARIO = 20


def _format_changes_from_baseline(
    decisions: list[Decision],
) -> list[str]:
    """Show only fields that differ from baseline."""
    baseline = build_baseline_decisions()
    baseline_map = {d.team_id: d for d in baseline}
    lines: list[str] = []
    for dec in decisions:
        base = baseline_map.get(dec.team_id)
        if base is None:
            continue
        changes: list[str] = []
        if dec.flights_per_day != base.flights_per_day:
            changes.append(f"FlightsPerDay={dec.flights_per_day}")
        if dec.price_business != base.price_business:
            changes.append(f"Price_B={dec.price_business}")
        if dec.price_leisure != base.price_leisure:
            changes.append(f"Price_L={dec.price_leisure}")
        if dec.branding_level != base.branding_level:
            changes.append(f"Brand={dec.branding_level}")
        if dec.product_strategy != base.product_strategy:
            changes.append(f"Product={dec.product_strategy}")
        if changes:
            lines.append(f"    Team {dec.team_id}: {', '.join(changes)}")
    if not lines:
        lines.append("    (no changes from baseline)")
    return lines


def write_text_report(report: Report, out_path: Path) -> None:
    """Write a human-readable plain-text report."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []

    # ── Header ─────────────────────────────────────────────────────
    lines.append("=" * 72)
    lines.append("  Airline Simulation Test Suite Report")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  Timestamp  : {report.timestamp}")
    lines.append(f"  RNG Seed   : {report.seed}")
    lines.append(f"  Git Commit : {report.git_commit or '(not available)'}")
    lines.append(f"  Total Run  : {len(report.results)} / {report.total_scenarios} scenarios")
    lines.append(f"  PASSED     : {report.passed}")
    lines.append(f"  FAILED     : {report.failed}")
    lines.append(f"  Runtime    : {report.total_runtime_seconds:.2f}s")
    lines.append("")

    # ── Summary table ──────────────────────────────────────────────
    lines.append("-" * 72)
    lines.append(f"  {'ID':>3}  {'Scenario Name':<48} {'Status':<6}  Notes")
    lines.append("-" * 72)
    for r in report.results:
        notes = ""
        if r.status == "FAIL":
            notes = r.failure_type
            if r.exception:
                notes = r.exception[:40]
        lines.append(f"  {r.scenario_id:>3}  {r.scenario_name:<48} {r.status:<6}  {notes}")
    lines.append("-" * 72)
    lines.append("")

    # ── Detailed results ───────────────────────────────────────────
    for r in report.results:
        lines.append("=" * 72)
        lines.append(f"  Scenario {r.scenario_id:02d}: {r.scenario_name}")
        lines.append(f"  STATUS: {r.status}")
        lines.append(f"  Elapsed: {r.elapsed_seconds:.3f}s")
        lines.append("")

        # Inputs applied
        if r.decisions_applied:
            lines.append("  Inputs applied (changes from baseline):")
            for change_line in _format_changes_from_baseline(r.decisions_applied):
                lines.append(change_line)
            lines.append("")

        # Exception
        if r.exception:
            lines.append(f"  Exception: {r.exception}")
            lines.append("")

        # Overwrite check
        if r.overwrite_check:
            owstat = "PASS" if r.overwrite_check.passed else "FAIL"
            lines.append(f"  Decision Overwrite Check: {owstat}")
            if not r.overwrite_check.passed:
                lines.append(f"    {r.overwrite_check.detail}")
            lines.append("")

        # Comparison details
        if r.comparison:
            comp = r.comparison

            # Missing / extra teams
            if comp.missing_teams:
                lines.append(f"  Missing teams in actual: {comp.missing_teams}")
            if comp.extra_teams:
                lines.append(f"  Extra teams in actual: {comp.extra_teams}")

            # Diffs
            if comp.diffs:
                total_diffs = len(comp.diffs)
                shown = min(total_diffs, _MAX_DIFFS_PER_SCENARIO)
                lines.append(f"  Mismatches: {total_diffs} total (showing first {shown})")
                lines.append("")
                lines.append(f"    {'Team':<8} {'Field':<28} {'Expected':<20} {'Actual':<20}")
                lines.append(f"    {'-'*8} {'-'*28} {'-'*20} {'-'*20}")
                for diff in comp.diffs[:shown]:
                    tid = diff.team_id or "(none)"
                    lines.append(
                        f"    {tid:<8} {diff.field:<28} {diff.expected:<20} {diff.actual:<20}"
                    )
                lines.append("")

            # Invariants
            if comp.invariants:
                lines.append("  Invariant checks:")
                for inv in comp.invariants:
                    inv_stat = "PASS" if inv.passed else "FAIL"
                    detail_str = f"  ({inv.detail})" if inv.detail else ""
                    lines.append(f"    [{inv_stat}] {inv.name}{detail_str}")
                lines.append("")

        lines.append("")

    # ── Footer ─────────────────────────────────────────────────────
    lines.append("=" * 72)
    skipped = report.total_scenarios - len(report.results)
    if skipped > 0:
        lines.append(f"  Skipped scenarios: {skipped}")
    else:
        lines.append("  Skipped scenarios: 0")
    lines.append(f"  Total runtime: {report.total_runtime_seconds:.2f}s")
    lines.append("=" * 72)
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the 32-scenario airline simulation test suite",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("tests/reports/simulation_test_report.txt"),
        help="Output report file path (default: tests/reports/simulation_test_report.txt)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=12345,
        help="RNG seed for deterministic random scenarios (default: 12345)",
    )
    parser.add_argument(
        "--stop-on-fail",
        action="store_true",
        default=False,
        help="Stop after first failed scenario",
    )
    parser.add_argument(
        "--keep-sim-folders",
        action="store_true",
        default=False,
        help="Keep temp simulation folders after run (default: delete)",
    )
    args = parser.parse_args()

    print(f"Airline Simulation Test Suite")
    print(f"Seed: {args.seed}")
    print(f"Running {len(ALL_SCENARIOS)} scenarios...")
    print()

    report = run_all_scenarios(
        seed=args.seed,
        stop_on_fail=args.stop_on_fail,
        keep_sim_folders=args.keep_sim_folders,
    )

    write_text_report(report, args.out)

    # Print summary to stdout
    print(f"Results: {report.passed} PASS / {report.failed} FAIL out of {len(report.results)}")
    print(f"Runtime: {report.total_runtime_seconds:.2f}s")
    print(f"Report: {args.out}")

    sys.exit(0 if report.failed == 0 else 1)


if __name__ == "__main__":
    main()
