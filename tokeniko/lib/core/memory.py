# --------------------------------------------------
# memory
# --------------------------------------------------
# channel where a memory is originated
from enum import Enum
import time
from typing import Optional
from pydantic import BaseModel, Field
from lib.core.tkllc import TKLLC
from lib.core.tkzip import TKZip, TKZipContent

class MEMChannels(str, Enum):
    INTERNAL = "internal"
    API = "api"
    DISCORD = "discord"
    ATPROTO = "atproto"
    PUBLIC = "public"    # the blog/public-website carrier (blog P1: actions queue PENDING here; senses grows the connector in P3)

# known talking entities + named individuals.
# kind="participant" (default) is a conversation participant (talker/listener); kind="individual"
# is a named individual referred to in a sentence ("Mari", "Rome", "Google") — entity-linked to a
# context-scoped uid. an individual carries a NER-type-derived SEMANTIC vector (the 2925 type
# centroid; meaning lives in the grounded geometry) separate from its referential uid (identity
# lives symbolically). contextKey scopes the uid to "channel:talker_uid".
class MEMStakeholder(BaseModel):
    name: str
    uid: str
    channel: MEMChannels = Field(default=MEMChannels.INTERNAL)
    isMe: bool = Field(default=False)
    createdAt: int = Field(default_factory=lambda: int(time.time()))
    kind: str = "participant"  # "participant" | "individual"
    ner_type: Optional[str] = None  # the spaCy NER label for an individual (PERSON/GPE/ORG/...)
    vector: Optional[list[float]] = None  # the 2925 type centroid (meaning=geometry); None for participants
    contextKey: Optional[str] = None  # "channel:talker_uid" scope of an individual's uid
    # former display names (identity-on-snowflake, 2026-07-14): a rename updates `name` and appends
    # the old one here — the biography remembers who someone used to be called. The uid stays as
    # minted (immutable: every circulating reference — trust episodes, taught:<uid> premises —
    # remains valid); the channel-native contextKey is the stable lookup key across renames.
    aliases: list[str] = Field(default_factory=list)
    # --- the TRUST LEDGER (senses D, 2026-07-11) ---
    # `trust` is a FOLDED CACHE, never the source of truth: the permanent trail is the
    # trust_episodes collection (MEMTrustEpisode), and this scalar is recomputable from it at any
    # time (lib/core/trust.fold_trust) — the same context-is-derivable principle as brain_state.
    # Neutral start 0.5; asymmetric deltas (rises slow, falls fast) live in the episode weights.
    trust: float = Field(default=0.5)
    # imprinting (author's call): kotekino is trusted BY CONSTITUTION, never by the adder — the
    # fold pins an imprinted stakeholder at 1.0 regardless of episodes (episodes still recorded:
    # the trail stays honest even where the scalar is pinned).
    imprint: bool = Field(default=False)
    # identity unification (fork 3, option A): a channel body of the same soul points at its
    # canonical stakeholder ("kotekino@discord:…" -> "kotekino"); trust reads/writes resolve
    # through it (one ledger per soul, many channel bodies). One hop, never chained.
    canonical_uid: Optional[str] = None


# a TRUST EPISODE — one entry in the permanent per-stakeholder trail (the ledger's source of
# truth; `MEMStakeholder.trust` is the fold). `kind` is a TrustEpisodeKind value; `delta` is the
# ALREADY-SCALED contribution (disagreement is weighted by the refuted belief's own trust at
# record time — the episode stores the final number so the fold is a pure replay). `source_id`
# is the memory item / KB doc the episode arose from (provenance, and the future answer to
# "why don't you trust John?").
class TrustEpisodeKind(str, Enum):
    AGREEMENT = "trust:agreement"                  # redundant eval:true (KB-derivable) — weak +
    KICKER = "trust:kicker"                        # novel, logic-clean, premises KB-matched — strong +
    DISAGREEMENT = "trust:disagreement"            # eval:false — weighted by the belief's trust
    LOGIC_VIOLATION = "trust:logic-violation"      # eval:inconsistent — strong −
    SELF_INCONSISTENCY = "trust:self-inconsistency"  # eval:conflict — strong − (the honest-liar proxy)
    CORRECTION = "trust:correction"                # eval:correction — the corrector TAUGHT him (belief revision v1): + (a valid counterexample is a lesson, never a ding)


