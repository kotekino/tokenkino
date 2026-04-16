import os
import ollama
from pymongo import MongoClient
from bunnet import init_bunnet
from lib.core.models import TKBaseDoc, TKDictionaryDoc, TKNameDoc, TKPlaceDoc

def init_io(mongo_uri: str = None, mongo_db_name: str = None, ollama_uri: str = None):
   
   # --- MONGO AI ---
    uri = mongo_uri or os.getenv("MONGO_URI")
    mongo_db_name = mongo_db_name or os.getenv("MONGO_DB_NAME")
    
    mongo_client = MongoClient(uri)
    mongo_client._default_database_name = mongo_db_name
    
    # Inizializziamo Bunnet: da qui in poi BaseDoc & co. sono "vivi"
    init_bunnet(
        database=mongo_client[mongo_db_name],
        document_models=[
            TKBaseDoc,
            TKDictionaryDoc,
            TKNameDoc,
            TKPlaceDoc
        ]
    )

    # --- OLLAMA AI ---
    ollama_uri = ollama_uri or os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ai_client = ollama.Client(host=ollama_uri)

    return mongo_client, ai_client   