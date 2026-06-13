# ------------------------------------------------------------------------------------------------
# SPACETIME
# spacetime is resolved in passes: (1) compiler_spacetimeResolveTime assigns each entity
# reference a raw position on the time axis (position[0], abstract days from the deictic now);
# (2) compiler_spacetimeResolveSpace assigns the space axes (position[1:4], relative place
# coords); (3) compiler_spacetimeNormalize squashes all raw coords to [-1,1] and emits the map;
# (4) compiler_spacetimeResolveVelocity derives velocity[1:4] as the slope of the normalized
# trajectory (Δposition/Δtime per entity across clauses).
# ------------------------------------------------------------------------------------------------
from lib.core.tk import TKEntity
from lib.core.tkllc import LLCItemPayload, TKLLCContent, TKLLCItem, TKLLEntityReference, TKLLSpacetimeMap
from lib.llc.constants import _SEQUENCE_ANCHORS, _SPATIAL_RELATION_ANCHORS, _TEMPORAL_ANCHORS, _TEMPORAL_PREP_DURATION, _TEMPORAL_PREP_PAST, _TENSE_ANCHORS, _TIME_UNITS

from .c_state import _entities

# map of resolved (flat) llc entity id -> lowercased token
def compiler_spacetimeTokens() -> dict[int, str]:
    return {m.entity.id: (m.entity.token or "").lower() for m in _entities}

# map of resolved (flat) llc entity id -> geo coordinates ([lon, lat(, alt)]) for known places
def compiler_spacetimeGeo() -> dict[int, list[float]]:
    return {m.entity.id: m.entity.geo for m in _entities if m.entity.geo}

# entity references that participate in a clause content (subject/predicate/direct/indirects)
def compiler_spacetimeContentRefs(content: TKLLCContent) -> list[TKLLEntityReference]:
    refs: list[TKLLEntityReference] = []
    if content.subject: refs.append(content.subject)
    if content.predicate: refs.append(content.predicate)
    if content.direct: refs.append(content.direct)
    refs.extend(content.indirects)
    return refs

# a temporal-quantity phrase ("in 11 hours", "for 3 days") detected by its object being a
# time-unit noun. returns ("offset", days) for in/after/within (future) and before/ago (past),
# ("duration", days) for for/during, or None. the (shared) preposition only sets direction.
def compiler_spacetimeTemporalRef(ref: TKLLEntityReference, tokens: dict[int, str]) -> tuple[str, float] | None:
    unit = _TIME_UNITS.get(tokens.get(ref.id, ""))
    if unit is None:
        return None

    # count from a nummod number property (default 1)
    count = 1.0
    for prop in ref.properties:
        if prop.dep == "nummod":
            try:
                count = float(tokens.get(prop.id, "1"))
            except ValueError:
                pass
    days = count * unit

    prep = (ref.marker.word or "").lower() if ref.marker else ""
    if prep in _TEMPORAL_PREP_PAST:
        return ("offset", -days)
    if prep in _TEMPORAL_PREP_DURATION:
        return ("duration", days)
    # in / after / within (and bare) -> future offset
    return ("offset", days)

# duration (abstract days) of a clause from a "for/during X units" phrase, else 0
def compiler_spacetimeClauseDuration(content: TKLLCContent, tokens: dict[int, str]) -> float:
    for indirect in content.indirects:
        temporal = compiler_spacetimeTemporalRef(indirect, tokens)
        if temporal and temporal[0] == "duration":
            return temporal[1]
    return 0.0

# time (abstract days) of a clause: a temporal-quantity phrase ("in 11 hours") or an explicit
# anchor (yesterday/today) sets it absolutely; else a sequence advmod (then/later) advances the
# cursor; else the tense baseline; else the clause inherits the running cursor.
def compiler_spacetimeClauseTime(content: TKLLCContent, cursor: dict, tokens: dict[int, str]) -> float:
    # temporal-quantity phrase: offset from now (e.g. "in 11 hours" -> +11/24 days)
    for indirect in content.indirects:
        temporal = compiler_spacetimeTemporalRef(indirect, tokens)
        if temporal and temporal[0] == "offset":
            cursor["t"] = temporal[1]
            cursor["anchored"] = True
            return cursor["t"]

    # explicit temporal anchor (obl:tmod date words)
    for indirect in content.indirects:
        word = tokens.get(indirect.id, "")
        if word in _TEMPORAL_ANCHORS:
            cursor["t"] = _TEMPORAL_ANCHORS[word]
            cursor["anchored"] = True
            return cursor["t"]

    # sequence advmod on the predicate
    if content.predicate:
        for prop in content.predicate.properties:
            if prop.dep == "advmod":
                word = tokens.get(prop.id, "")
                if word in _SEQUENCE_ANCHORS:
                    cursor["t"] += _SEQUENCE_ANCHORS[word]
                    return cursor["t"]

    # tense baseline (coarse past/present/future): weakest fallback, only while no explicit
    # anchor has been seen, so it does not override a discourse time already established
    if not cursor["anchored"] and content.predicate and content.predicate.aux and content.predicate.aux.tense:
        offset = _TENSE_ANCHORS.get(content.predicate.aux.tense)
        if offset is not None:
            cursor["t"] = offset
            return cursor["t"]

    return cursor["t"]