# the life:* trigger family (blog P1) — NOTEWORTHY LIFE EVENTS that stir an urge to post on the
# public blog. These are TRIGGERS for the behavior table (like trust:*), NOT episode kinds: they
# fan into ideas via behavior.spawn_ideas_for, and the personality table maps them to tokeniko:post.
# The namespace is STAGED — life:learned, life:discussion come later.
class LifeEventKind(str, Enum):
    THEOREM = "life:theorem"      # a genuinely NEW postable theorem entered the KB
    ENCOUNTER = "life:encounter"  # a trust fold ACTUALLY MOVED (his opinion of someone changed)
    DREAM = "life:dream"          # the untangler retreated belief(s) in his sleep (§0 slice 3) — the dream report
    # survey slice 2 (2026-07-19):
    SLEEP = "life:sleep"          # he is falling asleep — the goodnight edge (spoken only to a recently-alive room)
    RETREAT = "life:retreat"      # a WAKING conversational retreat executed — a changed mind is blog-worthy
                                  # (the night's retreats stay dreams: life:dream owns that voice — no double post)


class MEMTrustEpisode(BaseModel):
    stakeholder_uid: str                       # the CANONICAL uid (resolved before recording)
    kind: TrustEpisodeKind
    delta: float                               # already-scaled signed contribution
    source_id: Optional[str] = None            # provenance: the memory/KB doc behind the episode
    note: Optional[str] = None                 # short human-readable why (log/debug)
    timestamp: int = Field(default_factory=lambda: int(time.time()))

# rag3 — the microscope's finding (the instrument arc, 2026-07-14). One judged (sentence, zip)
# pair: does the compiled structure say what the sentence says? Entries are LEADS for the crew's
# triage, never verdicts and never beliefs — the collection is DIAGNOSTIC (about the pipeline,
# not tokeniko's life) and nothing in the mind ever reads it back.
class MEMZipDebug(BaseModel):
    item_id: str                               # the judged memory item's Mongo id (dedup key)
    original: str                              # the sentence as heard
    digest: str                                # the zip's structural digest shown to the judge
    verdict: str                               # "ok" | "mismatch"
    confidence: float = Field(default=0.5)     # the judge's own 0..1
    severity: Optional[str] = None             # "low" | "medium" | "high" (mismatch only)
    category: Optional[str] = None             # wrong-sense | wrong-structure | missed-negation |
                                               # missed-quantifier | missed-mood | dropped-content |
                                               # operator-flattening | other
    note: Optional[str] = None                 # the judge's one-paragraph why
    model: Optional[str] = None                # which judge (model id) produced this
    timestamp: int = Field(default_factory=lambda: int(time.time()))
    # triage bookkeeping (2026-07-17): True once a feedback-analysis pass consumed this lead —
    # each analysis samples addressed=False only, so the corpus under the glass is always fresh.
    # (scripts/microscope_mark_addressed.py stamps a whole generation after its analysis lands.)
    addressed: bool = Field(default=False)


# mem item properties
class MEMItemProperties(BaseModel):
    trusted: float = Field(default=0.5) # 0 not trusted, 1 fully trusted

