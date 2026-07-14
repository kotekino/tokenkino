# ------------------------------------------------------------------------------------------------
# curate_add_senses.py — add MISSING WordNet senses to the dictionary (operator-gated curation).
#
# The original ingestion (dictionary.py) kept only the first `max_per_pos=3` senses per POS per
# word — a sensible cap that cut some load-bearing senses (the 2026-07-14 "bit incident":
# bit.n.06, the information unit, sits 6th in WordNet's noun list for "bit", so «a coin stores
# bits of information» could never resolve it). This script adds a curated sense with a vector
# computed by the SAME algorithm as the ingestion (synonyms/antonyms/derivations/wup/gloss-overlap
# against the 2925 base anchors) — the added row is indistinguishable from an ingested one.
#
# Usage (from the repo root):
#   python scripts/curate_add_senses.py           # DRY RUN: compute + report, write nothing
#   python scripts/curate_add_senses.py --apply   # insert the missing rows
#
# The batch below is the curation list — extend it as triage finds more casualties of the cap.
# ------------------------------------------------------------------------------------------------
import os
import re
import sys

import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient
import nltk
from nltk.corpus import wordnet as wn
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "tokeniko", ".env"))

# ---- the curation batch: (word, canonical synset key) -------------------------------------------
BATCH = [
    ("bit", "bit.n.06"),   # the information unit (from binary + digit) — the coin incident
]

nltk.download("wordnet", quiet=True)
nltk.download("omw-1.4", quiet=True)
nltk.download("stopwords", quiet=True)
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words("english"))


# ---- the ingestion algorithm, replicated FAITHFULLY from dictionary.py --------------------------
def calculate_synset_glossary(syn):
    phrase = syn.definition()
    for ex in syn.examples():
        phrase += " " + ex
    clean_words = re.findall(r"\b[a-z]+\b", phrase.lower())
    return {p for p in clean_words if p not in stop_words and len(p) > 2}


def calculate_base_glossary(word):
    tokens = set()
    for syn in wn.synsets(word):
        phrase = syn.definition()
        for ex in syn.examples():
            phrase += " " + ex
        clean_words = re.findall(r"\b[a-z]+\b", phrase.lower())
        tokens.update(p for p in clean_words if p not in stop_words and len(p) > 2)
    return tokens


def get_primary_meanings(word, max_per_pos=3):
    all_synsets = wn.synsets(word)
    if not all_synsets:
        for pos_tag in ["v", "n", "a", "r"]:
            lemma = lemmatizer.lemmatize(word, pos=pos_tag)
            if lemma != word:
                all_synsets = wn.synsets(lemma)
                if all_synsets:
                    break
    filtered, pos_counts = [], {"n": 0, "v": 0, "a": 0, "s": 0, "r": 0}
    for s in all_synsets:
        pos = s.pos()
        if pos_counts.get(pos, 0) < max_per_pos:
            filtered.append(s)
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
    return filtered


def get_semantic_value(target_word, target_synset, base_word, target_gloss, base_gloss):
    if target_word == base_word:
        return 1.0
    s2 = wn.synsets(base_word)
    if not s2:
        return 0.0
    set2 = set(s2)
    if target_synset in set2:
        return 1.0
    for lemma in target_synset.lemmas():
        for ant in lemma.antonyms():
            if ant.synset() in set2:
                return -1.0
    for lemma in target_synset.lemmas():
        for drf in lemma.derivationally_related_forms():
            if drf.synset() in set2:
                return 0.9
    max_sim = 0.0
    for ss2 in get_primary_meanings(base_word):
        if target_synset.pos() == ss2.pos():
            sim = target_synset.wup_similarity(ss2)
            if sim and sim > max_sim:
                max_sim = sim
    if max_sim > 0.65:
        return round(max_sim, 3)
    if target_gloss and base_gloss:
        overlap = len(target_gloss.intersection(base_gloss))
        if overlap >= 2:
            jaccard = overlap / len(target_gloss.union(base_gloss))
            score = min(round(jaccard * 5, 3), 0.5)
            if score > 0.1:
                return score
    return 0.0


def main():
    apply = "--apply" in sys.argv
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client[os.getenv("MONGO_DB_NAME")]
    coll = db["dictionary"]
    base_docs = list(db["base"].find().sort("index", 1))
    base_words = [d["word"] for d in base_docs]
    print(f"base anchors: {len(base_words)} | mode: {'APPLY' if apply else 'DRY RUN'}\n")

    for word, sense_key in BATCH:
        existing = coll.find_one({"sense": sense_key})
        if existing is not None:
            print(f"SKIP {sense_key}: already in the dictionary (word={existing['word']})")
            continue
        syn = wn.synset(sense_key)
        target_gloss = calculate_synset_glossary(syn)
        vector = [get_semantic_value(word, syn, bw, target_gloss, calculate_base_glossary(bw))
                  for bw in base_words]
        arr = np.asarray(vector)
        nz = int(np.count_nonzero(arr))
        top = sorted(zip(base_words, vector), key=lambda t: -abs(t[1]))[:8]
        print(f"{sense_key} [{word}] «{syn.definition()[:80]}»")
        print(f"  vector: {len(vector)} dims, {nz} nonzero | top anchors: "
              + ", ".join(f"{w}={v}" for w, v in top))
        if apply:
            coll.insert_one({"word": word, "pos": syn.pos(), "sense": sense_key,
                             "definition": syn.definition(), "vector": vector})
            print(f"  INSERTED into dictionary")
        else:
            print(f"  (dry run — not written)")

    client.close()


if __name__ == "__main__":
    main()