# resolve the TIME axis (position[0]) of every entity reference, walking clauses in document order
def compiler_spacetimeResolveTime(statements: list[TKLLCItem]) -> None:
    tokens = compiler_spacetimeTokens()
    cursor = {"t": 0.0, "anchored": False}  # deictic origin: utterance now

    def walk(content: LLCItemPayload) -> None:
        if isinstance(content, list):
            for item in content:
                walk(item.content)
            return
        t = compiler_spacetimeClauseTime(content, cursor, tokens)
        duration = compiler_spacetimeClauseDuration(content, tokens)
        for ref in compiler_spacetimeContentRefs(content):
            ref.spacetime.position[0] = t
            ref.spacetime.size[0] = duration

    for item in statements:
        walk(item.content)

# place identity key: the entity token plus its distinguishing modifiers, so place instances
# that share a head but differ in modifiers ("my room" vs "the living room") get distinct keys,
# while a repeated mention ("the room" ... "the room") stays the same place. Needed because the
# flat entities dedup by head token, collapsing distinct place instances onto one id.
def compiler_spacetimePlaceKey(ref: TKLLEntityReference, tokens: dict[int, str]) -> str:
    base = tokens.get(ref.id, "")
    mods = sorted(tokens.get(p.id, "") for p in ref.properties)
    return "|".join([base, *mods])

# coordinate of a place reference: a known place uses its real geo ([lon, lat, alt]); an abstract
# place a fresh relative coordinate. coordinates are cached per place key (reused on recurrence).
def compiler_spacetimePlaceCoord(ref: TKLLEntityReference, places: dict, tokens: dict[int, str], geo: dict[int, list[float]]) -> list[float]:
    key = compiler_spacetimePlaceKey(ref, tokens)
    if key not in places:
        coords = geo.get(ref.id)
        if coords and len(coords) >= 2:
            places[key] = [coords[0], coords[1], coords[2] if len(coords) > 2 else 0.0]
        else:
            places[key] = [float(len(places) + 1), 0.0, 0.0]
    return places[key]

# the locative references of a clause as (ref, relation) pairs (origin/dest/contain/near/far),
# gated on marker.dep == "case" (so infinitival "to leave" is not a place) and excluding temporal
# phrases ("in 11 hours"). the copular predicate of "I was in my room" is locative too.
def compiler_spacetimeClauseLocatives(content: TKLLCContent, tokens: dict[int, str]) -> list[tuple[TKLLEntityReference, str]]:
    candidates: list[TKLLEntityReference] = []
    if content.predicate: candidates.append(content.predicate)
    candidates.extend(content.indirects)

    locatives: list[tuple[TKLLEntityReference, str]] = []
    for ref in candidates:
        if compiler_spacetimeTemporalRef(ref, tokens):
            continue
        marker = ref.marker
        if marker and marker.dep == "case":
            relation = _SPATIAL_RELATION_ANCHORS.get((marker.word or "").lower())
            if relation:
                locatives.append((ref, relation))
    return locatives

# resolve the SPACE axis (position[1:4]) of every entity reference, in document order. each
# locative gets its OWN coordinate (so "from Osaka to Rome" places both, not one); non-locative
# refs (subject/predicate) get the clause's agent location = destination > static > origin >
# cursor, which also advances the cursor. known places use real geo, abstract ones relative coords
# (mixing the two in a scene is approximate, but normalization keeps the layout scene-relative).
def compiler_spacetimeResolveSpace(statements: list[TKLLCItem]) -> None:
    tokens = compiler_spacetimeTokens()
    geo = compiler_spacetimeGeo()
    places: dict[str, list[float]] = {}
    cursor = {"xyz": [0.0, 0.0, 0.0]}  # deictic origin: 'here'

    def walk(content: LLCItemPayload) -> None:
        if isinstance(content, list):
            for item in content:
                walk(item.content)
            return

        # each locative -> its own coordinate
        locatives = compiler_spacetimeClauseLocatives(content, tokens)
        coords = {id(ref): compiler_spacetimePlaceCoord(ref, places, tokens, geo) for ref, _ in locatives}
        byRelation = {relation: coords[id(ref)] for ref, relation in locatives}

        # agent location for non-locative refs: destination > static > origin > current cursor
        static = byRelation.get("contain") or byRelation.get("near") or byRelation.get("far")
        agent = byRelation.get("dest") or static or byRelation.get("origin") or cursor["xyz"]
        cursor["xyz"] = agent

        for ref in compiler_spacetimeContentRefs(content):
            xyz = coords.get(id(ref), agent)
            ref.spacetime.position[1] = xyz[0]
            ref.spacetime.position[2] = xyz[1]
            ref.spacetime.position[3] = xyz[2]

    for item in statements:
        walk(item.content)