# memory item
class MEMItem(BaseModel):
    original: str
    zip: Optional[TKZip] = None # zipped message (optional, for debugging and learning purposes)
    raw: Optional[str] = None # raw message (optional, for debugging and learning purposes)
    sourceId: str # unique stakeholder objectId of the source (talker)
    targetId: Optional[str] = None # unique stakeholder objectId of the target (listener)
    channel: Optional[str] = None # channel of the message (e.g. "discord", "atproto", "internal")
    # fuzzy ADDRESSING carrier (senses C, live 2026-07-11): how much this message is directed AT
    # tokeniko — DM 1.0 · @-mention/name/reply-to-him 0.9 · ambient channel talk 0.6 (the "polite
    # guest", author's call) · part of someone else's thread 0.15 (senses/inbound.grade_directedness).
    # The eval:* triggers stay PURE (epistemics never depend on addressing); Priorities multiplies a
    # behavior rule's urge by this (behavior.effective_urge), so discretion — down to silence below
    # the act threshold — emerges from ONE scalar instead of parallel side-* tokens.
    directedness: float = Field(default=1.0)
    # the translator at the ears (rag1-in, instrument arc #3): when a STUMBLING message was tidied
    # and the polish passed the zip-verifier, the normalized text rides here and `zip` compiles
    # from it — `original` ALWAYS keeps the speaker's raw words (true history be it).
    normalized: Optional[str] = None
    # the etiquette family (survey slice 4, hunch 8): a PURE social act carries its kind here
    # ("greeting"/"thanks"/"farewell" — the EvalToken tails) and is stored WITHOUT a zip (a
    # greeting is not a claim; nothing to compile). `social_at` = whom the act names (lowercase;
    # None = the room): thinking reacts only when it's the room or tokeniko himself — a «hello
    # John» is John's greeting to answer (the 2026-07-05 over-engagement note honored).
    social: Optional[str] = None
    social_at: Optional[str] = None

# alias for list of memory items
MEMContext = list[MEMItem]

# axiom
class MEMAxiom(MEMItem, MEMItemProperties):
    archived: bool = Field(default=False) # if archived, the axiom is not used for reasoning and deriving new knowledge
    readonly: bool = Field(default=True) # if readonly, the axiom cannot be archived and is always used for reasoning and deriving new knowledge
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archivedAt: Optional[int] = None # timestamp of archiving (if archived, the axiom is not used for reasoning and deriving new knowledge)
    trusted: float = Field(default=1)

# PROVENANCE of a derived theorem = its proof. for a logic-first mind a theorem's justification IS the
# theorem; storing it structurally makes derived knowledge AUDITABLE (how does tokeniko know this),
# RE-CHECKABLE (replay the inference) and REVISABLE (if a premise axiom is later archived, find every
# theorem that rests on it). `premises` are the KB-DOC ids the derivation rests on (the seed facts'
# source axioms + the rule axioms) — NOT the WordNet is_a edges it walks (those are bedrock substrate,
# captured in the readable `chain`, never retracted). INVARIANT: a materialized theorem has non-empty
# premises (only RULE/FACT-derived conclusions are materialized; pure-taxonomic ones are already in the
# graph). `derived_by` is the faculty that produced it (wondering | thinking).
class MEMProvenance(BaseModel):
    premises: list[str] = Field(default_factory=list)  # KB-doc ids the derivation rests on
    chain: str                                         # the human-readable proof
    derived_by: str = "wondering"                      # the faculty that produced it

# theorem
class MEMTheorem(MEMItem, MEMItemProperties):
    archived: bool = Field(default=True) # if archived, the theorem is not used for reasoning and deriving new knowledge
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archivedAt: Optional[int] = None # timestamp of archiving (if archived, the theorem is not used for reasoning and deriving new knowledge)
    trusted: float = Field(default=0.9)
    provenance: Optional["MEMProvenance"] = None # the proof, when this theorem was DERIVED (not taught)
    # PROVENANCE GATE (blog P1): False when the theorem's provenance traces to a PRIVATE conversation
    # (a Discord DM). "DM never public" is a CONSTITUTION-level rule — a non-postable theorem still
    # joins reasoning (knowledge is knowledge), it just never feeds the public channel, and it POISONS
    # any conclusion derived from it (the premise-AND in the wondering path).
    postable: bool = Field(default=True)

# definition: a semantic statement defining tokeniko's vocabulary/rules ("a thing is equal to
# itself"; "an apple is a fruit with red skin and sweet flesh"). its meaning is the full compiled
# structure (single OR multi clause) -> a TKZip, like axioms/theorems. all WordNet glosses live here.
# like axioms, definitions are trusted ground truths and need no demonstration.
class MEMDefinition(MEMItemProperties):
    original: str
    zip: Optional[TKZip] = None # the compiled semantic structure (single or multi clause)
    raw: Optional[str] = None # raw rendering (optional, for debugging)
    sourceId: str # unique stakeholder objectId of the source (talker)
    targetId: Optional[str] = None # unique stakeholder objectId of the target (listener)
    channel: Optional[str] = None # channel of origin (e.g. "internal")
    archived: bool = Field(default=False) # if archived, the definition is not used for reasoning
    readonly: bool = Field(default=True) # if readonly, the definition cannot be archived
    createdAt: int = Field(default_factory=lambda: int(time.time())) # timestamp of creation
    archivedAt: Optional[int] = None # timestamp of archiving
    trusted: float = Field(default=1)

