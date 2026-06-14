# --------------------------------------------------------------
# services: business logic for the MEMORY resource.
# Memory items are the time-series log of conversation inputs/outputs
# (the `memory` timeseries collection). Mongo timeseries forbids in-place
# update, so there is NO update operation: list / get / search / insert only.
# Inserting a memory item is a plain log append (no compilation here; the
# /input endpoint owns the pipeline).
# --------------------------------------------------------------
from datetime import datetime, timezone
from typing import Optional

from bunnet import PydanticObjectId

from lib.core.models import TKMemoryItemDoc


# --- domain errors (mapped by the API layer onto HTTP codes) ---
class InvalidMemoryIdError(Exception):
    """The provided object id is not a valid ObjectId."""

class MemoryNotFoundError(Exception):
    """No memory item found for the given object id."""


class MemoryService:
    """List / get / search / insert for memory items (the 'memory' timeseries
    collection).

    Reads and appends only — no update (Mongo timeseries forbids it). Needs no
    pipeline dependencies: insert stores the log entry directly. The API layer
    builds a single instance at startup and reuses it for every request.
    """

    # default cap so a huge log doesn't dump everything at once
    _DEFAULT_LIMIT = 100

    # fetch a memory item by id, or raise a domain error
    def _resolve(self, object_id: str) -> TKMemoryItemDoc:
        try:
            oid = PydanticObjectId(object_id)
        except Exception as error:
            raise InvalidMemoryIdError(object_id) from error
        item = TKMemoryItemDoc.get(oid).run()  # bunnet: get() returns a query, must be executed with run()
        if item is None:
            raise MemoryNotFoundError(object_id)
        return item

    # list recent memory items (newest first); optional projection + limit
    def list(self, projection=None, limit: int = _DEFAULT_LIMIT):
        cursor = TKMemoryItemDoc.find({}).sort("-timestamp").limit(limit)
        if projection is not None:
            cursor = cursor.project(projection)
        return cursor.to_list()

    # single memory item (full document)
    def get(self, object_id: str) -> TKMemoryItemDoc:
        return self._resolve(object_id)

    # search the log by timeframe / source / target / channel (newest first).
    # `frm`/`to` are epoch SECONDS (int), converted to UTC datetimes for the
    # `timestamp` query; only the provided bounds/filters are applied.
    def search(
        self,
        frm: Optional[int] = None,
        to: Optional[int] = None,
        source: Optional[str] = None,
        target: Optional[str] = None,
        channel: Optional[str] = None,
        limit: int = _DEFAULT_LIMIT,
    ):
        query: dict = {}

        timeframe: dict = {}
        if frm is not None:
            timeframe["$gte"] = datetime.fromtimestamp(frm, tz=timezone.utc)
        if to is not None:
            timeframe["$lte"] = datetime.fromtimestamp(to, tz=timezone.utc)
        if timeframe:
            query["timestamp"] = timeframe

        if source is not None:
            query["sourceId"] = source
        if target is not None:
            query["targetId"] = target
        if channel is not None:
            query["channel"] = channel

        return TKMemoryItemDoc.find(query).sort("-timestamp").limit(limit).to_list()

    # append a new memory item (plain log entry; no compilation/parse)
    def create(
        self,
        original: str,
        sourceId: str,
        targetId: Optional[str] = None,
        channel: Optional[str] = None,
        metadata: Optional[str] = None,
    ) -> TKMemoryItemDoc:
        item = TKMemoryItemDoc(
            original=original,
            sourceId=sourceId,
            targetId=targetId,
            channel=channel,
            metadata=metadata,
        )
        item.insert()
        return item