def compiler_spacetimeCollectReferences(statements: list[TKLLCItem]) -> list[TKLLEntityReference]:
    ents: list[TKEntity] = []

    for stat in statements:
        if isinstance(stat.content, TKLLCContent):
            if stat.content.subject: ents.append(stat.content.subject)
            if stat.content.direct: ents.append(stat.content.direct)
            if stat.content.predicate: ents.append(stat.content.predicate)
            if stat.content.indirects: ents.extend(stat.content.indirects)
        else:
            ents.extend(compiler_spacetimeCollectReferences(stat.content))

    return ents

# build spacetime map from entities and normalize the spacetime of the entities in the map (-1, 1)
def compiler_spacetimeNormalize(statements: list[TKLLCItem]) -> TKLLSpacetimeMap:

    # collect all entities
    references = compiler_spacetimeCollectReferences(statements)

    spacetimeMap: TKLLSpacetimeMap = TKLLSpacetimeMap()

    # get bounds
    minT = min(e.spacetime.position[0] - e.spacetime.size[0] / 2 for e in references) if len(references) > 0 else 0
    maxT = max(e.spacetime.position[0] + e.spacetime.size[0] / 2 for e in references) if len(references) > 0 else 0
    minX = min(e.spacetime.position[1] - e.spacetime.size[1] / 2 for e in references) if len(references) > 0 else 0
    maxX = max(e.spacetime.position[1] + e.spacetime.size[1] / 2 for e in references) if len(references) > 0 else 0
    minY = min(e.spacetime.position[2] - e.spacetime.size[2] / 2 for e in references) if len(references) > 0 else 0
    maxY = max(e.spacetime.position[2] + e.spacetime.size[2] / 2 for e in references) if len(references) > 0 else 0
    minZ = min(e.spacetime.position[3] - e.spacetime.size[3] / 2 for e in references) if len(references) > 0 else 0
    maxZ = max(e.spacetime.position[3] + e.spacetime.size[3] / 2 for e in references) if len(references) > 0 else 0

    # same scale for x, y, z
    minSpace = min(minX, minY, minZ)
    maxSpace = max(maxX, maxY, maxZ)

    # a space axis is DEGENERATE when its own raw coords never vary (e.g. a scene that only moves
    # along x leaves y,z flat). Such an axis carries no position information, but normalizing its
    # constant raw value against the shared [minSpace,maxSpace] frame would map it to -1 (a spurious
    # "leftmost" reading, the @x,-1,-1 display artifact). Flag it so it normalizes to 0 (centered /
    # absent) instead, while populated axes keep the shared isotropic frame untouched.
    xDegenerate = maxX - minX == 0
    yDegenerate = maxY - minY == 0
    zDegenerate = maxZ - minZ == 0

    # position is an absolute coordinate -> map [min,max] onto [-1,1] (offset + scale). a degenerate
    # axis (no spatial variation) is centered at 0 rather than pinned to the shared-frame edge.
    def normalize(value: float, min: float, max: float, degenerate: bool = False) -> float:
        if degenerate or max - min == 0: return 0
        return (value - min) / (max - min) * 2 - 1

    # size (extent) and velocity (rate) are deltas -> scale only, so 0 stays 0
    def normalizeDelta(value: float, min: float, max: float) -> float:
        if max - min == 0: return 0
        return value / (max - min) * 2

    # the map stores the RAW bounds actually used for normalization (the absolute scene frame),
    # NOT the trivially-normalized [-1,1]. entity coords are normalized within these bounds, so
    # the map is the de-normalization key: it preserves the absolute anchor (a lone "the dog ran"
    # keeps tbounds=[-0.5,-0.5], distinct from "will run" -> [0.5,0.5]) and lets two memories be
    # compared on an absolute frame. space axes share the isotropic [minSpace, maxSpace] scale.
    spacetimeMap.tbounds = [minT, maxT]
    spacetimeMap.xbounds = [minSpace, maxSpace]
    spacetimeMap.ybounds = [minSpace, maxSpace]
    spacetimeMap.zbounds = [minSpace, maxSpace]

    # recalculate the spacetime of the entities in the map
    for e in references:
        e.spacetime.position[0] = normalize(e.spacetime.position[0], minT, maxT)
        e.spacetime.position[1] = normalize(e.spacetime.position[1], minSpace, maxSpace, xDegenerate)
        e.spacetime.position[2] = normalize(e.spacetime.position[2], minSpace, maxSpace, yDegenerate)
        e.spacetime.position[3] = normalize(e.spacetime.position[3], minSpace, maxSpace, zDegenerate)
        e.spacetime.size[0] = normalizeDelta(e.spacetime.size[0], minT, maxT)
        e.spacetime.size[1] = normalizeDelta(e.spacetime.size[1], minSpace, maxSpace)
        e.spacetime.size[2] = normalizeDelta(e.spacetime.size[2], minSpace, maxSpace)
        e.spacetime.size[3] = normalizeDelta(e.spacetime.size[3], minSpace, maxSpace)
        # NB: velocity is resolved AFTER normalization (compiler_spacetimeResolveVelocity),
        # as the slope of the already-normalized trajectory, so it is not rescaled here.

    return spacetimeMap

