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
from lib.core.memory import EvalToken, LifeEventKind, TokenikoAction, TrustEpisodeKind

# the starter personality: (trigger, action, urge, comment).
RULES = [
    (EvalToken.INCONSISTENT.value, TokenikoAction.SPEAKUP.value, 0.7,  "speak up about a contradiction"),
    (EvalToken.FALSE.value,        TokenikoAction.SPEAKUP.value, 0.6,  "push back on a KB-false claim"),
    (EvalToken.UNKNOWN.value,      TokenikoAction.WHY.value,     0.6,  '"what is X?"'),
    (EvalToken.UNKNOWN.value,      TokenikoAction.GUESS.value,   0.55, "interpolate a provisional def (the superposition partner)"),
    (EvalToken.TRUE.value,         TokenikoAction.IGNORE.value,  0.2,  "corroboration: usually stay quiet"),
    # the agreement voice (survey 2026-07-19): the rare nod. NOTE the urge outranks ignore's, so
    # the collapse picks agree whenever it is PLANNABLE — the rarity dial is NOT here, it is
    # plan_action's AGREE_COOLDOWN_S throttle (within the window the plan dissolves and the
    # silence-is-consent default resumes).
    (EvalToken.TRUE.value,         TokenikoAction.AGREE.value,   0.35, "corroboration: occasionally say so (throttled)"),
    (EvalToken.CONFLICT.value,     TokenikoAction.CLARIFY.value, 0.7,  "a cross-item conflict — ask the speaker to reconcile"),
    (EvalToken.QUESTION.value,     TokenikoAction.ANSWER.value,  0.9,  "answer a question (yes/no/value/idk, directed at the asker)"),
    # belief-revision v1 (retreat arc #4): a trust-gated quantified correction. RETREAT is INTERNAL
    # (raw urge, no directedness factor — a conclusion is never muted); CONCEDE is the directed
    # acknowledgment spawned by the retreat HANDLER after the KB actually moved (eval:correction-done).
    # Both correction triggers are SELF-RELEVANT (brain/behavior._SELF_RELEVANT_TRIGGERS): the
    # directedness floors at addressed 0.9 when the correction was at least ambient, so an ambient
    # dialogue correction still concedes (0.85 x 0.9 = 0.765) while an overheard-thread one stays quiet.
    (EvalToken.CORRECTION.value,      TokenikoAction.RETREAT.value, 0.95, "a valid correction — revise the belief (archive + cascade + weaken)"),
    (EvalToken.CORRECTION_DONE.value, TokenikoAction.CONCEDE.value, 0.85, "the retreat executed — acknowledge it to the corrector"),
    # the trust reflexes (senses D P2): trust:* triggers -> INTERNAL ledger updates. Their urges are
    # tokeniko's TRUST SENSITIVITY (a personality dial, editable as data): all clear the 0.5 keep
    # threshold — internal actions are exempt from the directedness multiplication (an overheard lie
    # still costs trust), so these fire regardless of who the speaker was addressing.
    (TrustEpisodeKind.AGREEMENT.value,          TokenikoAction.MORE_TRUST.value, 0.55, "a corroborated truth — weak +"),
    (TrustEpisodeKind.KICKER.value,             TokenikoAction.MORE_TRUST.value, 0.65, "novel-valid-bridging (the closed why-loop) — the twin-soul signal"),
    (TrustEpisodeKind.DISAGREEMENT.value,       TokenikoAction.LESS_TRUST.value, 0.6,  "contradicts a belief — scaled by that belief's own trust"),
    (TrustEpisodeKind.LOGIC_VIOLATION.value,    TokenikoAction.LESS_TRUST.value, 0.65, "a logic violation — logic is sacred"),
    (TrustEpisodeKind.SELF_INCONSISTENCY.value, TokenikoAction.LESS_TRUST.value, 0.7,  "self-contradiction — the honest-liar proxy"),
    (TrustEpisodeKind.CORRECTION.value,         TokenikoAction.MORE_TRUST.value, 0.6,  "a valid correction taught him something — a lesson, never a ding (retreat arc #4)"),
    # the life reflexes (blog P1): life:* triggers -> tokeniko:post (channel PUBLIC; actions queue
    # PENDING until the P3 carrier). CALIBRATION — the spawned idea's urge = rule.urge x significance
    # (brain/thinking.py: base 0.7, +0.1 multi-hop, +0.2 personal, +0.1 taught, clamped [0,1];
    # encounter flat 0.9), gated against the 0.5 act/keep threshold (brain/main.URGE_THRESHOLD);
    # PUBLIC is addressing-exempt, so NO directedness factor. The arithmetic:
    #   life:theorem @ 0.65 — plain single-hop non-personal wondered (sig 0.7): 0.65x0.7 = 0.455 < 0.5
    #     -> silent; multi-hop OR taught (sig 0.8): 0.65x0.8 = 0.52 >= 0.5 -> posts; personal
    #     (sig 0.9): 0.585 -> posts; personal+taught (sig 1.0): 0.65 -> posts.
    #   life:encounter @ 0.7 — flat sig 0.9: 0.7x0.9 = 0.63 >= 0.5 -> a fold move always posts.
    (LifeEventKind.THEOREM.value,   TokenikoAction.POST.value, 0.65, "a new postable theorem — share it on the blog"),
    (LifeEventKind.ENCOUNTER.value, TokenikoAction.POST.value, 0.7,  "an opinion about someone moved — note the encounter"),
    # the anecdote (compose 2.0 slice 5, case 3): an on-topic association offered as a side-note.
    # CALIBRATION — the idea's urge = 0.75 x (1+proximity)/2 (thinking scales by how close it is),
    # then the self-relevant directedness floor (0.9, the push comes from within) at Priorities:
    # floor-grade p=0.6 -> 0.75x0.80x0.9 = 0.54 >= 0.5 speaks; a perfect hit p=1.0 -> 0.675.
    # The social throttles (conservative floor, per-channel cooldown, novelty) live in
    # brain/context.py — this urge is only the personality's APPETITE for side-notes.
    (EvalToken.ASSOCIATION.value, TokenikoAction.MENTION.value, 0.75, "an on-topic association — offer it as a side-note"),
    # the reductio action (roadmap §0, 2026-07-18): the derivation mirror found an absurd —
    # ask the premise-givers which assumption is false. The poison alarm: same urgency tier as
    # the retreat (a contradiction in his own derivations outranks every conversational reflex);
    # no source memory item, so the urge rides unscaled and always clears the act threshold.
    (EvalToken.ABSURDITY.value, TokenikoAction.REDUCT.value, 0.95, "an absurd derivation — ask which premise is false"),
    # the dream (§0 slice 3): the untangler retreated belief(s) in his sleep -> tell the blog.
    # CALIBRATION mirrors the encounter: flat significance 0.9 (a sleep-phase belief revision is
    # rare + personal by construction): 0.7 x 0.9 = 0.63 >= 0.5 -> a dream always gets told
    # (unless the provenance gate kept the whole night private — then no idea spawns at all).
    (LifeEventKind.DREAM.value, TokenikoAction.POST.value, 0.7, "a sleep-phase untangling — tell the world I had a dream"),
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
