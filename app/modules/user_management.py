from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import bcrypt


VALID_ROLES = {"ADMIN", "TEAM_LEAD", "TEAM_MEMBER"}


@dataclass(frozen=True)
class UserRecord:
	simulation_id: str
	user_id: str
	username: str
	role: str
	team_id: str
	password_hash: str
	is_locked: str
	created_at_utc: str

	@property
	def locked(self) -> bool:
		return self.is_locked == "1"


def _utc_now() -> str:
	return datetime.now(timezone.utc).isoformat()


def _simulation_path(root_dir: Path | str, simulation_id: str) -> Path:
	return Path(root_dir) / simulation_id


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
	if not path.exists():
		raise FileNotFoundError(f"Required file not found: {path}")
	with path.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		return list(reader)


def _write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
	with path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=fieldnames)
		writer.writeheader()
		writer.writerows(rows)


def _next_numeric_suffix(existing_ids: list[str], prefix: str) -> int:
	max_suffix = 0
	for user_id in existing_ids:
		if user_id.startswith(prefix):
			suffix = user_id.removeprefix(prefix)
			if suffix.isdigit():
				max_suffix = max(max_suffix, int(suffix))
	return max_suffix + 1


def _load_users(users_csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
	with users_csv_path.open("r", newline="", encoding="utf-8") as handle:
		reader = csv.DictReader(handle)
		fieldnames = reader.fieldnames
		if not fieldnames:
			raise ValueError(f"Missing users.csv header in {users_csv_path}")
		return fieldnames, list(reader)


def _append_login_event(
	simulation_dir: Path,
	simulation_id: str,
	user_id: str,
	username: str,
	event_type: str,
) -> None:
	log_path = simulation_dir / "login_log.csv"
	rows = _read_csv_rows(log_path)
	next_id = f"E{len(rows) + 1}"
	now = _utc_now()
	rows.append(
		{
			"event_id": next_id,
			"simulation_id": simulation_id,
			"user_id": user_id,
			"username": username,
			"event_type": event_type,
			"event_at_utc": now,
		}
	)
	_write_csv_rows(
		log_path,
		["event_id", "simulation_id", "user_id", "username", "event_type", "event_at_utc"],
		rows,
	)


def list_users(simulation_id: str, root_dir: Path | str = Path("simulations")) -> list[UserRecord]:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	users_rows = _read_csv_rows(simulation_dir / "users.csv")
	return [
		UserRecord(
			simulation_id=row["simulation_id"],
			user_id=row["user_id"],
			username=row["username"],
			role=row["role"],
			team_id=row["team_id"],
			password_hash=row["password_hash"],
			is_locked=row["is_locked"],
			created_at_utc=row["created_at_utc"],
		)
		for row in users_rows
	]


def create_user(
	simulation_id: str,
	username: str,
	password: str,
	role: str,
	team_id: str = "",
	root_dir: Path | str = Path("simulations"),
) -> UserRecord:
	normalized_role = role.upper()
	if normalized_role not in VALID_ROLES:
		raise ValueError(f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}")
	if not username.strip():
		raise ValueError("username cannot be empty")
	if len(password) < 8:
		raise ValueError("password must be at least 8 characters")
	if normalized_role in {"TEAM_LEAD", "TEAM_MEMBER"} and not team_id.strip():
		raise ValueError("team_id is required for TEAM_LEAD and TEAM_MEMBER")

	simulation_dir = _simulation_path(root_dir, simulation_id)
	users_csv = simulation_dir / "users.csv"

	fieldnames, rows = _load_users(users_csv)
	existing_usernames = {row["username"].casefold() for row in rows}
	if username.casefold() in existing_usernames:
		raise ValueError(f"username '{username}' already exists")

	next_num = _next_numeric_suffix([row["user_id"] for row in rows], "U")
	new_user_id = f"U{next_num:03d}"
	password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
	now = _utc_now()

	new_row = {
		"simulation_id": simulation_id,
		"user_id": new_user_id,
		"username": username,
		"role": normalized_role,
		"team_id": team_id,
		"password_hash": password_hash,
		"is_locked": "0",
		"created_at_utc": now,
	}
	rows.append(new_row)
	_write_csv_rows(users_csv, fieldnames, rows)

	return UserRecord(**new_row)


def set_user_lock(
	simulation_id: str,
	username: str,
	is_locked: bool,
	root_dir: Path | str = Path("simulations"),
) -> UserRecord:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	users_csv = simulation_dir / "users.csv"
	fieldnames, rows = _load_users(users_csv)

	target_index = -1
	for index, row in enumerate(rows):
		if row["username"].casefold() == username.casefold():
			target_index = index
			break

	if target_index < 0:
		raise ValueError(f"username '{username}' not found")

	rows[target_index]["is_locked"] = "1" if is_locked else "0"
	_write_csv_rows(users_csv, fieldnames, rows)
	return UserRecord(**rows[target_index])


def authenticate_user(
	simulation_id: str,
	username: str,
	password: str,
	root_dir: Path | str = Path("simulations"),
) -> UserRecord | None:
	simulation_dir = _simulation_path(root_dir, simulation_id)
	users = list_users(simulation_id=simulation_id, root_dir=root_dir)

	matched = next((user for user in users if user.username.casefold() == username.casefold()), None)
	if matched is None:
		_append_login_event(simulation_dir, simulation_id, "", username, "LOGIN_FAILURE_UNKNOWN_USER")
		return None

	if matched.locked:
		_append_login_event(simulation_dir, simulation_id, matched.user_id, matched.username, "LOGIN_FAILURE_LOCKED")
		return None

	if not matched.password_hash:
		_append_login_event(simulation_dir, simulation_id, matched.user_id, matched.username, "LOGIN_FAILURE_NO_PASSWORD")
		return None

	password_ok = bcrypt.checkpw(password.encode("utf-8"), matched.password_hash.encode("utf-8"))
	if password_ok:
		_append_login_event(simulation_dir, simulation_id, matched.user_id, matched.username, "LOGIN_SUCCESS")
		return matched

	_append_login_event(simulation_dir, simulation_id, matched.user_id, matched.username, "LOGIN_FAILURE_BAD_PASSWORD")
	return None


def _build_cli() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description="User management for airline simulation")
	parser.add_argument("simulation_id", help="Simulation identifier")
	parser.add_argument(
		"--root",
		type=Path,
		default=Path("simulations"),
		help="Root simulations directory",
	)

	subparsers = parser.add_subparsers(dest="command", required=True)

	create_parser = subparsers.add_parser("create", help="Create a user")
	create_parser.add_argument("--username", required=True)
	create_parser.add_argument("--password", required=True)
	create_parser.add_argument("--role", required=True, choices=sorted(VALID_ROLES))
	create_parser.add_argument("--team-id", default="")

	list_parser = subparsers.add_parser("list", help="List users")
	list_parser.add_argument("--include-hash", action="store_true")

	lock_parser = subparsers.add_parser("lock", help="Lock a user")
	lock_parser.add_argument("--username", required=True)

	unlock_parser = subparsers.add_parser("unlock", help="Unlock a user")
	unlock_parser.add_argument("--username", required=True)

	auth_parser = subparsers.add_parser("auth", help="Authenticate user credentials")
	auth_parser.add_argument("--username", required=True)
	auth_parser.add_argument("--password", required=True)

	return parser