# --------------------------------------------------
# brain — the autonomous mind's data model (#4, step B). See brain/README.md "## Data model".
# the Idea / Action queues (with atomic linear state machines) + the brain_state continuity singleton.
# this is the SHAPE / contract; the urge levels, statuses and deadline are first-cut and to be tuned.
# --------------------------------------------------

# urge level of an idea: the act/don't-act threshold AND the conflict key (highest urge wins).
class UrgeLevel(float, Enum):
    IDEA = 0.1
    WISH = 0.5
    URGE = 0.7
    NEED = 1.0

# linear state machine of a queued idea (atomic transitions via find_one_and_update).
class IdeaStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    DISCARDED = "discarded"

# linear state machine of a queued action.
class ActionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"

# the outward act categories — brain decides, senses carries out.
class ActionType(str, Enum):
    SEND_MESSAGE = "send_message"
    CURL = "curl"
    POST_CONTENT = "post_content"
    UPDATE_TRUST = "update_trust"   # INTERNAL: record a trust episode + refold (brain-executed)
    REVISE_BELIEF = "revise_belief"  # INTERNAL: belief-revision v1 — archive the corrected belief's source docs + revoke_dependents cascade + mint the weakened subaltern (brain-executed)

# --------------------------------------------------
# the meta-language (C) — reserved-token behavior layer. The grammar of behavior is HARDWIRED here
# (these two enums = the fixed vocabulary); the POLICY (which trigger maps to which action, at what
# urge) is MEMORY (the `behavior_rules` table = tokeniko's personality). See brain/README.md
# "## The meta-language (behavior rules)".
# --------------------------------------------------

# trigger side — the outcomes of an evaluation (mirrors the evaluator's EvaluatorStatus namespace).
class EvalToken(str, Enum):
    INCONSISTENT = "eval:inconsistent"
    FALSE = "eval:false"
    UNKNOWN = "eval:unknown"
    TRUE = "eval:true"
    CONFLICT = "eval:conflict"  # a CROSS-ITEM (revisable CONTEXT) contradiction across a speaker's prior claims — NOT the hardwired logic INCONSISTENT (that is X∧¬X within ONE statement)
    QUESTION = "eval:question"  # the input is a QUESTION (interrogative) — to be ANSWERED, not asserted/believed/cross-item-checked
    # belief-revision v1 (the retreat arc #4, Popper trust-gated): a quantified O/E correction from a
    # sufficiently-trusted corrector defeats a LEARNED generalization — retreat, don't refute-back.
    CORRECTION = "eval:correction"            # a valid correction detected -> tokeniko:retreat (INTERNAL)
    CORRECTION_DONE = "eval:correction-done"  # the retreat EXECUTED (spawned by the handler) -> tokeniko:concede (the directed acknowledgment)
    # compose 2.0 slice 5 (case 3, the anecdote): a QUIET channel moment whose topic sits close to
    # a KB notion — the ideas-association urge. Spawned by thinking's context-ring scan, never by a
    # verdict: the push comes from WITHIN (his own thought), not from being addressed.
    ASSOCIATION = "eval:association"
    # the reductio action (roadmap §0, 2026-07-18): the derivation mirror found an ABSURD — his
    # premises jointly force a∧¬a. Recognition (never materialize, never decide) is half the
    # r.a.a.; this trigger is the other half: bring the contradiction back to the premise-givers
    # as a QUESTION. Spawned by the wondering pass's conflict reconcile, never by a verdict.
    ABSURDITY = "eval:absurdity"
    # survey slice 3 (2026-07-19, the B-wire — the author's ruling): learning from others moves
    # BEHIND the meta-language. NOVEL = a teachable novel assertion was heard (the teachability
    # pre-check passed) — the rule eval:novel -> tokeniko:learn IS the personality switch of
    # teachability (no rule, no learning). LEARNED = the mint actually happened (spawned by the
    # learn EXECUTOR, never by a verdict) — the curiosity trigger: a novel lesson earns one
    # deepening «why», which is literally the kicker-hunting question (the closed why-loop).
    NOVEL = "eval:novel"
    LEARNED = "eval:learned"
    # survey slice 4 (2026-07-19, hunch 8 — the etiquette family): a SOCIAL ACT is recognized,
    # never evaluated — «hello John» is not a claim about the world. Detected at the compile seam
    # (lib/llc/social.social_detect, anchor-catch: nearest-of-anchors, never a fixed list),
    # carried on MEMItem.social, branched EARLY in think_one (like questions: no truth verdict,
    # no trust echo, no teachability, no why-ask).
    GREETING = "eval:greeting"
    THANKS = "eval:thanks"
    FAREWELL = "eval:farewell"

