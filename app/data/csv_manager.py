"""
CSV Manager — centralised CSV read/write through the storage layer.
=====================================================================
Every module that reads or writes simulation CSV files should use the
helpers in this module instead of direct filesystem calls.  The
underlying I/O is routed through :pymod:`app.storage.spaces_store`,
which transparently targets either DigitalOcean Spaces or local files.

Drop-in replacements
---------------------
| Old (local)                          | New (this module)                        |
|--------------------------------------|------------------------------------------|
| ``_simulation_path(root, sim_id)``   | ``sim_key(sim_id, filename)``            |
| ``_load_csv(path)``                  | ``load_csv(sim_id, filename)``           |
| ``_write_csv(path, fields, rows)``   | ``write_csv(sim_id, filename, f, rows)`` |
| ``_read_csv_rows(path)``             | ``read_csv_rows(sim_id, filename)``      |
| ``path.exists()``                    | ``csv_exists(sim_id, filename)``         |
"""

from __future__ import annotations

import csv
import io
from typing import Any

from app.storage.spaces_store import get_store


# ── Key helpers ────────────────────────────────────────────────────────

def sim_key(simulation_id: str, filename: str) -> str:
    """Build the object key for a simulation CSV file.

    Example::

        sim_key("sim_001", "teams.csv")
        # → "simulations/sim_001/teams.csv"
    """
    return f"simulations/{simulation_id}/{filename}"


# ── Read helpers ───────────────────────────────────────────────────────

def csv_exists(simulation_id: str, filename: str) -> bool:
    """Return ``True`` when the CSV exists in the store."""
    return get_store().exists(sim_key(simulation_id, filename))


def load_csv(
    simulation_id: str,
    filename: str,
) -> tuple[list[str], list[dict[str, str]]]:
    """Read a CSV file and return ``(fieldnames, rows)``.

    Raises ``FileNotFoundError`` if the key does not exist.
    Raises ``ValueError`` if the file has no header row.
    """
    key = sim_key(simulation_id, filename)
    store = get_store()
    if not store.exists(key):
        raise FileNotFoundError(f"Required file not found: {key}")
    text = store.read_text(key)
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames
    if not fieldnames:
        raise ValueError(f"Missing CSV header in {key}")
    return list(fieldnames), list(reader)


def read_csv_rows(
    simulation_id: str,
    filename: str,
) -> list[dict[str, str]]:
    """Read a CSV and return rows only (empty list if missing)."""
    key = sim_key(simulation_id, filename)
    store = get_store()
    if not store.exists(key):
        return []
    text = store.read_text(key)
    return list(csv.DictReader(io.StringIO(text)))


# ── Write helpers ──────────────────────────────────────────────────────

def _rows_to_csv_text(
    fieldnames: list[str], rows: list[dict[str, Any]]
) -> str:
    """Serialize rows to a CSV string (with header)."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    if rows:
        writer.writerows(rows)
    return buf.getvalue()


def write_csv(
    simulation_id: str,
    filename: str,
    fieldnames: list[str],
    rows: list[dict[str, Any]],
) -> None:
    """Write a CSV file (atomically when using Spaces)."""
    key = sim_key(simulation_id, filename)
    text = _rows_to_csv_text(fieldnames, rows)
    get_store().write_text(key, text, content_type="text/csv")


# ── Key-value parameter helpers ────────────────────────────────────────

def load_parameters(simulation_id: str) -> dict[str, str]:
    """Parse the key-value ``parameters.csv`` into a lookup dict.

    Expected CSV format: ``key,value,notes``
    Returns ``{key: value, …}``.
    """
    key = sim_key(simulation_id, "parameters.csv")
    store = get_store()
    if not store.exists(key):
        raise FileNotFoundError(f"Parameters file not found: {key}")
    text = store.read_text(key)
    result: dict[str, str] = {}
    for row in csv.DictReader(io.StringIO(text)):
        k = row.get("key", "").strip()
        v = row.get("value", "").strip()
        if k:
            result[k] = v
    return result


# ── Raw text helpers (for non-CSV or external files) ───────────────────

def read_text(key: str) -> str:
    """Read raw text from an arbitrary key."""
    return get_store().read_text(key)


def write_text(key: str, text: str, content_type: str = "text/csv") -> None:
    """Write raw text to an arbitrary key."""
    get_store().write_text(key, text, content_type=content_type)


def store_exists(key: str) -> bool:
    """Check if an arbitrary key exists."""
    return get_store().exists(key)


def list_keys(prefix: str) -> list[str]:
    """List all keys matching a prefix."""
    return get_store().list_keys(prefix)
