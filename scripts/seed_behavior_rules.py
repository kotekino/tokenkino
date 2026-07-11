# ------------------------------------------------------------------------------------------------
# seed_behavior_rules.py — seed tokeniko's default PERSONALITY (the meta-language C, step C).
# The behavior_rules table = the KB-driven policy of the reserved-token behavior layer:
# [eval:X] -> [tokeniko:Y] @ urge. The SYNTAX is hardwired (brain/behavior.py); THIS content is
# memory. Multiple rules may share a trigger (a superposition of candidate reflexes).
#
# No pipeline needed — just init_io (no parser/compiler). Idempotent: a rule with the same
# (trigger, action) is skipped.
#
# Dry-run by default (prints the shape, writes nothing). Pass --apply to persist.
#   python scripts/seed_behavior_rules.py            # DRY-RUN
#   python scripts/seed_behavior_rules.py --apply    # insert the rules (idempotent)
# ------------------------------------------------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko"))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tokeniko", ".env"))

from lib.core.io import init_io
from lib.core.models import TKBehaviorRuleDoc
from lib.core.memory import EvalToken, TokenikoAction, TrustEpisodeKind

# the starter personality: (trigger, action, urge, comment).
RULES = [
    (EvalToken.INCONSISTENT.value, TokenikoAction.SPEAKUP.value, 0.7,  "speak up about a contradiction"),
    (EvalToken.FALSE.value,        TokenikoAction.SPEAKUP.value, 0.6,  "push back on a KB-false claim"),
    (EvalToken.UNKNOWN.value,      TokenikoAction.WHY.value,     0.6,  '"what is X?"'),
    (EvalToken.UNKNOWN.value,      TokenikoAction.GUESS.value,   0.55, "interpolate a provisional def (the superposition partner)"),
    (EvalToken.TRUE.value,         TokenikoAction.IGNORE.value,  0.2,  "corroboration: usually stay quiet"),
    (EvalToken.CONFLICT.value,     TokenikoAction.CLARIFY.value, 0.7,  "a cross-item conflict — ask the speaker to reconcile"),
    (EvalToken.QUESTION.value,     TokenikoAction.ANSWER.value,  0.9,  "answer a question (yes/no/value/idk, directed at the asker)"),
    # the trust reflexes (senses D P2): trust:* triggers -> INTERNAL ledger updates. Their urges are
    # tokeniko's TRUST SENSITIVITY (a personality dial, editable as data): all clear the 0.5 keep
    # threshold — internal actions are exempt from the directedness multiplication (an overheard lie
    # still costs trust), so these fire regardless of who the speaker was addressing.
    (TrustEpisodeKind.AGREEMENT.value,          TokenikoAction.MORE_TRUST.value, 0.55, "a corroborated truth — weak +"),
    (TrustEpisodeKind.KICKER.value,             TokenikoAction.MORE_TRUST.value, 0.65, "novel-valid-bridging (the closed why-loop) — the twin-soul signal"),
    (TrustEpisodeKind.DISAGREEMENT.value,       TokenikoAction.LESS_TRUST.value, 0.6,  "contradicts a belief — scaled by that belief's own trust"),
    (TrustEpisodeKind.LOGIC_VIOLATION.value,    TokenikoAction.LESS_TRUST.value, 0.65, "a logic violation — logic is sacred"),
    (TrustEpisodeKind.SELF_INCONSISTENCY.value, TokenikoAction.LESS_TRUST.value, 0.7,  "self-contradiction — the honest-liar proxy"),
]


def main():
    apply = "--apply" in sys.argv
    print(f"seed_behavior_rules.py — {'APPLYING (writes enabled)' if apply else 'DRY-RUN (no writes)'}")

    init_io(
        os.getenv("MONGO_URI"), os.getenv("MONGO_DB_NAME"),
        os.getenv("MONGO_DB_NAME_MEMORY"), os.getenv("OLLAMA_HOST"),
    )

    inserted = skipped = 0
    for trigger, action, urge, comment in RULES:
        existing = TKBehaviorRuleDoc.find_one({"trigger": trigger, "action": action}).run()
        print(f"\n  [{trigger}] -> [{action}] @ {urge}   # {comment}")
        if existing is not None:
            print("    -> already present, skipping")
            skipped += 1
            continue
        if apply:
            doc = TKBehaviorRuleDoc(trigger=trigger, action=action, urge=urge).insert()
            print(f"    -> inserted rule id={doc.id}")
            inserted += 1
        else:
            print("    -> would insert (dry-run)")

    print(f"\nDONE [{'APPLIED' if apply else 'DRY-RUN'}]  inserted={inserted}  skipped={skipped}")


if __name__ == "__main__":
    main()
