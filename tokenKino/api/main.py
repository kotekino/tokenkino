from contextlib import asynccontextmanager
import copy
import os
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient
from lib.llc.parser import parser, parser_diagram
from lib.tagger.functions import tagger
from dotenv import load_dotenv
from lib.core.io import get_stakeholder, get_tokenkino, init_io
from lib.core.models import TKMemoryItemDoc
from lib.llc.preparser import preparser_init, preparser_prepare, preparser_translate, preparser_typos
from lib.tkll.functions import tkll_searchSimilarTokens
from lib.llc.decompiler import decompiler_decompile, decompiler_init, decompiler_raw
from lib.core.entities import TKLLC, TKStatement
from lib.llc.flattener import flattener_flat
from lib.core.constants import _ME_UID

# env load (MONGO_URI, ecc.)
load_dotenv()

# define lifespan for startup and shutdown logic
async def lifespan(app: FastAPI):

    # IO init
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME")  
    db_name_memory = os.getenv("MONGO_DB_NAME_MEMORY")  
    ollama_host = os.getenv("OLLAMA_HOST")

    db_client, db_memory_client, ai_client = init_io(uri, db_name, db_name_memory, ollama_host)
    tokenkino = get_tokenkino()

    # Salviamo nello stato
    app.state.db_client = db_client
    app.state.ai_client = ai_client
    app.state.db_memory_client = db_memory_client
    app.state.tokenkino = tokenkino

    # init preparser
    await preparser_init(ai_client)
    await decompiler_init(ai_client)
    
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
        # get talker entity from memory, or create it if not exists
        talkerEntity = get_stakeholder(talker)

        # pipeline pre (if prepare), recursive, flat, raw, output (if output)
        preparsedTokens = await preparser_prepare(tokens) if prepare == 1 else tokens
        recursiveResult = parser(preparsedTokens, talkerEntity, app.state.tokenkino, app.state.ai_client)
        recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
        flatResult: TKLLC = flattener_flat(recursiveResultCopy) 
        rawResult = decompiler_raw(flatResult) if flatResult else ''
        outputResult = await decompiler_decompile(rawResult) if output == 1 else ''
       
        res = {
            "original": tokens,
            "raw output": rawResult,
            "polished output": outputResult,
            "llc flat": flatResult,
            "llc recursive": recursiveResult,
        }
        status = "complete"

        # store in memory
        if flatResult:
            memory_doc: TKMemoryItemDoc = TKMemoryItemDoc(
                tkllc=flatResult,
                sourceId=str(talkerEntity.id),
                targetId=str(app.state.tokenkino.id),
                channel="api",
                raw=tokens
            )
            memory_doc.insert()

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

@app.get("/api/v1/pre/translate")
async def prepare(tokens: str):
    res = await preparser_translate(tokens)
    return res

# ------------------------
# OUT endpoints
# ------------------------
@app.get("/api/v1/out")
async def polish(tokens: str):
    res = await decompiler_decompile(tokens)
    return res