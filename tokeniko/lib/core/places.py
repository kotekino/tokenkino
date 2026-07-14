# ------------------------------------------------------------------------------------------------
# lib/core/places.py — the PLACES BRIDGE readers (parser-free, shared).
#
# The places table (~4.7M docs, author-curated at first ingestion) is a hand-built spatial ontology:
# every place carries TWO complete containment chains — `path_admin` (political: europe → italy →
# lazio → rome) and `path_geo` (physical: universe → … → earth → eurasia) — plus a `type` column
# (city/country/planet/… — an is_a statement) and sparse `physical_features` cross-links (rome ON the
# italian peninsula). The compiler's place identity uid ("japan@place") is the KEY back into this
# table; these readers make the chains REASONING-LIVE without ever materializing the 4.7M-doc
# firehose into the relations collection (the cascade-noise lesson: read the curated table lazily).
#
# Imports ONLY lib.core.models — usable by the parser (which also wants the type centroid sense)
# AND by the evaluation harness / evaluator injection (which must stay parser-free).
# ------------------------------------------------------------------------------------------------
from typing import Optional

from lib.core.models import TKDictionaryDoc, TKPlaceDoc

_PLACE_UID_SUFFIX = "@place"

# a place's `type` column (closed set, ~21 values) -> the dictionary sense whose 2925 vector becomes
# the place's semantic centroid. sense selection mirrors the WSD frequency prior: noun senses only,
# query-word lemma preferred, smallest sense number; compound/non-noun types (drainage_basin,
# star_system, …) fall back to location.n.01 (honest, never noise). cached per type string.
_TYPE_SENSE_CACHE: dict[str, str] = {}
_TYPE_FALLBACK_SENSE = "location.n.01"


def place_type_sense(place_type: str) -> str:
    if place_type in _TYPE_SENSE_CACHE:
        return _TYPE_SENSE_CACHE[place_type]
    word = (place_type or "").replace("_", " ").strip().lower()
    sense = _TYPE_FALLBACK_SENSE
    if word:
        docs = TKDictionaryDoc.find({"word": word}).to_list()
        nouns = sorted(d.sense for d in docs if d.sense and ".n." in d.sense)
        word_key = word.replace(" ", "_")
        preferred = [s for s in nouns if s.split(".")[0] == word_key]
        if preferred:
            sense = preferred[0]
        elif nouns:
            sense = nouns[0]
    _TYPE_SENSE_CACHE[place_type] = sense
    return sense


def place_uid_name(uid: Optional[str]) -> Optional[str]:
    """'japan@place' -> 'japan'; None when the uid is not a place identity."""
    if uid and uid.endswith(_PLACE_UID_SUFFIX):
        return uid[: -len(_PLACE_UID_SUFFIX)]
    return None


# per-process doc cache (the places table is static). None is cached too (a missing name stays missing).
_DOC_CACHE: dict[str, Optional[TKPlaceDoc]] = {}


def _doc(name: str) -> Optional[TKPlaceDoc]:
    if name in _DOC_CACHE:
        return _DOC_CACHE[name]
    d = TKPlaceDoc.find_one({"name": name}).run()
    _DOC_CACHE[name] = d
    return d


def place_type_of(uid: str) -> Optional[str]:
    """the type-column SENSE of a place identity ('japan@place' -> the 'country' sense), or None."""
    name = place_uid_name(uid)
    if not name:
        return None
    d = _doc(name)
    return place_type_sense(d.type) if d else None


def _contained(inner: TKPlaceDoc, outer_name: str) -> Optional[str]:
    """the chain label when `outer_name` contains `inner` (path/parent/feature), else None."""
    if outer_name in (inner.path_admin or [])[:-1] or outer_name == inner.parent_admin:
        return "path_admin"
    if outer_name in (inner.path_geo or [])[:-1] or outer_name == inner.parent_geo:
        return "path_geo"
    if outer_name in (inner.physical_features or []):
        return "physical_features"
    return None


def place_contains(inner_uid: str, outer_uid: str) -> Optional[tuple[bool, str]]:
    """is the place `inner_uid` inside the place `outer_uid`? (True/False + the reason chain), or
    None when either identity is not a known place. Both chains are COMPLETE (every doc reaches the
    universe root), so for two KNOWN places non-containment in either direction is a confident
    FALSE — unlike the sparse part_of graph, absence here IS evidence."""
    inner_name, outer_name = place_uid_name(inner_uid), place_uid_name(outer_uid)
    if not inner_name or not outer_name:
        return None
    if inner_name == outer_name:
        return True, f"places: {inner_name} = {outer_name} (same place)"
    inner, outer = _doc(inner_name), _doc(outer_name)
    if inner is None or outer is None:
        return None
    chain = _contained(inner, outer_name)
    if chain is not None:
        return True, f"places: {inner_name} ⊂ {outer_name} ({chain})"
    reverse = _contained(outer, inner_name)
    if reverse is not None:
        return False, f"places: antisymmetry — {outer_name} ⊂ {inner_name} ({reverse})"
    return False, f"places: {inner_name} ⊄ {outer_name} (complete chains, no containment)"


def place_parent(uid: str) -> Optional[tuple[str, str]]:
    """the immediate container of a place identity: (parent name, chain label) — admin preferred
    (the human answer to 'where is Rome?' is 'Lazio', not 'Eurasia'), geo fallback. None if unknown."""
    name = place_uid_name(uid)
    if not name:
        return None
    d = _doc(name)
    if d is None:
        return None
    if d.parent_admin:
        return d.parent_admin, "path_admin"
    if d.parent_geo:
        return d.parent_geo, "path_geo"
    return None
