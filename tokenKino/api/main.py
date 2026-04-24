from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient
from lib.llc.functions import llc, llc_diagram, llc_preparser
from lib.tagger.functions import tagger
from dotenv import load_dotenv
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc

# env load (MONGO_URI, ecc.)
load_dotenv()

# define lifespan for startup and shutdown logic
async def lifespan(app: FastAPI):

    # IO init
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME")    
    ollama_host = os.getenv("OLLAMA_HOST")

    db_client, ai_client = init_io(uri, db_name, ollama_host)
    
    # Salviamo nello stato
    app.state.db_client = db_client
    app.state.ai_client = ai_client
    
    yield  #where fastapi runs
    
    # shutdown logic
    db_client.close()

# init fastapi app
app = FastAPI(lifespan=lifespan)

# endpoints
@app.get("/api/v1/llc")
def process(q: str = Query(..., min_length=3, description="Sentence to submit")):
    try:
        res = llc(q, None, app.state.ai_client)
        status = "complete"
    except Exception as error:
        res = repr(error)
        status = "failed"
    return {"status": status, "data": res}

@app.get("/api/v1/render", response_class=HTMLResponse)
def render(q: str = Query(..., min_length=3, description="Sentence to submit")):
    res = llc_diagram(q)
    return res

@app.get("/api/v1/dict")
def search(word: str):
    doc = TKDictionaryDoc.find_one(TKDictionaryDoc.word == word).run()
    return doc

@app.get("/api/v1/llc_preparser")
def preparse(tokens: str):
    res = llc_preparser(tokens, None, app.state.ai_client)
    return res