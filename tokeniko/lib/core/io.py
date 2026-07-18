import logging
import os
import time
import ollama
from pymongo import MongoClient
from bunnet import init_bunnet
from lib.core.models import TKAxiomDoc, TKBaseDoc, TKDefinitionDoc, TKDictionaryDoc, TKMarkerDoc, TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKNameDoc, TKPlaceDoc, TKPropertyDoc, TKRelationDoc, TKDerivedRelationDoc, TKDerivedRuleDoc, TKTheoremDoc, TKIdeaDoc, TKActionDoc, TKBehaviorRuleDoc, TKBrainStateDoc, TKReductioDoc, TKScaffoldDoc, TKTrustEpisodeDoc, TKZipDebugDoc
from lib.core.constants import _ME_NAME, _ME_UID
from lib.core.memory import MEMChannels

logger = logging.getLogger("tokeniko-io")

def init_io(mongo_uri: str = None, mongo_db_name: str = None, mongo_db_name_memory: str = None, ollama_uri: str = None):
   
   # --- MONGO AI ---
    uri = mongo_uri or os.getenv("MONGO_URI")
    mongo_db_name = mongo_db_name or os.getenv("MONGO_DB_NAME")
    mongo_db_name_memory = mongo_db_name_memory or os.getenv("MONGO_DB_NAME_MEMORY")

    # opt-in socket timeout (ms): without it a read on a dead/stalled connection blocks FOREVER
    # (pymongo default) — a slept laptop or a wedged server-side op freezes the whole loop (the
    # 2026-07-09 soak). Long-lived unattended processes (the brain daemon / soak drivers) should set
    # MONGO_SOCKET_TIMEOUT_MS generously (e.g. 300000); a timed-out op raises and the loop retries.
    socket_timeout = os.getenv("MONGO_SOCKET_TIMEOUT_MS")
    kwargs = {"socketTimeoutMS": int(socket_timeout)} if socket_timeout else {}
    mongo_client = MongoClient(uri, **kwargs)
    mongo_client._default_database_name = mongo_db_name
    
    # init knowledge base
    init_bunnet(
        database=mongo_client[mongo_db_name],
        document_models=[
            TKBaseDoc,
            TKDictionaryDoc,
            TKNameDoc,
            TKPlaceDoc,
            TKMarkerDoc,
            TKPropertyDoc,
            TKRelationDoc,
            TKDerivedRelationDoc,
            TKDerivedRuleDoc
        ]
    )

    mongo_client_memory = MongoClient(uri)
    mongo_client_memory._default_database_name = mongo_db_name_memory
    
    # init memory
    init_bunnet(
        database=mongo_client_memory[mongo_db_name_memory],
        document_models=[
            TKAxiomDoc,
            TKTheoremDoc,
            TKDefinitionDoc,
            TKMemoryItemDoc,
            TKMemoryStakeholdersDoc,
            TKIdeaDoc,
            TKActionDoc,
            TKBehaviorRuleDoc,
            TKBrainStateDoc,
            TKScaffoldDoc,
            TKReductioDoc,
            TKTrustEpisodeDoc,
            TKZipDebugDoc
        ]
    )

    # --- OLLAMA AI ---
    ollama_uri = ollama_uri or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ai_client = ollama.AsyncClient(host=ollama_uri)

    return mongo_client, mongo_client_memory, ai_client   

# search for stakeholders in memory
def get_tokeniko():
    
    tokeniko = TKMemoryStakeholdersDoc.find_one({"uid": _ME_UID}).run()

    if not tokeniko:
        tokeniko = TKMemoryStakeholdersDoc(uid=_ME_UID, name=_ME_NAME, isMe=True, channel=MEMChannels.INTERNAL).save()

    return tokeniko

# try getting a stakeholder by uid — SNOWFLAKE-FIRST across renames (identity fission fix,
# 2026-07-14): the uid embeds the mutable display name ("hellen@discord:12345"), so a Discord
# rename used to mint a SECOND soul for the same person (trust history orphaned). Resolution now
# goes uid → channel-native contextKey ("discord:12345", name-free) → mint; a contextKey hit with
# a fresh name is a RENAME — the doc keeps its uid as minted (immutable: every circulating
# reference stays valid), updates `name`, and remembers the old one in `aliases`. Individuals are
# EXCLUDED from the fallback: their contextKey is the SCOPE (the talker), shared by every
# individual that talker mentions — never an identity.
def get_stakeholder(name: str, channel: MEMChannels = MEMChannels.INTERNAL,
                    display_name: str = None, context_key: str = None):

    stakeholder = TKMemoryStakeholdersDoc.find_one({"uid": name}).run()

    # a channel-scoped uid ("renzo@discord:12345") carries its own contextKey after the "@" —
    # the same scheme as entity-linked individuals; outbound uses it to resolve a DM destination.
    if context_key is None and "@" in name:
        context_key = name.split("@", 1)[1]

    if not stakeholder and context_key:
        stakeholder = TKMemoryStakeholdersDoc.find_one(
            {"contextKey": context_key, "kind": {"$ne": "individual"}}
        ).run()
        if stakeholder:
            # same channel-native id, new surface uid -> a rename, never a new soul
            new_name = display_name or name.split("@", 1)[0]
            if new_name and new_name != stakeholder.name:
                if stakeholder.name not in (stakeholder.aliases or []):
                    stakeholder.aliases = (stakeholder.aliases or []) + [stakeholder.name]
                logger.info("[io] rename detected on %s: %r -> %r (uid unchanged)",
                            context_key, stakeholder.name, new_name)
                stakeholder.name = new_name
                stakeholder.save()

    if not stakeholder:
        stakeholder = TKMemoryStakeholdersDoc(
            uid=name, name=display_name or name, isMe=False, channel=channel,
            contextKey=context_key,
        ).save()

    return stakeholder

# get-or-create an entity-linked named individual stakeholder by its context-scoped uid. idempotent:
# returns the existing doc if present, else creates one with kind="individual" + its NER type, 2925
# type centroid (vector) and context key. only the storing paths (e.g. /input) call this — NOT
# /evaluate, which must stay pure.
def upsert_individual(name: str, uid: str, ner_type: str, vector: list, context_key: str, channel: MEMChannels = MEMChannels.INTERNAL):

    individual = TKMemoryStakeholdersDoc.find_one({"uid": uid}).run()

    if not individual:
        individual = TKMemoryStakeholdersDoc(
            uid=uid,
            name=name,
            isMe=False,
            kind="individual",
            ner_type=ner_type,
            vector=vector,
            contextKey=context_key,
            channel=channel
        ).save()

    return individual