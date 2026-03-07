#!/usr/bin/env python3
"""
Backup DigitalOcean Spaces Bucket → local /backup folder
==========================================================
Downloads **every** object from the configured DO Spaces bucket
into ``backup/spaces_backup_YYYYMMDD_HHMMSS/``.

Read-only — never writes to the bucket.

Usage::

    python backup_spaces.py            # uses .env for credentials
    python backup_spaces.py --dry-run  # list objects without downloading

Environment variables (loaded from .env automatically):

    SPACES_ACCESS_KEY_ID      (required)
    SPACES_SECRET_ACCESS_KEY  (required)
    SPACES_REGION             (default: sfo3)
    SPACES_BUCKET             (default: airlines-sim)
    SPACES_ENDPOINT           (default: https://sfo3.digitaloceanspaces.com)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import boto3
from dotenv import load_dotenv

# ── Configuration ────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent
BACKUP_DIR = PROJECT_ROOT / "backup"

load_dotenv(PROJECT_ROOT / ".env")


def _env(name: str, default: str | None = None) -> str:
    val = os.environ.get(name, "").strip()
    if val:
        return val
    if default is not None:
        return default
    print(f"ERROR: Required environment variable {name} is not set.", file=sys.stderr)
    sys.exit(1)


def build_s3_client():
    """Create a read-only boto3 S3 client for DO Spaces."""
    return boto3.client(
        "s3",
        region_name=_env("SPACES_REGION", "sfo3"),
        endpoint_url=_env("SPACES_ENDPOINT", "https://sfo3.digitaloceanspaces.com"),
        aws_access_key_id=_env("SPACES_ACCESS_KEY_ID"),
        aws_secret_access_key=_env("SPACES_SECRET_ACCESS_KEY"),
    )


# ── Listing ──────────────────────────────────────────────────────────

def list_all_keys(s3, bucket: str) -> list[dict]:
    """Return a list of dicts with 'Key' and 'Size' for every object."""
    objects: list[dict] = []
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        for obj in page.get("Contents", []):
            objects.append({"Key": obj["Key"], "Size": obj.get("Size", 0)})
    return objects


# ── Download ─────────────────────────────────────────────────────────

def download_objects(
    s3,
    bucket: str,
    objects: list[dict],
    dest: Path,
    *,
    dry_run: bool = False,
) -> None:
    """Download every object to *dest*, preserving the key as a relative path."""
    total = len(objects)
    total_bytes = sum(o["Size"] for o in objects)
    print(f"\nBucket : {bucket}")
    print(f"Objects: {total}")
    print(f"Size   : {total_bytes / 1024 / 1024:.2f} MB")
    print(f"Dest   : {dest}\n")

    if dry_run:
        print("── Dry-run listing ──")
        for obj in objects:
            print(f"  {obj['Key']}  ({obj['Size']} bytes)")
        print("\nNo files downloaded (dry-run mode).")
        return

    dest.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    errors: list[str] = []

    for idx, obj in enumerate(objects, 1):
        key = obj["Key"]
        local_path = dest / key

        # Skip "directory" markers (keys ending with /)
        if key.endswith("/"):
            continue

        try:
            # If a previous "dir marker" file collides, remove it
            if local_path.parent.is_file():
                local_path.parent.unlink()
            local_path.parent.mkdir(parents=True, exist_ok=True)

            s3.download_file(bucket, key, str(local_path))
            downloaded += 1
            pct = idx / total * 100
            print(f"  [{idx}/{total}] ({pct:5.1f}%) {key}")
        except Exception as exc:
            errors.append(f"{key}: {exc}")
            print(f"  [{idx}/{total}] ERROR {key}: {exc}", file=sys.stderr)

    print(f"\nDownloaded {downloaded}/{total} objects to {dest}")
    if errors:
        print(f"\n{len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backup all objects from a DigitalOcean Spaces bucket."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List objects without downloading.",
    )
    parser.add_argument(
        "--prefix",
        default="",
        help="Only back up keys starting with this prefix.",
    )
    args = parser.parse_args()

    bucket = _env("SPACES_BUCKET", "airlines-sim")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_DIR / f"spaces_backup_{timestamp}"

    s3 = build_s3_client()

    print(f"Connecting to bucket '{bucket}' …")
    objects = list_all_keys(s3, bucket)

    if args.prefix:
        objects = [o for o in objects if o["Key"].startswith(args.prefix)]
        print(f"Filtered to prefix '{args.prefix}': {len(objects)} objects")

    if not objects:
        print("Bucket is empty (or prefix matched nothing). Nothing to back up.")
        return

    download_objects(s3, bucket, objects, dest, dry_run=args.dry_run)

    if not args.dry_run:
        print(f"\nBackup complete → {dest}")


if __name__ == "__main__":
    main()
