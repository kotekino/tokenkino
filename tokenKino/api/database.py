import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv() # Carica le variabili dal file .env

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.get_database("MONGO_DB_NAME")