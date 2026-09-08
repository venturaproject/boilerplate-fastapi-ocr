"""Pluggable storage for OCR job uploads: `STORAGE_BACKEND=local|s3`.

Keys are `{job_id}/{filename}`. `LocalStorage` also accepts an absolute path as
a key (jobs created before this refactor stored the full path).
"""

from __future__ import annotations

import functools
import os
import shutil
import uuid
from typing import Protocol

import anyio.to_thread

from app.config import settings


class StorageBackend(Protocol):
    def save(self, key: str, data: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete_prefix(self, prefix: str) -> None: ...


class LocalStorage:
    name = "local"

    def __init__(self) -> None:
        self.root = settings.ocr_storage_dir

    def _path(self, key: str) -> str:
        return key if os.path.isabs(key) else os.path.join(self.root, key)

    def save(self, key: str, data: bytes) -> None:
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as fh:
            fh.write(data)

    def read(self, key: str) -> bytes:
        with open(self._path(key), "rb") as fh:
            return fh.read()

    def delete_prefix(self, prefix: str) -> None:
        shutil.rmtree(self._path(prefix.rstrip("/")), ignore_errors=True)


class S3Storage:
    name = "s3"

    def __init__(self) -> None:
        import boto3

        self.bucket = settings.s3_bucket
        self.prefix = (settings.s3_prefix or "").lstrip("/")
        kwargs: dict = {}
        if settings.s3_endpoint_url:
            kwargs["endpoint_url"] = settings.s3_endpoint_url
        if settings.s3_region:
            kwargs["region_name"] = settings.s3_region
        if settings.s3_access_key_id and settings.s3_secret_access_key:
            kwargs["aws_access_key_id"] = settings.s3_access_key_id
            kwargs["aws_secret_access_key"] = settings.s3_secret_access_key
        self._client = boto3.client("s3", **kwargs)

    def _key(self, key: str) -> str:
        return f"{self.prefix}{key}" if self.prefix else key

    def save(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self.bucket, Key=self._key(key), Body=data)

    def read(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self.bucket, Key=self._key(key))
        return obj["Body"].read()

    def delete_prefix(self, prefix: str) -> None:
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self._key(prefix)):
            objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
            if objs:
                self._client.delete_objects(Bucket=self.bucket, Delete={"Objects": objs})


@functools.lru_cache(maxsize=1)
def get_storage() -> StorageBackend:
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage()


def _safe_name(filename: str | None) -> str:
    name = os.path.basename(filename or "").strip()
    if not name or name in (".", ".."):
        return "upload"
    if len(name) > 200:  # keep well under filesystem NAME_MAX
        root, ext = os.path.splitext(name)
        name = root[: 200 - len(ext)] + ext
    return name


async def save_upload(job_id: uuid.UUID, filename: str | None, data: bytes) -> str:
    key = f"{job_id}/{_safe_name(filename)}"
    await anyio.to_thread.run_sync(get_storage().save, key, data)
    return key


def read_file(key: str) -> bytes:
    return get_storage().read(key)


def delete_job_files(job_id: uuid.UUID) -> None:
    get_storage().delete_prefix(f"{job_id}/")
