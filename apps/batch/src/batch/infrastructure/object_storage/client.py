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

    def put_object(
        self,
        ref: ObjectRef,
        *,
        body: bytes,
        content_type: str,
    ) -> StoredObject:
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
