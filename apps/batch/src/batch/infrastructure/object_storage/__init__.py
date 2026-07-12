"""Object storage infrastructure scaffold."""

from batch.infrastructure.object_storage.client import (
    ObjectRef,
    ObjectStorageClient,
    ScaffoldObjectStorageClient,
    StoredObject,
)

__all__ = [
    "ObjectRef",
    "ObjectStorageClient",
    "ScaffoldObjectStorageClient",
    "StoredObject",
]