# a reference is a locative ground (the place a clause happens at) when it carries a locative
# case marker. such references are the static frame, not movers, so they are excluded from the
# velocity derivative (otherwise distinct place instances sharing one entity id - "my room" vs
# "the living room" - would be read as one room that moved).
def compiler_spacetimeIsGround(ref: TKLLEntityReference) -> bool:
    marker = ref.marker
    return bool(marker and marker.dep == "case" and (marker.word or "").lower() in _SPATIAL_RELATION_ANCHORS)

# resolve VELOCITY (velocity[1:4]) from two sources, both AFTER normalization (positions in
# comparable [-1,1] units): (1) intra-clause motion - a clause with an explicit origin (from) and
# destination (to) gives its subject a displacement velocity dest - origin; (2) cross-clause
# trajectory - for entities recurring over time, (next position - this) / (next time - this).
# velocity[0] (time component) is left 0 (degenerate).
def compiler_spacetimeResolveVelocity(statements: list[TKLLCItem]) -> None:
    tokens = compiler_spacetimeTokens()
    motionRefs: set[int] = set()
    maxAbs = 0.0

    # (1) intra-clause motion: subject velocity = destination - origin
    def walkMotion(content: LLCItemPayload) -> None:
        nonlocal maxAbs
        if isinstance(content, list):
            for item in content:
                walkMotion(item.content)
            return
        if not content.subject:
            return
        byRelation: dict[str, TKLLEntityReference] = {}
        for ref, relation in compiler_spacetimeClauseLocatives(content, tokens):
            byRelation.setdefault(relation, ref)
        origin, dest = byRelation.get("origin"), byRelation.get("dest")
        if origin and dest:
            for axis in (1, 2, 3):
                v = dest.spacetime.position[axis] - origin.spacetime.position[axis]
                content.subject.spacetime.velocity[axis] = v
                maxAbs = max(maxAbs, abs(v))
            motionRefs.add(id(content.subject))

    for item in statements:
        walkMotion(item.content)

    # (2) cross-clause trajectory (grounds excluded; motion refs keep their intra-clause velocity)
    references = [r for r in compiler_spacetimeCollectReferences(statements) if not compiler_spacetimeIsGround(r)]
    byId: dict[int, list[TKLLEntityReference]] = {}
    for ref in references:
        byId.setdefault(ref.id, []).append(ref)
    for group in byId.values():
        group.sort(key=lambda r: r.spacetime.position[0])
        for a, b in zip(group, group[1:]):
            if id(a) in motionRefs:
                continue
            dt = b.spacetime.position[0] - a.spacetime.position[0]
            if dt == 0:
                continue
            for axis in (1, 2, 3):
                v = (b.spacetime.position[axis] - a.spacetime.position[axis]) / dt
                a.spacetime.velocity[axis] = v
                maxAbs = max(maxAbs, abs(v))

    # (3) scene-relative scaling into [-1,1] (preserve zero and sign), like the position map
    if maxAbs > 1.0:
        for ref in compiler_spacetimeCollectReferences(statements):
            for axis in (1, 2, 3):
                ref.spacetime.velocity[axis] /= maxAbs
