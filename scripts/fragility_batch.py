# ------------------------------------------------------------------------------------------------
# fragility_batch.py — the categorized fragility-probe matrix + injector (the consolidation harness).
# Each probe: (category, speaker, sentence, expected, severity_if_fail). Injected via GET
# /api/v1/input at prepare=0 (NO preparser/typo-guard -> exercises the raw neuro-symbolic core).
# Pair with scripts/trace_fragility.py to analyze the brain's reaction. See doc/test-feedback.md.
#
#   python scripts/fragility_batch.py --list            # print the matrix, inject nothing
#   python scripts/fragility_batch.py --wipe            # wipe disposable (memory/ideas/actions)
#   python scripts/fragility_batch.py --wipe --inject   # clean sheet then inject (brain must be UP)
#   python scripts/fragility_batch.py --inject          # inject only
# ------------------------------------------------------------------------------------------------
import os, sys, time, requests

PKG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko")
sys.path.insert(0, PKG)
from dotenv import load_dotenv
load_dotenv(os.path.join(PKG, ".env"))
from pymongo import MongoClient

API = os.getenv("TOKENIKO_API", "http://localhost:8000") + "/api/v1"

# (category, speaker, sentence, expected, severity_if_fail)
BATCH = [
    # A — well-formed TRUE assertions (baseline grounding: relational + geometric)
    ("A", "ada", "a cat is a mammal",            "true/known (subsumed)",            "S2"),
    ("A", "ada", "a dog is an animal",           "true/known (subsumed)",            "S2"),
    ("A", "ada", "an emotion is a feeling",      "true (emotion is_a feeling)",      "S2"),
    ("A", "ada", "a robin is a bird",            "true (subsumed)",                  "S2"),

    # B — well-formed FALSE assertions (logic-is-sacred under input)
    ("B", "ben", "a cat is a dog",               "NOT true (distinct siblings)",     "S0"),
    ("B", "ben", "advice is an advertisement",   "NOT true (distinct concepts)",     "S0"),
    ("B", "ben", "a stone is an animal",         "false (cross-kingdom refute)",     "S0"),
    ("B", "ben", "a circle is a square",         "NOT true (distinct abstracts)",    "S0"),
    ("B", "ben", "the cat is dead and alive",    "INCONSISTENT (antonym contra)",    "S0"),
    ("B", "ben", "a mammal is a cat",            "NOT universally true (quant dir)", "S1"),

    # C — polar QUESTIONS (mood + answer machinery; self/other = R1)
    ("C", "cleo", "are you human?",              "NO (tokeniko not human)",          "S1"),
    ("C", "cleo", "do you exist?",               "YES (cogito)",                     "S1"),
    ("C", "cleo", "am I alive?",                 "depends on asker-linking (R1)",    "S1"),
    ("C", "cleo", "is a cat a mammal?",          "YES (definitional)",               "S2"),
    ("C", "cleo", "is advice an advertisement?", "NO (distinct)",                    "S0"),
    ("C", "cleo", "are you curious?",            "IDK (no self-knowledge)",          "S2"),

    # D — WH questions (wh-solver)
    ("D", "dan", "what is a war?",               "VALUE hostility (is_a hypernym)",  "S2"),
    ("D", "dan", "what is a cat?",               "VALUE mammal/animal",              "S2"),
    ("D", "dan", "who is happy?",                "UNKNOWN (subject gap, staged)",    "S3"),
    ("D", "dan", "why do I exist?",              "derivation chain or UNKNOWN",      "S2"),
    ("D", "dan", "how do you feel?",             "UNKNOWN (manner, staged)",         "S3"),
    ("D", "dan", "where is Rome?",               "UNKNOWN (location, staged)",       "S3"),
    ("D", "dan", "when is now?",                 "UNKNOWN (time, staged)",           "S3"),

    # E — unknown vocab / gibberish (eval:unknown -> why/guess; OOV guard)
    ("E", "ada", "the flurble is glonky",        "eval:unknown (gibberish)",          "S2"),
    ("E", "ada", "I am curious to know you",     "eval:unknown (known words, no rel)","S2"),
    ("E", "ada", "a wug is a dax",               "eval:unknown (novel taxonomy)",     "S2"),
    ("E", "ada", "zorp blarg quux",              "eval:unknown / ungrammatical",      "S3"),

    # F — typos, NO preparser (core robustness vs the typo-guard question)
    ("F", "ben", "teh cat is a mamal",           "graceful (typo'd 'cat is mammal')","S2"),
    ("F", "ben", "i tink therefore i am",        "graceful ('tink' typo)",           "S2"),
    ("F", "ben", "a doge is an animl",           "graceful (typos)",                 "S2"),

    # G — fragments / incomplete (parser resilience)
    ("G", "cleo", "the cat",                     "no crash; INSUFFICIENT/partial",   "S3"),
    ("G", "cleo", "is a mammal",                 "no crash; no subject",             "S3"),
    ("G", "cleo", "running fast",                "no crash; VP fragment",            "S3"),
    ("G", "cleo", "because knowledge",           "no crash; subordinate fragment",   "S3"),

    # H — long / multi-clause / premise-in-question (clause tree, coordination, R4b)
    ("H", "dan", "if an actress is a female actor then there are two types of humans that are actors which are female actors and male actors", "parses; true-ish", "S2"),
    ("H", "dan", "I am human, do I think?",      "premise should feed Q (R4b)",      "S1"),
    ("H", "dan", "a cat is a mammal and a dog is an animal", "coordination: both true","S2"),
    ("H", "dan", "the cat which is black sleeps because it is tired", "rel + subordinate", "S2"),
    ("H", "dan", "I think therefore I am",       "implication parses",               "S2"),

    # I — KB-implication chains (forward-chaining + theorem derivation, seeded rules)
    ("I", "ada", "a cat eats meat",              "eval:true CHAIN -> materialize",   "S1"),
    ("I", "ada", "a tiger eats meat",            "eval:true CHAIN (tiger->carnivore)","S1"),
    ("I", "ada", "a human is mortal",            "true (all humans mortal)",         "S1"),
    ("I", "ada", "Mari is mortal",              "chain via seeded 'Mari is human'?", "S1"),

    # J — imperatives / bare moods (the parked imperative path)
    ("J", "ben", "tell me about cats",           "imperative (currently unhandled)", "S3"),
    ("J", "ben", "think about knowledge",        "imperative",                       "S3"),
    ("J", "ben", "exist",                        "bare verb / mood",                 "S3"),

    # K — named individuals (entity-linking)
    ("K", "cleo", "Mari is happy",               "individual + property stored",     "S2"),
    ("K", "cleo", "Rome is a city",              "place individual",                 "S2"),
    ("K", "cleo", "Mari is Luca",                "distinct individuals (not eq)",    "S1"),
    ("K", "cleo", "Google is a company",         "org individual",                   "S2"),

    # L — edge punctuation / mood markers (R4a)
    ("L", "dan", "the cat is a dog??",           "QUESTION (double ?? = R4a)",       "S3"),
    ("L", "dan", "a cat is a mammal!?",          "QUESTION (mixed !?)",              "S3"),
    ("L", "dan", "you exist!",                   "assertion/emphatic",               "S3"),
    ("L", "dan", "really?",                      "bare question word",               "S3"),
]


