import os
from pymongo import MongoClient
from bunnet import init_bunnet
from lib.core.models import BaseDoc, DictionaryDoc, NameDoc, PlaceDoc

def init_io(connection_string: str = None, db_name: str = None):
    # init mongo client
    uri = connection_string or os.getenv("MONGO_URI")
    client = MongoClient(uri)
    client._default_database_name = db_name

    init_bunnet(
        database=client[db_name],
        document_models=[
            BaseDoc,
            DictionaryDoc,
            NameDoc,
            PlaceDoc
        ]
    )

    return client