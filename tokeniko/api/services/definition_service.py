# --------------------------------------------------------------
# services: business logic for the definitions resource.
# A definition is a single-sentence, purely semantic statement (no operators):
# its meaning is a single TKZipContent, not a full TKZip.
# --------------------------------------------------------------
import copy
import time
from typing import Optional

from bunnet import PydanticObjectId

from lib.llc.parser import parser
from lib.llc.compiler import compiler_compile
from lib.llc.decompiler import decompiler_raw
from lib.core.models import TKDefinitionDoc
from lib.core.memory import MEMChannels
from lib.core.tk import TKStatement
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip, TKZipContent


# --- domain errors (mapped by the API layer onto HTTP codes) ---
class InvalidDefinitionIdError(Exception):
    """The provided object id is not a valid ObjectId."""

class DefinitionNotFoundError(Exception):
    """No definition found for the given object id."""

class NotASingleClauseError(Exception):
    """The sentence is not a single semantic clause (a definition must have no operators)."""


# the single leaf TKZipContent of a one-clause statement; rejects multi-clause / operator-bearing zips
def _extract_definition_content(tkzip: TKZip) -> TKZipContent:
    items = tkzip.items.content
    if isinstance(items, list) and len(items) == 1 and isinstance(items[0].content, TKZipContent):
        return items[0].content
    raise NotASingleClauseError("a definition must be a single semantic clause (no operators, one clause)")


class DefinitionService:
    """CRUD + compilation for definitions (the 'definitions' collection).

    Mirrors AxiomService, but stores the single clause's TKZipContent (definitions are purely
    semantic, with no relational operators). Framework-agnostic: built once at startup and reused.
    """

    def __init__(self, tokeniko, ai_client):
        self._tokeniko = tokeniko
        self._ai_client = ai_client

    # parse + compile a sentence into the fields stored on a definition (single TKZipContent)
    def compile_fields(self, tokens: str) -> dict:
        recursiveResult = parser(tokens, self._tokeniko, self._tokeniko, self._ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        if not flatResult:
            raise ValueError("compilation produced no result")
        content = _extract_definition_content(flatResult[1])
        rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
        return {"original": tokens, "content": content, "raw": rawResult}

    # fetch a definition by id, or raise a domain error
    def _resolve(self, object_id: str) -> TKDefinitionDoc:
        try:
            oid = PydanticObjectId(object_id)
        except Exception as error:
            raise InvalidDefinitionIdError(object_id) from error
        definition = TKDefinitionDoc.get(oid).run()  # bunnet: get() returns a query, run() executes it
        if definition is None:
            raise DefinitionNotFoundError(object_id)
        return definition

    # list definitions; optional `archived` filter and optional projection
    def list(self, archived: Optional[bool] = None, projection=None):
        query = {} if archived is None else {"archived": archived}
        cursor = TKDefinitionDoc.find(query)
        if projection is not None:
            cursor = cursor.project(projection)
        return cursor.to_list()

    # single definition (full document, content included)
    def get(self, object_id: str) -> TKDefinitionDoc:
        return self._resolve(object_id)

    # insert a new definition from a sentence
    def create(self, tokens: str) -> TKDefinitionDoc:
        fields = self.compile_fields(tokens)
        definition = TKDefinitionDoc(
            original=fields["original"],
            content=fields["content"],
            raw=fields["raw"],
            sourceId=str(self._tokeniko.id),
            targetId=str(self._tokeniko.id),
            channel=MEMChannels.INTERNAL,
        )
        definition.insert()
        return definition

    # partial update: only the provided fields change (recompiles if 'tokens' is present)
    def patch(self, object_id: str, updates: dict) -> TKDefinitionDoc:
        definition = self._resolve(object_id)
        if "tokens" in updates:
            fields = self.compile_fields(updates.pop("tokens"))
            definition.original = fields["original"]
            definition.content = fields["content"]
            definition.raw = fields["raw"]
        for key, value in updates.items():
            setattr(definition, key, value)
        if "archived" in updates:
            definition.archivedAt = int(time.time()) if definition.archived else None
        definition.save()
        return definition

    # replacement update: recompile the sentence and reset the flags
    def replace(self, object_id: str, tokens: str, trusted: float, archived: bool, readonly: bool) -> TKDefinitionDoc:
        definition = self._resolve(object_id)
        fields = self.compile_fields(tokens)
        definition.original = fields["original"]
        definition.content = fields["content"]
        definition.raw = fields["raw"]
        definition.trusted = trusted
        definition.archived = archived
        definition.readonly = readonly
        definition.archivedAt = int(time.time()) if archived else None
        definition.save()
        return definition

    # delete a definition
    def delete(self, object_id: str) -> None:
        definition = self._resolve(object_id)
        definition.delete()
