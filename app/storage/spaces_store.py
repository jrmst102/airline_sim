"""
Spaces Store — DigitalOcean Spaces (S3-compatible) client.
============================================================
Provides a thin abstraction for reading/writing text and binary
objects in a DigitalOcean Spaces bucket.  Falls back to **local
filesystem** when ``SPACES_ACCESS_KEY_ID`` is not set, so
development works without cloud credentials.

Usage::

    from app.storage.spaces_store import get_store

    store = get_store()
    store.write_text("simulations/sim_001/teams.csv", csv_text)
    text = store.read_text("simulations/sim_001/teams.csv")
"""

from __future__ import annotations

import io
import os
import uuid
from pathlib import Path
from typing import Protocol

from app.storage.config import SpacesConfig, load_spaces_config, spaces_configured


# ── Abstract interface ────────────────────────────────────────────────

class Store(Protocol):
    """Minimal key-value store interface."""

    def read_text(self, key: str) -> str: ...
    def write_text(self, key: str, text: str, content_type: str = "text/csv") -> None: ...
    def read_bytes(self, key: str) -> bytes: ...
    def write_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None: ...
    def exists(self, key: str) -> bool: ...
    def list_keys(self, prefix: str) -> list[str]: ...
    def delete(self, key: str) -> None: ...


# ── Local filesystem implementation ──────────────────────────────────

class LocalStore:
    """Store backed by the local filesystem (development fallback).

    Keys are interpreted as paths relative to *root*.
    """

    def __init__(self, root: Path | str = Path(".")) -> None:
        self._root = Path(root)

    def _resolve(self, key: str) -> Path:
        return self._root / key

    def read_text(self, key: str) -> str:
        return self._resolve(key).read_text(encoding="utf-8")

    def write_text(self, key: str, text: str, content_type: str = "text/csv") -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def read_bytes(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def write_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def list_keys(self, prefix: str) -> list[str]:
        base = self._resolve(prefix)
        if not base.exists():
            return []
        if base.is_file():
            return [prefix]
        return sorted(
            str(p.relative_to(self._root))
            for p in base.rglob("*")
            if p.is_file()
        )

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()


# ── DigitalOcean Spaces implementation ───────────────────────────────

class SpacesStore:
    """Store backed by a DigitalOcean Spaces (S3-compatible) bucket."""

    def __init__(self, cfg: SpacesConfig) -> None:
        import boto3

        self._bucket = cfg.bucket
        self._s3 = boto3.client(
            "s3",
            region_name=cfg.region,
            endpoint_url=cfg.endpoint_url,
            aws_access_key_id=cfg.access_key_id,
            aws_secret_access_key=cfg.secret_access_key,
        )

    # ── helpers ────────────────────────────────────────────────────

    def _tmp_key(self, key: str) -> str:
        return f"{key}.tmp.{uuid.uuid4().hex[:12]}"

    # ── public API ─────────────────────────────────────────────────

    def read_text(self, key: str) -> str:
        resp = self._s3.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read().decode("utf-8")

    def write_text(self, key: str, text: str, content_type: str = "text/csv") -> None:
        """Atomic write: upload to tmp key, server-side copy, delete tmp."""
        tmp = self._tmp_key(key)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=tmp,
            Body=text.encode("utf-8"),
            ContentType=content_type,
        )
        self._s3.copy_object(
            Bucket=self._bucket,
            Key=key,
            CopySource={"Bucket": self._bucket, "Key": tmp},
        )
        self._s3.delete_object(Bucket=self._bucket, Key=tmp)

    def read_bytes(self, key: str) -> bytes:
        resp = self._s3.get_object(Bucket=self._bucket, Key=key)
        return resp["Body"].read()

    def write_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        tmp = self._tmp_key(key)
        self._s3.put_object(
            Bucket=self._bucket,
            Key=tmp,
            Body=data,
            ContentType=content_type,
        )
        self._s3.copy_object(
            Bucket=self._bucket,
            Key=key,
            CopySource={"Bucket": self._bucket, "Key": tmp},
        )
        self._s3.delete_object(Bucket=self._bucket, Key=tmp)

    def exists(self, key: str) -> bool:
        try:
            self._s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except self._s3.exceptions.ClientError:
            return False

    def list_keys(self, prefix: str) -> list[str]:
        keys: list[str] = []
        paginator = self._s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                k = obj["Key"]
                if not k.endswith(".tmp"):
                    keys.append(k)
        return sorted(keys)

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self._bucket, Key=key)


# ── Singleton accessor ───────────────────────────────────────────────

_store_instance: Store | None = None


def get_store() -> Store:
    """Return the global Store instance (created on first call).

    When ``SPACES_ACCESS_KEY_ID`` is set → SpacesStore (cloud).
    Otherwise → LocalStore (local filesystem, project root).
    """
    global _store_instance
    if _store_instance is not None:
        return _store_instance

    if spaces_configured():
        cfg = load_spaces_config()
        _store_instance = SpacesStore(cfg)
    else:
        # Use simulations/ dir under project root for local development
        project_root = Path(__file__).resolve().parent.parent.parent
        _store_instance = LocalStore(root=project_root / "simulations")

    return _store_instance


def reset_store() -> None:
    """Reset the cached store instance (useful for testing)."""
    global _store_instance
    _store_instance = None


def set_store(store: Store) -> None:
    """Inject a custom Store instance (useful for testing)."""
    global _store_instance
    _store_instance = store
