import os
import time
import ollama
from pymongo import MongoClient
from bunnet import init_bunnet
from lib.core.models import TKAxiomDoc, TKBaseDoc, TKDictionaryDoc, TKMemoryItemDoc, TKMemoryStakeholdersDoc, TKNameDoc, TKPlaceDoc, TKTheoremDoc
from lib.core.constants import _ME_NAME, _ME_UID

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
            TKPlaceDoc
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
        tokeniko = TKMemoryStakeholdersDoc(uid=_ME_UID, name=_ME_NAME, isMe=True, channel="internal").save()

    return tokeniko

# try getting a stakeholder by uid
def get_stakeholder(name: str, channel: str = "internal"):
    
    stakeholder = TKMemoryStakeholdersDoc.find_one({"uid": name}).run()

    if not stakeholder:
        uid: str = ""  # generate a unique uid for the stakeholder if name == "unknown", otherwise use the name as uid
        if name == "unknown":
            uid = f"unknown_{int(time.time())}"
        else:
            uid = name

        stakeholder = TKMemoryStakeholdersDoc(uid=uid, name=uid, isMe=False, channel=channel).save()

    return stakeholder