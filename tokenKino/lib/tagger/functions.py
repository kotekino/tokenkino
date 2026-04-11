from pymongo import MongoClient

def tagger(mongoClient: MongoClient=None):
    return f"Hello, I am the tagger!"