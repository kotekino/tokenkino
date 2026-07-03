# --------------------------------------------------------------
# services: business logic for the API resources.
# Keeps main.py thin (routing/validation only); the sentence -> axiom
# compilation and the Mongo operations (CRUD) live here.
# --------------------------------------------------------------
import copy
import time
from typing import Optional

from bunnet import PydanticObjectId

from lib.llc.parser import parser
from lib.llc.compiler import compiler_compile
from lib.llc.decompiler import decompiler_raw
from lib.core.models import TKAxiomDoc
from lib.core.memory import MEMChannels
from lib.core.tk import TKStatement
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip
from lib.core.evaluation_harness import revoke_dependents
from api.services.validation import assert_no_contradiction


# --- domain errors (mapped by the API layer onto HTTP codes) ---
class InvalidAxiomIdError(Exception):
    """The provided object id is not a valid ObjectId."""

class AxiomNotFoundError(Exception):
    """No axiom found for the given object id."""


class AxiomService:
    """CRUD + compilation for axioms (the 'axioms' collection).

    Receives the pipeline dependencies (the `tokeniko` stakeholder and the
    Ollama client) so it stays independent of FastAPI: the API layer builds
    a single instance at startup and reuses it for every request.
    """

    def __init__(self, tokeniko, ai_client):
        self._tokeniko = tokeniko
        self._ai_client = ai_client

    # parse + compile a sentence into the fields stored on an axiom
    def compile_fields(self, tokens: str) -> dict:
        recursiveResult = parser(tokens, self._tokeniko, self._tokeniko, self._ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        if not flatResult:
            raise ValueError("compilation produced no result")
        rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
        return {"original": tokens, "zip": flatResult[1], "raw": rawResult}

    # fetch an axiom by id, or raise a domain error
    def _resolve(self, object_id: str) -> TKAxiomDoc:
        try:
            oid = PydanticObjectId(object_id)
        except Exception as error:
            raise InvalidAxiomIdError(object_id) from error
        axiom = TKAxiomDoc.get(oid).run()  # bunnet: get() returns a query, must be executed with run()
        if axiom is None:
            raise AxiomNotFoundError(object_id)
        return axiom

    # list axioms; optional `archived` filter and optional projection
    def list(self, archived: Optional[bool] = None, projection=None):
        query = {} if archived is None else {"archived": archived}
        cursor = TKAxiomDoc.find(query)
        if projection is not None:
            cursor = cursor.project(projection)
        return cursor.to_list()

    # single axiom (full document, zip included)
    def get(self, object_id: str) -> TKAxiomDoc:
        return self._resolve(object_id)

    # insert a new axiom from a sentence
    def create(self, tokens: str) -> TKAxiomDoc:
        fields = self.compile_fields(tokens)
        assert_no_contradiction(fields["zip"])  # logic-is-sacred: never store a contradictory form
        axiom = TKAxiomDoc(
            original=fields["original"],
            zip=fields["zip"],
            raw=fields["raw"],
            sourceId=str(self._tokeniko.id),
            targetId=str(self._tokeniko.id),
            channel=MEMChannels.INTERNAL,
        )
        axiom.insert()
        return axiom

    # partial update: only the provided fields change (recompiles if 'tokens' is present)
    def patch(self, object_id: str, updates: dict) -> TKAxiomDoc:
        axiom = self._resolve(object_id)
        if "tokens" in updates:
            fields = self.compile_fields(updates.pop("tokens"))
            assert_no_contradiction(fields["zip"])  # reject a contradictory form before saving
            axiom.original = fields["original"]
            axiom.zip = fields["zip"]
            axiom.raw = fields["raw"]
        for key, value in updates.items():
            setattr(axiom, key, value)
        # keep the archive timestamp consistent
        if "archived" in updates:
            axiom.archivedAt = int(time.time()) if axiom.archived else None
        axiom.save()
        # transitive cascade (step 3): retracting an axiom retracts everything proven on it —
        # dependent theorems, then THEIR dependents (theorems breed theorems; the proof net holds).
        if updates.get("archived") is True:
            revoke_dependents([str(axiom.id)], dry_run=False)
        return axiom

    # replacement update: recompile the sentence and reset the flags
    def replace(self, object_id: str, tokens: str, trusted: float, archived: bool, readonly: bool) -> TKAxiomDoc:
        axiom = self._resolve(object_id)
        fields = self.compile_fields(tokens)
        assert_no_contradiction(fields["zip"])  # reject a contradictory form before saving
        axiom.original = fields["original"]
        axiom.zip = fields["zip"]
        axiom.raw = fields["raw"]
        axiom.trusted = trusted
        axiom.archived = archived
        axiom.readonly = readonly
        axiom.archivedAt = int(time.time()) if archived else None
        axiom.save()
        if archived:
            revoke_dependents([str(axiom.id)], dry_run=False)  # transitive cascade (step 3)
        return axiom

    # delete an axiom (the cascade first — after the delete the id would still match, but keep the
    # retraction ordered: dependents fall before their ground does)
    def delete(self, object_id: str) -> None:
        axiom = self._resolve(object_id)
        revoke_dependents([str(axiom.id)], dry_run=False)
        axiom.delete()