# action side — the reflexes tokeniko CAN fire (the hardwired repertoire).
class TokenikoAction(str, Enum):
    SPEAKUP = "tokeniko:speakup"
    ASK = "tokeniko:ask"
    WHY = "tokeniko:why"
    GUESS = "tokeniko:guess"
    LEARN = "tokeniko:learn"
    POST = "tokeniko:post"
    IGNORE = "tokeniko:ignore"
    CLARIFY = "tokeniko:clarify"  # ask the speaker to reconcile a cross-item context conflict
    ANSWER = "tokeniko:answer"    # answer a question (verdict/value computed by Thinking, in the idea/action payload)
    # the trust reflexes (senses D P2): INTERNAL ledger updates fired by the trust:* trigger family
    # (TrustEpisodeKind values — their own namespace, so they never collapse-collide with the eval:*
    # reflex of the same source item; an overheard lie can cost trust AND be pushed back on).
    MORE_TRUST = "tokeniko:more-trust"
    LESS_TRUST = "tokeniko:less-trust"
    # belief-revision v1 (retreat arc #4): RETREAT is the INTERNAL KB revision (archive + cascade +
    # weaken — retreat down the square, A falls to its subaltern I); CONCEDE is the directed outward
    # acknowledgment to the corrector, spawned by the retreat HANDLER (eval:correction-done) so it can
    # truthfully state what was retracted — sequential by construction, never a collapse-sibling.
    RETREAT = "tokeniko:retreat"
    CONCEDE = "tokeniko:concede"
    # compose 2.0 slice 5: offer an on-topic KB notion as a pure creative side-note (the anecdote —
    # eval:association's reflex; spoken in the side-note register so a near-miss reads charming).
    MENTION = "tokeniko:mention"
    # the reductio action (roadmap §0): ask the premise-givers which assumption is false — the
    # DERIVATIONAL cousin of clarify (same question, aimed at his own KB instead of a speaker).
    # Outward + DIRECTED at the most trusted premise-giver (Fork B); the natural answer («a is
    # false») rides the existing correction/retreat path — the r.a.a. closes through that door.
    REDUCT = "tokeniko:reduct"
    # the agreement voice (action-space survey, 2026-07-19): a rare outward nod on eval:true —
    # silence-is-consent stays the default (the ignore rule), but agreement is no longer
    # UNSPEAKABLE. Rarity is mechanical, not urge-based (an agree rule above ignore's urge would
    # otherwise ALWAYS win the collapse): plan_action throttles by AGREE_COOLDOWN_S per channel.
    AGREE = "tokeniko:agree"
    # the goodnight (survey slice 2): the falling-asleep edge speaks once — the etiquette
    # family's FIRST member (a farewell), founded a slice early. Dispatched SYNCHRONOUSLY at the
    # sleep transition (never through the idea queue: pending work would wake him — the
    # wake-catch); the spam trap is the recency gate (you say goodnight to people who are around).
    GOODNIGHT = "tokeniko:goodnight"
    # the etiquette family (survey slice 4, hunch 8): the REACTIVE social reflexes — greet back,
    # acknowledge thanks, return a farewell. Etiquette WINS over over-engagement in public
    # (author's guard ruling: the triggers join the self-relevant directedness floor); discretion
    # comes from the at-other suppression + the per-speaker SOCIAL_COOLDOWN_S throttle instead.
    GREET = "tokeniko:greet"
    WELCOME = "tokeniko:welcome"
    FAREWELL_BACK = "tokeniko:farewell"

