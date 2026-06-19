import os
import time
import ollama
from pymongo import MongoClient
from bunnet import init_bunnet
from lib.core.models import TKAxiomDoc, TKBaseDoc, TKDefinitionDoc, TKDictionaryDoc, TKMarkerDoc, TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKNameDoc, TKPlaceDoc, TKPropertyDoc, TKRelationDoc, TKTheoremDoc
from lib.core.constants import _ME_NAME, _ME_UID
from lib.core.memory import MEMChannels

def init_io(mongo_uri: str = None, mongo_db_name: str = None, mongo_db_name_memory: str = None, ollama_uri: str = None):
   
   # --- MONGO AI ---
    uri = mongo_uri or os.getenv("MONGO_URI")
    mongo_db_name = mongo_db_name or os.getenv("MONGO_DB_NAME")
    mongo_db_name_memory = mongo_db_name_memory or os.getenv("MONGO_DB_NAME_MEMORY")
    
    mongo_client = MongoClient(uri)
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
            TKRelationDoc
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
            TKMemoryStakeholdersDoc
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

# try getting a stakeholder by uid
def get_stakeholder(name: str, channel: MEMChannels = MEMChannels.INTERNAL):

    stakeholder = TKMemoryStakeholdersDoc.find_one({"uid": name}).run()

    if not stakeholder:
        stakeholder = TKMemoryStakeholdersDoc(uid=name, name=name, isMe=False, channel=channel).save()

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