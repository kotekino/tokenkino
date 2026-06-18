# ------------------------------------------------------------------------------------------------
# EVALUATOR — taxonomic relations (the is_a graph)
# pure graph logic over a WordNet-derived is_a (hypernym) graph: subsumption ("a cat is a mammal"
# is TRUE because cat —is_a*→ mammal) and CONSERVATIVE ontological disjointness ("a cat is a plant"
# is FALSE — cat is an organism, plant is either the plant kingdom or a factory artifact, and a cat
# is neither).
#
# DB-AGNOSTIC: every function takes a `parents` callable (sense -> list[direct is_a parents]); the
# caller injects the reader. The graph stores DIRECT edges only, so ancestry is a BFS at query time.
#
# WHY CONSERVATIVE + TIERED (the disjointness rule, pinned empirically — see STEP-0/recon):
#   WordNet's is_a is incomplete and noisy (WSD also mislabels senses). A blanket "different branch
#   under a common ancestor ⇒ disjoint" over-fires: e.g. organism.n.01 has ~48 children, most of which
#   are NOT real kingdoms (parent, native, host, …) and person.n.01 sits beside animal.n.01 — so
#   "different child of organism" would wrongly refute "a human is an animal". We therefore fire a
#   strong-FALSE ONLY when the two senses sit under DIFFERENT members of a small, hand-vetted set of
#   mutually-exclusive anchors — and we compare at the FINEST TIER where both senses are placed:
#     tier 1 — biological kingdoms (animal/plant/fungus/bacteria/microorganism) under organism;
#     tier 2 — kinds of physical thing (organism/artifact/natural_object/substance) under object;
#     tier 3 — physical vs abstract (physical_entity/abstraction) under entity.
#   So cat vs dog (both animal) and cat vs person (both organism) correctly do NOT refute, while cat
#   vs plant (animal⊥plant), cat vs car (organism⊥artifact) and cat vs idea (physical⊥abstract) do —
#   and "a cat is a plant" refutes whether "plant" reads as the botanical kingdom OR the factory
#   artifact. A sense placed in no tier (e.g. cat.n.03 "woman") yields NO refutation — it falls through
#   to definition-grounding / INSUFFICIENT. Keeps the false-FALSE rate near zero at the cost of missing
#   some true disjointness (acceptable: refutation is the strong claim, so it must be the cautious one).
# ------------------------------------------------------------------------------------------------
from typing import Callable, Optional

# mutually-exclusive ontological category TIERS, ordered MOST-SPECIFIC first (see header). two senses
# are disjoint when, at the finest tier where BOTH are placed, they fall under DIFFERENT anchors.
_DISJOINT_TIERS: tuple[frozenset[str], ...] = (
    # tier 1 — biological kingdoms (under organism). person.n.01 is intentionally NOT here (a person
    # IS an animal in reality; it sits beside animal under organism in WordNet).
    frozenset({"animal.n.01", "plant.n.02", "fungus.n.01", "fungus.n.02",
               "bacteria.n.01", "microorganism.n.01"}),
    # tier 2 — kinds of physical thing (under object/whole / matter)
    frozenset({"organism.n.01", "artifact.n.01", "natural_object.n.01", "substance.n.01"}),
    # tier 3 — physical vs abstract (under entity)
    frozenset({"physical_entity.n.01", "abstraction.n.06"}),
)

Parents = Callable[[str], list[str]]


# BFS over is_a from `sense` to every reachable ancestor. cycle-safe (visited set) and depth-capped.
# returns {ancestor -> path}, the path being the list of senses from `sense` (inclusive) up to that
# ancestor (inclusive). `sense` itself is NOT included as a key (it is not its own ancestor).
def relations_isa_ancestors(sense: str, parents: Parents, max_depth: int = 12) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    # frontier holds (node, path-from-sense-to-node)
    frontier: list[tuple[str, list[str]]] = [(sense, [sense])]
    while frontier:
        node, path = frontier.pop(0)
        if len(path) - 1 >= max_depth:
            continue
        for p in parents(node):
            if p == sense or p in found:
                continue
            new_path = path + [p]
            found[p] = new_path
            frontier.append((p, new_path))
    return found


# the is_a path from `child` up to `parent` (inclusive on both ends) when parent is an ancestor of
# child, else None. parent == child returns the trivial single-node path (a sense subsumes itself).
def relations_subsumes(parent: str, child: str, parents: Parents) -> Optional[list[str]]:
    if parent == child:
        return [child]
    ancestors = relations_isa_ancestors(child, parents)
    path = ancestors.get(parent)
    return path if path is not None else None


# the anchor (member of `tier`) that `sense` is placed under, with the is_a path to it, or
# (None, None). `sense` may itself be the anchor. `ancestors` is its precomputed is_a ancestor map
# (insertion order = BFS = shallowest first, so the shallowest anchor wins).
def _anchor_in_tier(sense: str, tier: frozenset[str],
                    ancestors: dict[str, list[str]]) -> tuple[Optional[str], Optional[list[str]]]:
    if sense in tier:
        return sense, [sense]
    for anc, path in ancestors.items():
        if anc in tier:
            return anc, path
    return None, None


# CONSERVATIVE tiered ontological disjointness. returns a witness chain when `a` and `b` are
# high-confidence disjoint, else None.
#
# rule: a ⊥ b iff
#   (1) neither subsumes the other (an is_a relation is the opposite of disjointness), AND
#   (2) at the FINEST tier where BOTH senses are placed under an anchor, those anchors DIFFER.
# walking most-specific tier first means agreement at a fine tier (cat & dog both `animal`) blocks a
# spurious refutation from a coarser one, and a missing fine placement falls through to a coarser tier
# (cat `organism` vs car `artifact`). the witness is the two ancestry paths plus a disjointness note.
def relations_disjoint(a: str, b: str, parents: Parents) -> Optional[list[str]]:
    # (1) a subsumption either way means they are NOT disjoint
    if relations_subsumes(a, b, parents) is not None or relations_subsumes(b, a, parents) is not None:
        return None

    anc_a = relations_isa_ancestors(a, parents)
    anc_b = relations_isa_ancestors(b, parents)

    # (2) compare at the finest tier where both are placed
    for tier in _DISJOINT_TIERS:
        ka, path_a = _anchor_in_tier(a, tier, anc_a)
        kb, path_b = _anchor_in_tier(b, tier, anc_b)
        if ka is None or kb is None:
            continue              # not both placed at this tier -> try a coarser one
        if ka == kb:
            return None           # agree at the finest shared tier -> NOT disjoint
        chain_a = " —is_a→ ".join(path_a)
        chain_b = " —is_a→ ".join(path_b)
        note = f"{ka} ⊥ {kb} (mutually-exclusive ontological categories)"
        return [chain_a, chain_b, note]

    return None
