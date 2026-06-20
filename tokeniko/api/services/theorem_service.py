# --------------------------------------------------------------
# services: business logic for the theorems resource.
# Mirrors AxiomService (theorems store a full TKZip). Unlike axioms, theorems have no `readonly`
# flag and default to archived=True / trusted=0.9.
# --------------------------------------------------------------
import copy
import time
from typing import Optional

from bunnet import PydanticObjectId

from lib.llc.parser import parser
from lib.llc.compiler import compiler_compile
from lib.llc.decompiler import decompiler_raw
from lib.core.models import TKTheoremDoc
from lib.core.memory import MEMChannels
from lib.core.tk import TKStatement
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip
from api.services.validation import assert_no_contradiction


# --- domain errors (mapped by the API layer onto HTTP codes) ---
class InvalidTheoremIdError(Exception):
    """The provided object id is not a valid ObjectId."""

class TheoremNotFoundError(Exception):
    """No theorem found for the given object id."""


class TheoremService:
    """CRUD + compilation for theorems (the 'theorems' collection)."""

    def __init__(self, tokeniko, ai_client):
        self._tokeniko = tokeniko
        self._ai_client = ai_client

    # parse + compile a sentence into the fields stored on a theorem
    def compile_fields(self, tokens: str) -> dict:
        recursiveResult = parser(tokens, self._tokeniko, self._tokeniko, self._ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        if not flatResult:
            raise ValueError("compilation produced no result")
        rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
        return {"original": tokens, "zip": flatResult[1], "raw": rawResult}

    # fetch a theorem by id, or raise a domain error
    def _resolve(self, object_id: str) -> TKTheoremDoc:
        try:
            oid = PydanticObjectId(object_id)
        except Exception as error:
            raise InvalidTheoremIdError(object_id) from error
        theorem = TKTheoremDoc.get(oid).run()  # bunnet: get() returns a query, run() executes it
        if theorem is None:
            raise TheoremNotFoundError(object_id)
        return theorem

    # list theorems; optional `archived` filter and optional projection
    def list(self, archived: Optional[bool] = None, projection=None):
        query = {} if archived is None else {"archived": archived}
        cursor = TKTheoremDoc.find(query)
        if projection is not None:
            cursor = cursor.project(projection)
        return cursor.to_list()

    # single theorem (full document, zip included)
    def get(self, object_id: str) -> TKTheoremDoc:
        return self._resolve(object_id)

    # insert a new theorem from a sentence
    def create(self, tokens: str) -> TKTheoremDoc:
        fields = self.compile_fields(tokens)
        assert_no_contradiction(fields["zip"])  # logic-is-sacred: never store a contradictory form
        theorem = TKTheoremDoc(
            original=fields["original"],
            zip=fields["zip"],
            raw=fields["raw"],
            sourceId=str(self._tokeniko.id),
            targetId=str(self._tokeniko.id),
            channel=MEMChannels.INTERNAL,
        )
        theorem.insert()
        return theorem

    # partial update: only the provided fields change (recompiles if 'tokens' is present)
    def patch(self, object_id: str, updates: dict) -> TKTheoremDoc:
        theorem = self._resolve(object_id)
        if "tokens" in updates:
            fields = self.compile_fields(updates.pop("tokens"))
            assert_no_contradiction(fields["zip"])  # reject a contradictory form before saving
            theorem.original = fields["original"]
            theorem.zip = fields["zip"]
            theorem.raw = fields["raw"]
        for key, value in updates.items():
            setattr(theorem, key, value)
        if "archived" in updates:
            theorem.archivedAt = int(time.time()) if theorem.archived else None
        theorem.save()
        return theorem

    # replacement update: recompile the sentence and reset the flags
    def replace(self, object_id: str, tokens: str, trusted: float, archived: bool) -> TKTheoremDoc:
        theorem = self._resolve(object_id)
        fields = self.compile_fields(tokens)
        assert_no_contradiction(fields["zip"])  # reject a contradictory form before saving
        theorem.original = fields["original"]
        theorem.zip = fields["zip"]
        theorem.raw = fields["raw"]
        theorem.trusted = trusted
        theorem.archived = archived
        theorem.archivedAt = int(time.time()) if archived else None
        theorem.save()
        return theorem

    # delete a theorem
    def delete(self, object_id: str) -> None:
        theorem = self._resolve(object_id)
        theorem.delete()
