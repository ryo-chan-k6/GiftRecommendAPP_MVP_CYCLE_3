"""Object storage client scaffold."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class ObjectRef:
    """Reference to a stored object."""

    bucket: str
    key: str


@dataclass(frozen=True)
class StoredObject:
    """Object payload placeholder."""

    ref: ObjectRef
    content_type: str
    body: bytes


class ObjectStorageError(Exception):
    """Raised when Object Storage put/get fails (mapped to GRS-RAW-* in job layer)."""

    def __init__(self, *, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class ObjectStorageClient(Protocol):
    """Object storage boundary for Raw JSON persistence (Phase4a protocol)."""

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> StoredObject: ...

    def get_object(self, ref: ObjectRef) -> StoredObject | None: ...


@dataclass
class ScaffoldObjectStorageClient:
    """Phase4a in-memory object store for unit tests."""

    objects: dict[tuple[str, str], StoredObject] = field(default_factory=dict)
    put_calls: list[dict[str, object]] = field(default_factory=list)
    get_calls: list[ObjectRef] = field(default_factory=list)
    fail_on_put: bool = False

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> StoredObject:
        if self.fail_on_put:
            raise ObjectStorageError(code="GRS-RAW-001", message="scaffold forced put failure")
        stored = StoredObject(ref=ref, content_type=content_type, body=body)
        self.objects[(ref.bucket, ref.key)] = stored
        self.put_calls.append(
            {
                "ref": ref,
                "body": body,
                "content_type": content_type,
            }
        )
        return stored

    def get_object(self, ref: ObjectRef) -> StoredObject | None:
        self.get_calls.append(ref)
        return self.objects.get((ref.bucket, ref.key))
