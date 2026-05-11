from contextlib import asynccontextmanager
import copy
import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient
from lib.llc.parser import parser, parser_diagram
from lib.tagger.functions import tagger
from dotenv import load_dotenv
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.llc.preparser import preparser_init, preparser_prepare, preparser_typos
from lib.tkll.functions import tkll_searchSimilarTokens
from lib.llc.decompiler import llc_decompile, llc_decompiler_init, llc_raw
from lib.core.entities import TKLLC, TKStatement
from lib.llc.flattener import flattener_flat

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
    await preparser_init(ai_client)
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
async def process(tokens: str = Query(..., min_length=3, description="Sentence to submit"), output: int = 0, prepare: int = 0, talker: str = "unknown"):
    try:
        
        # pipeline pre (if prepare), recursive, flat, raw, output (if output)
        preparsedTokens = await preparser_prepare(tokens) if prepare == 1 else tokens
        recursiveResult = parser(preparsedTokens, talker,  None, app.state.ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: TKLLC = flattener_flat(recursiveResultCopy) 
        rawResult = llc_raw(flatResult) if flatResult else ''
        outputResult = await llc_decompile(rawResult) if output == 1 else ''
       
        res = {
            "original": tokens,
            "raw output": rawResult,
            "polished output": outputResult,
            "llc flat": flatResult,
            "llc recursive": recursiveResult,
        }
        status = "complete"
    except Exception as error:
        res = repr(error)
        status = "failed"
    return {"status": status, "data": res}

@app.get("/api/v1/tkllc/render", response_class=HTMLResponse)
async def render(tokens: str = Query(..., min_length=3, description="Sentence to submit"), prepare: int = 0):
    preparsedTokens = await preparser_prepare(tokens) if prepare == 1 else tokens
    res = parser_diagram(preparsedTokens)
    return res

# ------------------------
# TKLL endpoints
# ------------------------
@app.get("/api/v1/tkll/dict")
async def search(token: str, prepare: int = 0):
    preparsedTokens = await preparser_prepare(token) if prepare == 1 else token
    doc = tkll_searchSimilarTokens(preparsedTokens)

    return doc

# ------------------------
# PRE endpoints
# ------------------------
@app.get("/api/v1/pre/polish")
async def polish(tokens: str):
    res = await preparser_typos(tokens)
    return res

@app.get("/api/v1/pre/prepare")
async def prepare(tokens: str):
    res = await preparser_prepare(tokens)
    return res

# ------------------------
# OUT endpoints
# ------------------------
@app.get("/api/v1/out")
async def polish(tokens: str):
    res = await llc_decompile(tokens)
    return res