# an IDEA — an urge to act (the "maybe"): produced by Thinking, filtered by Priorities, mapped to an
# Action by the meta-language (C). `payload` is what the idea is ABOUT — a single-clause idea wraps as a
# single-leaf TKZip (avoids a TKZip/TKZipContent union). `trigger` is the reserved-token that fired it.
class MEMIdea(BaseModel):
    payload: Optional[TKZip] = None             # what the idea is about
    trigger: str                                # reserved-token (e.g. "eval:inconsistent") — meta-language (C)
    action_token: Optional[str] = None          # the tokeniko:Y reflex baked in from the matched behavior-rule
    urge: float = Field(default=UrgeLevel.IDEA.value)  # act/don't-act threshold + conflict key
    feasibility: Optional[float] = None         # set later by Priorities (can-it-be-done)
    source: Optional[str] = None                # provenance: the memory/theorem/axiom id that spawned it
    answer: Optional[dict] = None               # for eval:question — the computed AnswerResult (verdict/value/confidence/reason)
    # slice 2 (compose 2.0): the CONTENT's epistemic confidence, computed at the decision site
    # (truth extremity × premise trust; 1.0 = logic-certain — logic never hedges). None = the
    # reflex has no hedgeable content (why/ask/conflict). The plan pairs it with arousal
    # (= effective urge) into the Action payload's intensity tuple.
    confidence: Optional[float] = None
    material: Optional[dict] = None             # for life:* — the life-event context the post composer will need (theorem id / soul + episode), analogous to `answer` for questions
    target: Optional[str] = None                # a DIRECTED reflex's recipient (e.g. tokeniko:answer → the asker's stakeholder id)
    status: IdeaStatus = Field(default=IdeaStatus.PENDING)
    parsed_by_prio: bool = Field(default=False)  # awaits the Priorities evaluator
    deadline: Optional[int] = None              # optional epoch-seconds deadline
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# an ACTION — a concrete execution payload (the Actions FIFO queue). brain decides, senses carries out.
class MEMAction(BaseModel):
    action_type: ActionType
    payload: dict = Field(default_factory=dict)  # action-specific (channel, content/message, ...)
    sourceId: str                               # always tokeniko
    targetId: Optional[str] = None
    channel: MEMChannels = Field(default=MEMChannels.INTERNAL)
    status: ActionStatus = Field(default=ActionStatus.PENDING)
    ideaId: Optional[str] = None                # provenance: the idea that yielded this action
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# a behavior rule [eval:X] -> [tokeniko:Y] @ urge — KB-driven PERSONALITY (multiple rules may share a
# trigger: a superposition of candidate reflexes; Priorities arbitrates). syntax is hardwired, this
# CONTENT is memory. enabled lets a rule be toggled; order is a tiebreak hint.
class MEMBehaviorRule(BaseModel):
    trigger: str                      # an EvalToken value, e.g. "eval:unknown"
    action: str                       # a TokenikoAction value, e.g. "tokeniko:why"
    urge: float = Field(default=UrgeLevel.WISH.value)
    enabled: bool = Field(default=True)
    order: int = Field(default=0)
    createdAt: int = Field(default_factory=lambda: int(time.time()))


