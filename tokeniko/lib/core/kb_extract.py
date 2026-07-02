# --------------------------------------------------------------
# lib/core/kb_extract.py — the definition→is_a EXTRACTOR + gate (definitions-as-rules, step 3).
#
# PURE + parser-free: mine each definition's main copular clause ("an X is a ⟨genus⟩") into a candidate
# is_a edge (subject_sense -> genus_sense), then GATE it against tokeniko's OWN bedrock is_a graph so
# only clean, graph-consistent edges reach the low-trust tier. The single source of truth for the gate
# — the read-only probe (scripts/probe_extractor.py, the ruler) and the writer (scripts/extract_
# definitions.py) both call extract_isa_edges(), so they can never drift.
#
# Governing principle: asymmetric risk -> reject-on-doubt (a false is_a edge poisons ALL downstream
# reasoning). The gate (validated in the step-3 dry-run, see doc/ref/landed.md):
#   REDUNDANT     — the bedrock graph already derives subject is_a genus -> drop (adds nothing).
#   PLACEHOLDER   — a metalinguistic genus (name/term/word/designation) is a gloss artifact, not a
#                   hypernym ("a beer is a general NAME for…") -> drop structurally.
#   CYCLE         — subject is already an is_a ancestor of the genus -> subject->genus closes a loop.
#   DISJOINT(1/2) — the senses are disjoint at a RELIABLE ontological tier (1 biological kingdoms /
#                   2 organism-artifact-substance). tier 3 (physical⊥abstract) is DROPPED for admission
#                   — it false-rejects true cross-abstraction edges (agent→cause); a coarse REFUTATION
#                   tool must not be repurposed as an ADMISSION gate (see doc reference geometry-not-isa).
# Everything else is ACCEPTED. The caller (writer) attaches trust/method/provenance and persists.
# --------------------------------------------------------------
from collections import Counter

from lib.core.evaluation_harness import _zip_leaves
from lib.llc.evaluator.e_relations import relations_subsumes, relations_disjoint

# reliable disjointness tiers for ADMISSION. tier 1 (biological kingdoms) + tier 2 (organism/artifact/
# substance) are trustworthy; tier 3 (physical⊥abstract) is NOT — WordNet arbitrarily files polysemous
# nouns on either side. We reject a candidate ONLY when the disjointness fires at tier 1 or 2.
_T1 = {"animal.n.01", "plant.n.02", "fungus.n.01", "fungus.n.02", "bacteria.n.01", "microorganism.n.01"}
_T2 = {"organism.n.01", "artifact.n.01", "natural_object.n.01", "substance.n.01"}
_T3 = {"physical_entity.n.01", "abstraction.n.06"}

# metalinguistic placeholder heads that are NEVER a real is_a hypernym (gloss artifacts). conservative:
# only the unambiguously-metalinguistic words, so no legitimate abstract genus (process/state/group…)
# is ever dropped.
_PLACEHOLDER_GENERA = {"name", "term", "word", "designation"}


def _is_noun(sense) -> bool:
    return bool(sense) and ".n." in sense


def _genus_lemma(sense: str) -> str:
    return (sense or "").split(".", 1)[0]


def _disjoint_tier(note: str) -> int:
    for tok in note.replace(" ⊥", " ").split():
        if tok in _T1:
            return 1
        if tok in _T2:
            return 2
        if tok in _T3:
            return 3
    return 0


# candidate genus edges (one per definition, main clause): the FIRST leaf whose subject + predicate are
# both noun senses (the taxonomic spine), no self-edge. Reads the STORED (recompiled, sense-faithful)
# zips — no parser. Returns [(subject_sense, genus_sense, doc), ...].
def _candidate_edges(definition_docs):
    out = []
    for d in definition_docs:
        leaves = _zip_leaves(d.zip.items) if d.zip else []
        for lf in leaves:
            s = getattr(lf, "senses", None) or {}
            subj, genus = s.get("subject"), s.get("predicate")
            if _is_noun(subj) and _is_noun(genus) and subj != genus:
                out.append((subj, genus, d))
                break  # main clause only
    return out


# the gate verdict for one candidate edge, given the bedrock is_a reader `parents`. Returns one of:
# "redundant" | "placeholder" | "cycle" | "disjoint" | "accept".
def gate_edge(subject_sense: str, genus_sense: str, parents) -> str:
    if relations_subsumes(genus_sense, subject_sense, parents) is not None:
        return "redundant"                                       # bedrock already derives it
    if _genus_lemma(genus_sense) in _PLACEHOLDER_GENERA:
        return "placeholder"                                     # gloss artifact
    if relations_subsumes(subject_sense, genus_sense, parents) is not None:
        return "cycle"                                           # subject already an ancestor of genus
    witness = relations_disjoint(subject_sense, genus_sense, parents)
    if witness is not None and _disjoint_tier(witness[-1]) in (1, 2):
        return "disjoint"                                        # reliable-tier ontological conflict
    return "accept"


# extract the ACCEPTED low-trust is_a edges from the definitions, gated against the bedrock graph.
# `parents` is the injected BEDROCK is_a reader (sense -> direct hypernyms) — NEVER the union reader,
# so the gate judges candidates against the trusted graph only. Returns (edges, stats):
#   edges = [{subject, object, source_id, source_original}, ...]  (relation is is_a; caller adds trust/method)
#   stats = Counter of {candidate, redundant, placeholder, cycle, disjoint, accept}
def extract_isa_edges(definition_docs, parents) -> tuple[list[dict], Counter]:
    stats: Counter = Counter()
    edges: list[dict] = []
    seen: set = set()
    for subj, genus, doc in _candidate_edges(definition_docs):
        stats["candidate"] += 1
        verdict = gate_edge(subj, genus, parents)
        stats[verdict] += 1
        if verdict != "accept":
            continue
        key = (subj, genus)
        if key in seen:
            continue                                             # dedup identical edges across defs
        seen.add(key)
        edges.append({
            "subject": subj,
            "object": genus,
            "source_id": str(doc.id),
            "source_original": doc.original,
        })
    return edges, stats
