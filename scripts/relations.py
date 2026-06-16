# ------------------------------------------------------------------------------------------------
# relations.py — harvest WordNet's STRUCTURED relations into atomic, sense-scoped triples.
# Phase 1a of the knowledge bootstrap (see tokeniko/doc/plan.md): the inference engine's chaining
# backbone, built WITHOUT the parser (pure WordNet, no NL compilation). Each triple is
# {subject, relation, object, pos} with subject/object being WordNet sense names (e.g. "cat.n.01").
# Direct edges only — transitive closure (is_a chains, branch-disjointness) is computed at query time.
#
# Relations (POS-aware): is_a (hypernyms + instance hypernyms), part_of (part/member/substance
# holonyms — i.e. the wholes this sense belongs to), antonym (lemma antonyms, sense-scoped), entails
# (verbs), attribute (adjective <-> noun), similar_to (adjective satellites).
#
# Writes to the app knowledge base (MONGO_URI / MONGO_DB_NAME from tokeniko/.env), collection
# "relations". Run a dry sample first:  python scripts/relations.py sample
# Full harvest:                          python scripts/relations.py
# ------------------------------------------------------------------------------------------------
import os
import sys

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tokeniko", ".env"))

from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
DB_NAME = os.getenv("MONGO_DB_NAME")
COLLECTION = "relations"
BATCH_SIZE = 2000


# all relation triples for one synset, as (subject, relation, object, pos), deduped, order-preserving
def triples_for(synset) -> list[tuple]:
    subj, pos = synset.name(), synset.pos()
    out: list[tuple] = []

    def add(relation, target_synset):
        out.append((subj, relation, target_synset.name(), pos))

    # is-a (taxonomy backbone) — ordinary + instance hypernyms ("Rome is_a city")
    for h in synset.hypernyms():
        add("is_a", h)
    for h in synset.instance_hypernyms():
        add("is_a", h)
    # part_of — the wholes this sense belongs to (part / member / substance holonyms)
    for h in synset.part_holonyms() + synset.member_holonyms() + synset.substance_holonyms():
        add("part_of", h)
    # entails (verbs): walk -> step
    for e in synset.entailments():
        add("entails", e)
    # attribute (adjective <-> noun): big -> size, good -> quality
    for a in synset.attributes():
        add("attribute", a)
    # similar_to (adjective satellites)
    for x in synset.similar_tos():
        add("similar_to", x)
    # antonym — lemma-level, kept sense-scoped (same source as the base matrix's -1)
    for lemma in synset.lemmas():
        for ant in lemma.antonyms():
            add("antonym", ant.synset())

    return list(dict.fromkeys(out))  # dedup (e.g. an antonym reachable via two lemmas)


def _docs(triples):
    return [{"subject": s, "relation": r, "object": o, "pos": p} for (s, r, o, p) in triples]


# dry run: harvest a handful of well-known senses and print, no DB writes
def sample():
    names = ["cat.n.01", "carnivore.n.01", "lettuce.n.02", "good.a.01", "big.a.01", "walk.v.01"]
    total = 0
    for name in names:
        ts = triples_for(wn.synset(name))
        total += len(ts)
        print(f"\n### {name}  ({len(ts)} triples)")
        for s, r, o, p in ts:
            print(f"   {s:18s} --{r}--> {o}")
    print(f"\nsample total: {total} triples (NO DB writes)")


def main():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    coll = db[COLLECTION]

    print(f"Harvesting WordNet relations -> {DB_NAME}.{COLLECTION} @ {MONGO_URI}")
    all_synsets = list(wn.all_synsets())
    total = len(all_synsets)
    print(f"Total synsets: {total}")

    # resume logic: skip subjects already harvested
    already = set(coll.distinct("subject"))
    print(f"Already harvested: {len(already)} subjects")

    buffer = []
    written = 0
    for i, synset in enumerate(all_synsets):
        if synset.name() in already:
            continue
        buffer.extend(_docs(triples_for(synset)))
        if len(buffer) >= BATCH_SIZE:
            if buffer:
                coll.insert_many(buffer)
                written += len(buffer)
            buffer.clear()
        if (i + 1) % 10000 == 0:
            print(f"  {i + 1}/{total} synsets scanned, {written} triples written")

    if buffer:
        coll.insert_many(buffer)
        written += len(buffer)

    print(f"\n✅ Done. {written} new triples written.")
    print("Creating indexes (subject, object, relation)...")
    coll.create_index("subject")
    coll.create_index("object")
    coll.create_index("relation")
    client.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sample":
        sample()
    else:
        main()
