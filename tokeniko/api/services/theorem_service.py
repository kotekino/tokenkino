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
from lib.core.models import TKTheoremDoc, TKDictionaryDoc
from lib.core.memory import MEMChannels, MEMProvenance
from lib.core.tk import TKStatement
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip
from lib.core.evaluation_harness import conclusion_key, revoke_dependents, _zip_leaves
from lib.core.zip_native import assemble_conclusion_zip
from api.services.validation import assert_no_contradiction


# --- domain errors (mapped by the API layer onto HTTP codes) ---
class InvalidTheoremIdError(Exception):
    """The provided object id is not a valid ObjectId."""

class TheoremNotFoundError(Exception):
    """No theorem found for the given object id."""

class UngroundableConclusionError(Exception):
    """Native assembly refused: a named role has no dictionary vector (a belief is never assembled over a hole)."""


# the subject role tensor layout (tkzip.py): 300 markers + 2925 semantic + 12 spacetime
_SEM_LO, _SEM_HI = 300, 300 + 2925


# PIN the derived conclusion's KNOWN senses into the compiled zip (materialize only). The wondering
# derives a conclusion SYMBOLICALLY (exact subject/predicate/object senses, straight from the proof),
# renders it to NL, and the render is then re-parsed here — a lossy round-trip: "a budget stores
# information" parses "stores" as the plural NOUN (shop), losing the subject and corrupting the
# semantic dedup key (every "X stores information" collapsed onto one stored mutant). The derivation's
# senses ARE the truth; the NL is only its surface — so after compiling for geometry, re-home the role
# senses (+ their 2925 vectors, same in-place style as the definition pin / genus untangle).
def _pin_conclusion_senses(zip_obj, senses: dict) -> None:
    targets = {}
    subj = senses.get("subject")
    if subj and ".n." in subj:
        targets["subject"] = subj            # a CLASS subject; an individual uid rides identities
    if senses.get("predicate"):
        targets["predicate"] = senses["predicate"]
    if senses.get("object"):
        targets["direct"] = senses["object"]
    if not targets:
        return
    vec_cache: dict[str, Optional[list]] = {}

    def _vec(sense):
        if sense not in vec_cache:
            doc = TKDictionaryDoc.find_one({"sense": sense}).run()
            vec_cache[sense] = doc.vector if (doc and doc.vector) else None
        return vec_cache[sense]

    for leaf in _zip_leaves(zip_obj.items):
        for role, sense in targets.items():
            if (leaf.senses or {}).get(role) == sense:
                continue
            leaf.senses[role] = sense
            vec = _vec(sense)
            tensor = getattr(leaf, role, None)
            if vec and tensor and len(tensor) == 3237:
                tensor[_SEM_LO:_SEM_HI] = vec  # keep label + geometry in sync


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

    # MATERIALIZE a DERIVED conclusion as a first-class theorem (wondering-v2 1c). Unlike create()
    # (manual authoring: archived, no provenance), this stores the theorem tokeniko DERIVED himself:
    # ACTIVE (archived=False -> joins reasoning), trusted, carrying its PROOF (MEMProvenance from the
    # chainer). `tokens` is the rendered first-person NL ("I exist"); it is compiled through the real
    # pipeline (talker=tokeniko ⇒ "I" -> its own uid) so the theorem is a genuine zip, not a fabricated
    # one. DEDUP is on the SEMANTIC conclusion (subject uid + predicate sense), not the surface string,
    # so a truth already held is not re-stored under different wording -> wondering converges. Returns
    # the existing theorem (no write) when the conclusion is already known, else the newly-stored one.
    def materialize(self, tokens: str, provenance: MEMProvenance, trusted: float = 0.9,
                    senses: Optional[dict] = None, postable: bool = True,
                    structure: Optional[dict] = None) -> TKTheoremDoc:
        # ZIP-NATIVE ENTRANCE (instrument arc #2): when the caller sends the conclusion's full
        # STRUCTURE, the zip is assembled directly from it — the parser never runs, `tokens` is
        # only the human label, and there is nothing to re-pin (the senses are first-class inputs,
        # not a repair). The parser path below stays as the structure-less fallback. Same seam,
        # two entrances — the write-path invariant is untouched.
        fields: dict
        if structure and structure.get("subject") and structure.get("predicate"):
            native = assemble_conclusion_zip(
                structure["subject"], structure["predicate"], structure.get("object"),
                bool(structure.get("negated", False)), subject_kind=structure.get("subject_kind"),
            )
            if native is None:
                raise UngroundableConclusionError(
                    f"native assembly refused (ungroundable role): {structure}")
            fields = {"original": tokens, "zip": native, "raw": None}
        else:
            fields = self.compile_fields(tokens)
            if senses:
                _pin_conclusion_senses(fields["zip"], senses)  # the derivation's senses ARE the truth
        assert_no_contradiction(fields["zip"])  # logic-is-sacred: never store a contradictory form
        key = conclusion_key(fields["zip"])
        for existing in TKTheoremDoc.find({"archived": False}).to_list():
            if existing.zip is not None and conclusion_key(existing.zip) == key:
                return existing  # the conclusion is already held (semantic dedup) — converge, no write
        theorem = TKTheoremDoc(
            original=fields["original"],
            zip=fields["zip"],
            raw=fields["raw"],
            sourceId=str(self._tokeniko.id),   # tier-2: tokeniko derived it — speaker-irrelevant
            targetId=str(self._tokeniko.id),
            channel=MEMChannels.INTERNAL,
            archived=False,                    # ACTIVE -> joins reasoning (model default is archived=True)
            trusted=trusted,
            provenance=provenance,             # the proof: premises + chain + derived_by
            postable=postable,                 # provenance gate (blog P1): "DM never public", brain-computed
        )
        theorem.insert()
        return theorem

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
        # transitive cascade (step 3): a retracted theorem takes its own descendants with it
        # (with theorem fuel, a child theorem's premises cite THIS theorem's id).
        if updates.get("archived") is True:
            revoke_dependents([str(theorem.id)], dry_run=False)
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
        if archived:
            revoke_dependents([str(theorem.id)], dry_run=False)  # transitive cascade (step 3)
        return theorem

    # delete a theorem (cascade first: descendants fall before their ground does)
    def delete(self, object_id: str) -> None:
        theorem = self._resolve(object_id)
        revoke_dependents([str(theorem.id)], dry_run=False)
        theorem.delete()