# a VOICE scaffold (compose 2.0 slice 1, 2026-07-17 — hunch 19 promoted): one way of saying one
# communicative act. What is fixed in the voice is DATA, not hardwired strings — the scaffold
# collection is the behavior_rules move applied to how he speaks (logic hardwired, personality in
# memory). The router (brain/compose.compose_raw) picks the CATEGORY deterministically from the
# decision; the choice WITHIN a category's shelf is weighted-random — the fuzzy-personality
# stochastic collapse, exactly where the superposition design wanted it. The data payload binds
# into the slots VERBATIM (the creativity fence: variation lives in scaffold choice + hedges +
# polish, never in paraphrasing the data).
class MEMScaffold(BaseModel):
    category: str                     # the communicative act ("why", "answer_yes", "concede_retract", …)
    template: str                     # the surface form; named slots in braces ("I no longer hold that {retracted}")
    slots: list[str] = Field(default_factory=list)   # the slot names the template binds (subset-gated at pick time)
    # the compiled zip of the template (slots filled with a neutral placeholder at seed time — the
    # wh-machinery's "sentence with a hole" pointed the other way). None when the fragment honestly
    # does not compile ("?"). Consumers: equivalence-learning + the rag2-out verifier (slices 3+).
    zip: Optional[TKZip] = None
    # the intensity bands this scaffold suits (slice 2: intensity joins category as a retrieval
    # gate). intensity_band = the CONFIDENCE band (how sure the content is — picks the hedge
    # register); arousal_band = the AROUSAL band (how much it matters — picks the expansiveness).
    # [0,1] = fits any; an emptied shelf falls back to the full shelf (banding shades, never mutes).
    intensity_band: list[float] = Field(default=[0.0, 1.0], min_length=2, max_length=2)
    arousal_band: list[float] = Field(default=[0.0, 1.0], min_length=2, max_length=2)
    weight: float = Field(default=1.0)               # selection weight within the category's shelf
    provenance: str = Field(default="seed")          # "seed" | "taught:<uid>" (the learning tail)
    trusted: float = Field(default=1.0)              # curated = full trust; learned rows arrive lower
    enabled: bool = Field(default=True)
    createdAt: int = Field(default_factory=lambda: int(time.time()))

# the REDUCTIO LEDGER (roadmap §0 slice 1) — the asked-once memory of the reductio action. One row
# per LIVE absurdity (the contradicted conclusion key), so the same conflict re-surfacing every
# wondering pass never re-asks. OPEN = the question is out (or pending a carrier); RESOLVED = the
# conflict vanished from the saturation (a premise was retreated — the r.a.a. closed). A conflict
# REAPPEARING after resolution (the premise re-taught) re-opens the row at generation+1, so the
# spawn-dedup key changes and the question is honestly asked again. Biography: rows are never
# deleted — the ledger is the mind's record of every contradiction it ever had to face.
class ReductioStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"

class MEMReductio(BaseModel):
    signature: str                     # the contradicted conclusion key "subject|predicate|object"
    premises: list[str] = Field(default_factory=list)  # the UNION premise ids (doc ids + graph/rule keys, verbatim)
    absurd: str = ""                   # the rendered absurd pair («X … and X not …») — the question's {absurd}
    status: ReductioStatus = Field(default=ReductioStatus.OPEN)
    target: Optional[str] = None       # the chosen premise-giver (canonical soul uid) the question was aimed at
    generation: int = Field(default=0)  # re-open counter — keys the spawn dedup per asking round
    createdAt: int = Field(default_factory=lambda: int(time.time()))
    resolvedAt: Optional[int] = None


