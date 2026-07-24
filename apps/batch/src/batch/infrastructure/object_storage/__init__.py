"""Object storage infrastructure (IF-STG scaffold + S3-compatible HTTP)."""

from batch.infrastructure.object_storage.client import (
    ObjectRef,
    ObjectStorageClient,
    ObjectStorageError,
    S3CompatibleObjectStorageClient,
    ScaffoldObjectStorageClient,
    StoredObject,
    create_object_storage_client,
    mask_object_storage_secret,
    missing_live_object_storage_credentials,
    resolve_live_object_storage_flag,
)

__all__ = [
    "ObjectRef",
    "ObjectStorageClient",
    "ObjectStorageError",
    "S3CompatibleObjectStorageClient",
    "ScaffoldObjectStorageClient",
    "StoredObject",
    "create_object_storage_client",
    "mask_object_storage_secret",
    "missing_live_object_storage_credentials",
    "resolve_live_object_storage_flag",
]
