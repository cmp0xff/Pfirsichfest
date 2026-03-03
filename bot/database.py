"""Database abstraction layer for Pfirsichfest Bot.

Provides a Protocol-based interface for Firestore-compatible operations
and an in-memory implementation for local development and testing.
"""

from __future__ import annotations

import logging
import operator
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

# Operator dispatch table used by InMemoryQuery.stream
_OPS: dict[str, Callable[[Any, Any], bool]] = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


def _no_match(_a: Any, _b: Any) -> bool:
    return False


# ---------------------------------------------------------------------------
# Protocol definitions — matches the Firestore API surface we actually use
# ---------------------------------------------------------------------------


class DocumentSnapshot(Protocol):
    """A snapshot of a single document."""

    @property
    def id(self) -> str: ...

    def to_dict(self) -> dict[str, Any] | None: ...


class DocumentReference(Protocol):
    """A reference to a single document in a collection."""

    def set(self, data: dict[str, Any]) -> Any: ...

    def update(self, data: dict[str, Any]) -> Any: ...


class Query(Protocol):
    """A query that can be streamed."""

    def stream(self) -> Any: ...


class CollectionReference(Protocol):
    """A reference to a collection of documents."""

    def document(self, doc_id: str) -> DocumentReference: ...

    def where(self, field: str, op: str, value: Any) -> Query: ...


@runtime_checkable
class DatabaseClient(Protocol):
    """Minimal database client interface matching Firestore usage."""

    def collection(self, name: str) -> CollectionReference: ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


@dataclass
class InMemoryDocumentSnapshot:
    """In-memory implementation of a Firestore-like document snapshot."""

    _id: str
    _data: dict[str, Any] | None

    @property
    def id(self) -> str:
        return self._id

    def to_dict(self) -> dict[str, Any] | None:
        return dict(self._data) if self._data else None


@dataclass
class InMemoryDatabaseClient:
    """In-memory dict-backed implementation of DatabaseClient.

    Useful for local development and testing without a real Firestore instance.
    Data is held in memory and lost on process restart.
    """

    store: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def collection(self, name: str) -> InMemoryCollectionReference:
        with self.lock:
            if name not in self.store:
                self.store[name] = {}
        return InMemoryCollectionReference(client=self, name=name)


@dataclass
class InMemoryDocumentReference:
    """In-memory implementation of a Firestore-like document reference."""

    client: InMemoryDatabaseClient
    col_name: str
    doc_id: str

    def set(self, data: dict[str, Any]) -> None:
        with self.client.lock:
            self.client.store[self.col_name][self.doc_id] = dict(data)

    def update(self, data: dict[str, Any]) -> None:
        with self.client.lock:
            store = self.client.store
            if self.col_name in store and self.doc_id in store[self.col_name]:
                store[self.col_name][self.doc_id].update(data)
            else:
                # Firestore update on non-existent doc raises; we just set it
                store[self.col_name][self.doc_id] = dict(data)


@dataclass
class InMemoryQuery:
    """In-memory implementation of a Firestore-like query."""

    client: InMemoryDatabaseClient
    col_name: str
    field_name: str
    op: str
    value: Any

    def stream(self) -> list[InMemoryDocumentSnapshot]:
        with self.client.lock:
            docs = self.client.store.get(self.col_name, {})
            cmp = _OPS.get(self.op, _no_match)
            return [
                InMemoryDocumentSnapshot(_id=doc_id, _data=data)
                for doc_id, data in docs.items()
                if cmp(data.get(self.field_name), self.value)
            ]


@dataclass
class InMemoryCollectionReference:
    """In-memory implementation of a Firestore-like collection reference."""

    client: InMemoryDatabaseClient
    name: str

    def document(self, doc_id: str) -> InMemoryDocumentReference:
        return InMemoryDocumentReference(
            client=self.client, col_name=self.name, doc_id=doc_id
        )

    def where(self, field: str, op: str, value: Any) -> InMemoryQuery:
        return InMemoryQuery(
            client=self.client,
            col_name=self.name,
            field_name=field,
            op=op,
            value=value,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_database_client(project_id: str | None) -> DatabaseClient:
    """Creates the appropriate database client based on configuration.

    If a valid GCP project ID is provided, returns a real Firestore client.
    Otherwise, returns an in-memory mock for local development.
    """
    if project_id and project_id != "your-gcp-project-id":
        from google.cloud import firestore  # type: ignore[import-untyped]  # noqa: PLC0415, I001

        client = firestore.Client(project=project_id)
        logger.info("Firestore client initialized for project '%s'.", project_id)
        return client  # type: ignore[return-value]

    logger.info(
        "No valid GOOGLE_CLOUD_PROJECT set. "
        "Using in-memory database for local development."
    )
    return InMemoryDatabaseClient()