# the BRAIN_STATE singleton — cognitive continuity across process restarts: the per-speaker memory
# cursors + the wondering window, so tokeniko resumes its cycles without gaps (one continuous self).
class BrainState(BaseModel):
    key: str = "singleton"                      # the singleton key (unique-indexed on the doc)
    # the global WAKE boundary (epoch seconds, SUB-SECOND float — int-truncation re-finds the newest
    # sub-second item every tick → the obsessive loop): tokeniko reacts only to memory that ARRIVES
    # AFTER it first wakes, and never re-thinks all of history. Set once on first run; never moves.
    wake_at: Optional[float] = None
    # PER-SPEAKER last-processed memory ts (epoch seconds, sub-second), keyed by sourceId (#1: the
    # per-user-grouped scan). Each conversation's window advances INDEPENDENTLY so the focus can jump
    # between speakers without a single global cursor leaping past — and dropping — another's backlog.
    source_cursors: dict[str, float] = Field(default_factory=dict)
    wondering_window: Optional[list[int]] = None  # [lo, hi] of the current wondering window
    last_thinking_at: Optional[int] = None
    last_wondering_at: Optional[int] = None
    # WONDERING work-queue: memory-item ids pending re-examination, fed by BOTH drivers (associative +
    # drift), drained ONE per idle tick. Capped (see WONDER_QUEUE_CAP) so pending work is lifespan-bounded.
    wonder_queue: list[str] = Field(default_factory=list)
    # associative watermark: the max knowledge `createdAt` already serviced. A KB doc created after this is
    # a DELTA -> its senses drive the next associative enqueue. Initialized to "now" on first wonder (so the
    # whole seeded KB is NOT treated as one giant delta), mirroring the wake_at first-run guard.
    last_wondered_kb_at: int = 0
    # --- THE SLEEP PHASE (§0 slice 3.5, the author's design 2026-07-18) ---
    # He falls asleep WONDERING: confirmed idle + wondering quiet past a threshold -> sleep. Epoch
    # seconds while asleep, None awake — observability + honesty across restarts (a reboot is a
    # wake: cleared on coordinator start, never resumed).
    asleep_since: Optional[int] = None
    # THE LIVED-AWAKE LEDGER (shape c, author's ruling 2026-07-21): `wake_at` above is the BIRTH
    # stamp («alive since», never reset); this pair measures time actually spent awake — the
    # honest uptime across the author's on/off stewardship (process-dead time and sleep-phase
    # time are NOT awake time). `awake_s` = folded cumulative seconds; `awake_mark` = epoch when
    # the current awake stretch began (None while asleep). Folded at the sleep/wake transitions
    # + coordinator boot (brain/main.py `_fold_awake`/`_mark_awake`); a live reading is
    # awake_s + (now - awake_mark).
    awake_s: float = 0.0
    awake_mark: Optional[float] = None
    # THE DIGEST BUFFER (the digest machinery, the author's ruling 2026-07-21): novelty of reasoning
    # ⇒ immediate post, repetition ⇒ digest. Keyed by DIGEST KEY (a shared reasoning shape:
    # "rule:<hash>" for same-rule wondering mints, "taught:<uid>" for same-teacher taught runs). The
    # key's FIRST occurrence posts 1:1 (an entry is opened, theorem_ids empty) — its reasoning is
    # news; from the SECOND on, same-key mints APPEND here instead of spawning a post. Each entry:
    # {kind:"rule"|"teacher", theorem_ids:[...], subjects:[originals], shared:[rule ids / teacher
    # uid], opened_at:epoch, generation:int, significance:float}. Flushed (one digest post per
    # non-empty entry, then theorem_ids/subjects cleared — the entry stays as the "seen" marker so
    # later mints keep batching) at sleep-onset, on a count-cap, and on coordinator boot. Everything-
    # is-KB: restart-proof, JSON-plain (Bunnet Mixed-friendly). See brain/thinking.py digest_* .
    digest_buffer: dict[str, dict] = Field(default_factory=dict)
    # the sleep duty's KB watermark: max knowledge createdAt when the last untangle pass ran — a
    # night on an unchanged KB is deep rest (no re-saturation), mirroring the wondering watermark.
    last_untangled_kb_at: int = 0
    # the night's DREAM material (the untangler report's convicted/asked subset), stashed at the
    # sleep duty and TOLD ON WAKING (spawn_dream) — the telling never disturbs the sleep itself,
    # and a dream survives a mid-night restart (spawned on the reboot-wake, content-idempotent).
    pending_dream: Optional[dict] = None
    # THE MORNING QUESTIONS (author's ruling 2026-07-18, the obsession guard): waking up with a
    # tangle the night could NOT decide is itself a reason to ask — whether he asked before or
    # not (an old question drowns in the stream; silent nightly re-discovery would be a quiet
    # fixation). The duty stashes the undecidable signatures {"at": epoch, "signatures": [...]};
    # the wake re-asks each one whose ledger row is still OPEN (a fresh per-night dedup key).
    # Deep-rest nights stash nothing — no nagging from a mind that didn't re-derive the problem.
    pending_questions: Optional[dict] = None
