"""Object storage infrastructure scaffold."""

from batch.infrastructure.object_storage.client import (
    ObjectRef,
    ObjectStorageClient,
    ObjectStorageError,
    ScaffoldObjectStorageClient,
    StoredObject,
)

__all__ = [
    "ObjectRef",
    "ObjectStorageClient",
    "ObjectStorageError",
    "ScaffoldObjectStorageClient",
    "StoredObject",
]
