# --------------------------------------------------------------
# services: business logic per le risorse dell'API.
# Tiene main.py snello (solo routing/validazione); qui vivono la
# compilazione frase -> assioma e le operazioni Mongo (CRUD).
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


# --- errori di dominio (mappati dal layer API su codici HTTP) ---
class InvalidAxiomIdError(Exception):
    """L'object id fornito non è un ObjectId valido."""

class AxiomNotFoundError(Exception):
    """Nessun assioma trovato per l'object id dato."""


class AxiomService:
    """CRUD + compilazione per gli assiomi (collezione 'axioms').

    Riceve le dipendenze del pipeline (lo stakeholder `tokeniko` e il client
    Ollama) così da restare indipendente da FastAPI: il layer API costruisce
    una sola istanza all'avvio e la riusa per ogni richiesta.
    """

    def __init__(self, tokeniko, ai_client):
        self._tokeniko = tokeniko
        self._ai_client = ai_client

    # parse + compile di una frase nei campi salvati su un assioma
    def compile_fields(self, tokens: str) -> dict:
        recursiveResult = parser(tokens, self._tokeniko, self._tokeniko, self._ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        if not flatResult:
            raise ValueError("compilation produced no result")
        rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
        return {"original": tokens, "zip": flatResult[1], "raw": rawResult}

    # recupera un assioma per id, o solleva errori di dominio
    def _resolve(self, object_id: str) -> TKAxiomDoc:
        try:
            oid = PydanticObjectId(object_id)
        except Exception as error:
            raise InvalidAxiomIdError(object_id) from error
        axiom = TKAxiomDoc.get(oid)
        if axiom is None:
            raise AxiomNotFoundError(object_id)
        return axiom

    # lista assiomi; filtro opzionale per `archived` e proiezione opzionale
    def list(self, archived: Optional[bool] = None, projection=None):
        query = {} if archived is None else {"archived": archived}
        cursor = TKAxiomDoc.find(query)
        if projection is not None:
            cursor = cursor.project(projection)
        return cursor.to_list()

    # singolo assioma (documento completo, zip incluso)
    def get(self, object_id: str) -> TKAxiomDoc:
        return self._resolve(object_id)

    # inserisce un nuovo assioma a partire da una frase
    def create(self, tokens: str) -> TKAxiomDoc:
        fields = self.compile_fields(tokens)
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

    # update parziale: cambiano solo i campi presenti (ricompila se c'è 'tokens')
    def patch(self, object_id: str, updates: dict) -> TKAxiomDoc:
        axiom = self._resolve(object_id)
        if "tokens" in updates:
            fields = self.compile_fields(updates.pop("tokens"))
            axiom.original = fields["original"]
            axiom.zip = fields["zip"]
            axiom.raw = fields["raw"]
        for key, value in updates.items():
            setattr(axiom, key, value)
        # mantieni coerente il timestamp di archiviazione
        if "archived" in updates:
            axiom.archivedAt = int(time.time()) if axiom.archived else None
        axiom.save()
        return axiom

    # replacement update: ricompila la frase e resetta i flag
    def replace(self, object_id: str, tokens: str, trusted: float, archived: bool, readonly: bool) -> TKAxiomDoc:
        axiom = self._resolve(object_id)
        fields = self.compile_fields(tokens)
        axiom.original = fields["original"]
        axiom.zip = fields["zip"]
        axiom.raw = fields["raw"]
        axiom.trusted = trusted
        axiom.archived = archived
        axiom.readonly = readonly
        axiom.archivedAt = int(time.time()) if archived else None
        axiom.save()
        return axiom

    # elimina un assioma
    def delete(self, object_id: str) -> None:
        axiom = self._resolve(object_id)
        axiom.delete()
