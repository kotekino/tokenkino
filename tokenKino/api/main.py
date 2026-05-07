from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient
from lib.llc.parser import llc, llc_diagram
from lib.tagger.functions import tagger
from dotenv import load_dotenv
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.llc.preparser import llc_pre_init, llc_pre_prepare, llc_pre_typos
from lib.tkll.functions import tkll_searchSimilarTokens
from lib.llc.decompiler import llc_decompile, llc_decompiler_init

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

    # init preparser
    await llc_pre_init(ai_client)
    await llc_decompiler_init(ai_client)
    
    yield  #where fastapi runs
    
    # shutdown logic
    db_client.close()

# init fastapi app
app = FastAPI(lifespan=lifespan)

# ------------------------
# TKLLC endpoints
# ------------------------
@app.get("/api/v1/tkllc")
async def process(tokens: str = Query(..., min_length=3, description="Sentence to submit"), output: int = 0, prepare: int = 0):
    try:
        preparsedTokens = await llc_pre_prepare(tokens) if prepare == 1 else tokens
        result = llc(preparsedTokens, None, app.state.ai_client)
        raw = result['raw']
        output = await llc_decompile(raw) if output == 1 else ''
        flat = result['flat']
        recursive = result['recursive']
       
        res = {
            "original": tokens,
            "raw output": raw,
            "polished output": output,
            "llc flat": flat,
            "llc recursive": recursive,
        }
        status = "complete"
    except Exception as error:
        res = repr(error)
        status = "failed"
    return {"status": status, "data": res}

@app.get("/api/v1/tkllc/render", response_class=HTMLResponse)
async def render(tokens: str = Query(..., min_length=3, description="Sentence to submit"), prepare: int = 0):
    preparsedTokens = await llc_pre_prepare(tokens) if prepare == 1 else tokens
    res = llc_diagram(preparsedTokens)
    return res

# ------------------------
# TKLL endpoints
# ------------------------
@app.get("/api/v1/tkll/dict")
async def search(token: str, prepare: int = 0):
    preparsedTokens = await llc_pre_prepare(token) if prepare == 1 else token
    doc = tkll_searchSimilarTokens(preparsedTokens)

    return doc

# ------------------------
# PRE endpoints
# ------------------------
@app.get("/api/v1/pre/polish")
async def polish(tokens: str):
    res = await llc_pre_typos(tokens)
    return res

@app.get("/api/v1/pre/prepare")
async def prepare(tokens: str):
    res = await llc_pre_prepare(tokens)
    return res

# ------------------------
# OUT endpoints
# ------------------------
@app.get("/api/v1/out")
async def polish(tokens: str):
    res = await llc_decompile(tokens)
    return res