def show():
    cat = None
    for c, spk, sent, exp, sev in BATCH:
        if c != cat:
            print(f"\n--- Category {c} ---"); cat = c
        print(f"  [{sev}] ({spk}) «{sent}»  -> {exp}")
    print(f"\nTOTAL: {len(BATCH)} probes / {len({b[0] for b in BATCH})} categories / "
          f"{len({b[1] for b in BATCH})} speakers.")


def wipe():
    mdb = MongoClient(os.getenv("MONGO_URI"))[os.getenv("MONGO_DB_NAME_MEMORY")]
    out = {c: mdb[c].delete_many({}).deleted_count for c in ("memory", "ideas", "actions")}
    print(f"WIPED disposable: {out}  (brain_state + KB + behavior_rules untouched)")


def inject():
    ok = fail = 0
    for c, spk, sent, exp, sev in BATCH:
        try:
            r = requests.get(f"{API}/input", params={"tokens": sent, "talker": spk, "prepare": 0}, timeout=120)
            st = r.json().get("status")
            print(f"  [{c}/{sev}] ({spk}) «{sent[:50]}» -> {r.status_code} {st}")
            ok += (st == "complete"); fail += (st != "complete")
        except Exception as e:
            print(f"  [{c}] «{sent[:40]}» -> ERROR {e!r}"); fail += 1
        time.sleep(0.1)
    print(f"\nINJECTED ok={ok} fail={fail} / {len(BATCH)}  (brain must be UP to react)")


if __name__ == "__main__":
    if "--list" in sys.argv or len(sys.argv) == 1: show()
    if "--wipe" in sys.argv: wipe()
    if "--inject" in sys.argv: inject()
