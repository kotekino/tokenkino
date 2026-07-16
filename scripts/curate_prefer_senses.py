# ------------------------------------------------------------------------------------------------
# curate_prefer_senses.py — set the curated DEFAULT sense per (word,pos) (operator-gated curation).
#
# M3 (the third harvest, 2026-07-16): WordNet orders senses by corpus frequency, and for several
# everyday words that order contradicts the word's plain conversational reading — squid.n.01 is
# the FOOD, calculator.n.01 the PERSON — so the WSD frequency prior picks them honestly and
# wrongly whenever context is silent. The `preferred` flag on a dictionary row is the crew's
# ruling on the plain reading. The WSD ladder consults it AFTER Lesk (textual gloss evidence
# still wins — «I ate squid with lemon» can still reach the food sense) and BEFORE the context
# centroid (curated human data outranks sparse-vector co-occurrence guessing: the centroid ranked
# pisces.n.02, the FISH SIGN, above the actual fish at cosine 0.755).
#
# Idempotent: for each (word,pos) the flag is CLEARED on all rows first, then set on exactly the
# curated sense — re-running converges; changing a ruling here and re-applying moves the flag.
#
# Usage (from the repo root):
#   python scripts/curate_prefer_senses.py           # DRY RUN: report current vs curated
#   python scripts/curate_prefer_senses.py --apply   # write the flags
# ------------------------------------------------------------------------------------------------
import os
import sys

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tokeniko", ".env"))

# ---- the curation batch: (word, pos, preferred synset key) — the author's per-word rulings ------
BATCH = [
    ("squid",      "n", "squid.n.02"),       # the animal, not the Italian-cuisine food
    ("calculator", "n", "calculator.n.02"),  # the machine, not the expert person
    ("being",      "n", "organism.n.01"),    # a creature («human being»), not the state of existing
    ("form",       "n", "kind.n.01"),        # «a form of X» = a kind, not the phonological word-form
    ("live",       "v", "populate.v.01"),    # inhabit («I live in Japan»), not lead-a-lifestyle
    ("fish",       "n", "fish.n.01"),        # the animal — pins the pisces.n.02 centroid residual
    ("whale",      "n", "whale.n.02"),       # the cetacean (belt-and-braces; fix A already selects it)
    ("gill",       "n", "gill.n.04"),        # the respiratory organ (curated in via add batch 2)
    ("channel",    "n", "channel.n.05"),     # the communication channel (curated in via add batch 2)
    # batch 2 (the second-harvest strays, 2026-07-16 second session):
    ("bit",        "n", "bit.n.06"),         # the information unit («a coin stores bits» read the
                                             # fragment bit.n.02 context-less; Lesk still reaches
                                             # the fragment when the text supports it — «a bit of
                                             # cake». is_a unit_of_measurement.n.01 already in the
                                             # graph, so the definition grounds TRUE)
]


def main():
    apply = "--apply" in sys.argv
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGO_DB_NAME")]
    coll = db["dictionary"]
    print(f"mode: {'APPLY' if apply else 'DRY RUN'}\n")

    for word, pos, sense_key in BATCH:
        rows = list(coll.find({"word": word, "pos": pos}, {"sense": 1, "preferred": 1}))
        if not rows:
            print(f"MISS {word}/{pos}: no dictionary rows at all — run curate_add_senses first?")
            continue
        target = next((r for r in rows if r["sense"] == sense_key), None)
        if target is None:
            print(f"MISS {word}/{pos}: {sense_key} not in the dictionary "
                  f"(has: {[r['sense'] for r in rows]}) — run curate_add_senses first")
            continue
        current = [r["sense"] for r in rows if r.get("preferred")]
        state = "already set" if current == [sense_key] else f"currently {current or 'unset'}"
        print(f"{word}/{pos} -> {sense_key}  ({state})")
        if apply:
            coll.update_many({"word": word, "pos": pos}, {"$unset": {"preferred": ""}})
            coll.update_one({"_id": target["_id"]}, {"$set": {"preferred": True}})

    if apply:
        flagged = list(coll.find({"preferred": True}, {"word": 1, "pos": 1, "sense": 1}))
        print(f"\ndone — {len(flagged)} preferred rows live:")
        for r in flagged:
            print(f"  {r['word']}/{r['pos']} = {r['sense']}")
    else:
        print("\n(dry run — nothing written; re-run with --apply)")


if __name__ == "__main__":
    main()