def main() -> None:
	parser = _build_cli()
	args = parser.parse_args()

	if args.command == "create":
		user = create_user(
			simulation_id=args.simulation_id,
			username=args.username,
			password=args.password,
			role=args.role,
			team_id=args.team_id,
			root_dir=args.root,
		)
		print(f"Created user {user.user_id} ({user.username}, {user.role})")
		return

	if args.command == "list":
		users = list_users(simulation_id=args.simulation_id, root_dir=args.root)
		for user in users:
			fields = [user.user_id, user.username, user.role, user.team_id, f"locked={user.locked}"]
			if args.include_hash:
				fields.append(user.password_hash)
			print(" | ".join(fields))
		return

	if args.command == "lock":
		user = set_user_lock(
			simulation_id=args.simulation_id,
			username=args.username,
			is_locked=True,
			root_dir=args.root,
		)
		print(f"Locked user {user.user_id} ({user.username})")
		return

	if args.command == "unlock":
		user = set_user_lock(
			simulation_id=args.simulation_id,
			username=args.username,
			is_locked=False,
			root_dir=args.root,
		)
		print(f"Unlocked user {user.user_id} ({user.username})")
		return

	if args.command == "auth":
		user = authenticate_user(
			simulation_id=args.simulation_id,
			username=args.username,
			password=args.password,
			root_dir=args.root,
		)
		if user:
			print(f"AUTH_SUCCESS {user.user_id} {user.username} {user.role}")
		else:
			print("AUTH_FAILURE")
		return

	raise RuntimeError(f"Unsupported command '{args.command}'")


if __name__ == "__main__":
	main()
