from __future__ import annotations

import argparse
from pathlib import Path


DIRECTORIES = [
	"app",
	"app/core",
	"app/data",
	"app/modules",
	"app/auth",
	"app/ui",
	"simulations",
	"backups",
	"archive",
	"tests",
]


FILES = [
	"app/main.py",
	"app/config.py",
	"app/core/simulation_engine.py",
	"app/core/demand_model.py",
	"app/core/pricing_model.py",
	"app/core/cost_model.py",
	"app/core/indices_model.py",
	"app/core/round_manager.py",
	"app/core/state_machine.py",
	"app/data/csv_manager.py",
	"app/data/file_structure.py",
	"app/data/schema_validator.py",
	"app/data/backup_manager.py",
	"app/modules/setup_simulation.py",
	"app/modules/start_simulation.py",
	"app/modules/move_next_round.py",
	"app/modules/undo_round.py",
	"app/modules/end_simulation.py",
	"app/modules/enter_decisions.py",
	"app/modules/display_results.py",
	"app/modules/change_parameters_live.py",
	"app/modules/backup_simulation.py",
	"app/modules/restore_simulation.py",
	"app/modules/destroy_simulation.py",
	"app/modules/user_management.py",
	"app/auth/login_manager.py",
	"app/auth/password_manager.py",
	"app/auth/permissions.py",
	"app/ui/admin_view.py",
	"app/ui/team_view.py",
	"app/ui/dashboard.py",
	"app/ui/components.py",
	"requirements.txt",
]


def create_structure(repo_root: Path) -> tuple[int, int]:
	created_dirs = 0
	created_files = 0

	for directory in DIRECTORIES:
		dir_path = repo_root / directory
		if not dir_path.exists():
			dir_path.mkdir(parents=True, exist_ok=True)
			created_dirs += 1

	for file_path in FILES:
		path = repo_root / file_path
		if not path.exists():
			path.parent.mkdir(parents=True, exist_ok=True)
			path.touch()
			created_files += 1

	return created_dirs, created_files


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Create airline_sim folder structure from docs/SPECIFICATION.md"
	)
	parser.add_argument(
		"--root",
		type=Path,
		default=Path(__file__).resolve().parents[1],
		help="Repository root path (defaults to project root)",
	)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	repo_root = args.root.resolve()
	created_dirs, created_files = create_structure(repo_root)

	print(f"Repository root: {repo_root}")
	print(f"Created directories: {created_dirs}")
	print(f"Created files: {created_files}")


if __name__ == "__main__":
	main()
