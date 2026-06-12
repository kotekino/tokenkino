from contextlib import asynccontextmanager
import copy
import os
import time
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from bunnet import PydanticObjectId
from pymongo import MongoClient
from lib.llc.parser import parser, parser_diagram, parser_init
from dotenv import load_dotenv
from lib.core.io import get_stakeholder, get_tokeniko, init_io
from lib.core.models import TKAxiomDoc, TKMemoryItemDoc, TKTheoremDoc
from lib.llc.preparser import preparser_init, preparser_prepare, preparser_translate, preparser_typos
from lib.tkll.functions import tkll_searchSimilarTokens
from lib.llc.decompiler import decompiler_decompile, decompiler_init, decompiler_raw
from lib.core.tk import TKStatement, TKStatements
from lib.core.tkllc import TKLLC
from lib.core.memory import MEMChannels
from lib.llc.compiler import compiler_compile, compiler_zipGetBaseMarker
from lib.core.tkzip import TKZip

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
    tokeniko = get_tokeniko()

    # Salviamo nello stato
    app.state.db_client = db_client
    app.state.ai_client = ai_client
    app.state.db_memory_client = db_memory_client
    app.state.tokeniko = tokeniko

    # init preparser
    parser_init()
    await preparser_init(ai_client)
    await decompiler_init(ai_client)
    
    yield  #where fastapi runs
    
    # shutdown logic
    db_client.close()
    db_memory_client.close()

# init fastapi app
app = FastAPI(lifespan=lifespan)

# ------------------------
# MAIN endpoints
# ------------------------
# store an axiom in memory, given a sentence
@app.get("/api/v1/theorem")
async def post_theorem(tokens: str):
    try:
        recursiveResult = parser(tokens, app.state.tokeniko, app.state.tokeniko, app.state.ai_client)
        recursiveResultCopy: TKStatements = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
        theorem = None
        status = "complete"

        # store in memory
        if flatResult:
            theorem: TKTheoremDoc = TKTheoremDoc(
                original=tokens,
                zip=flatResult[1],
                raw=rawResult,
                sourceId=str(app.state.tokeniko.id),
                targetId=str(app.state.tokeniko.id),
                channel=MEMChannels.INTERNAL
            )
            theorem.insert()
    except Exception as error:
        theorem = repr(error)
        status = "failed"
    return {"status": status, "data": theorem}

# ------------------------
# AXIOMS resource (/api/v1/axioms)
# ------------------------
# request bodies
class AxiomIn(BaseModel):
    tokens: str  # sentence to compile and store as an axiom

class AxiomPatch(BaseModel):
    # tutti opzionali: si aggiornano solo i campi presenti (partial update)
    tokens: Optional[str] = None       # se presente, ricompila original/zip/raw
    trusted: Optional[float] = None
    archived: Optional[bool] = None
    readonly: Optional[bool] = None
    channel: Optional[str] = None

class AxiomReplace(BaseModel):
    # replacement update: la frase è obbligatoria, i flag tornano ai default se non passati
    tokens: str
    trusted: float = 1.0
    archived: bool = False
    readonly: bool = True

# lightweight view for listing (senza lo zip, troppo grande)
class AxiomSummary(BaseModel):
    id: PydanticObjectId = Field(alias="_id")
    original: str
    raw: Optional[str] = None
    trusted: float
    archived: bool
    readonly: bool
    channel: Optional[str] = None
    createdAt: int

# parse + compile a sentence into the fields stored on an axiom
def _compile_axiom_fields(tokens: str) -> dict:
    recursiveResult = parser(tokens, app.state.tokeniko, app.state.tokeniko, app.state.ai_client)
    recursiveResultCopy: TKStatement = copy.deepcopy(recursiveResult)
    flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
    if not flatResult:
        raise ValueError("compilation produced no result")
    rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
    return {"original": tokens, "zip": flatResult[1], "raw": rawResult}

# fetch an axiom by id or raise 404 (also validates the object id -> 400)
def _get_axiom_or_404(object_id: str) -> TKAxiomDoc:
    try:
        oid = PydanticObjectId(object_id)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid object id")
    axiom = TKAxiomDoc.get(oid)
    if axiom is None:
        raise HTTPException(status_code=404, detail="axiom not found")
    return axiom

# list axioms (summary view, no zip); optional filter by archived
@app.get("/api/v1/axioms")
async def list_axioms(archived: Optional[bool] = None):
    query = {} if archived is None else {"archived": archived}
    axioms = TKAxiomDoc.find(query).project(AxiomSummary).to_list()
    return {"status": "complete", "data": axioms}

# get a single axiom (full document, including zip)
@app.get("/api/v1/axioms/{object_id}")
async def get_axiom(object_id: str):
    axiom = _get_axiom_or_404(object_id)
    return {"status": "complete", "data": axiom}

# insert a new axiom, given a sentence (was GET /api/v1/axiom)
@app.post("/api/v1/axioms")
async def create_axiom(payload: AxiomIn):
    try:
        fields = _compile_axiom_fields(payload.tokens)
        axiom: TKAxiomDoc = TKAxiomDoc(
            original=fields["original"],
            zip=fields["zip"],
            raw=fields["raw"],
            sourceId=str(app.state.tokeniko.id),
            targetId=str(app.state.tokeniko.id),
            channel=MEMChannels.INTERNAL
        )
        axiom.insert()
        return {"status": "complete", "data": axiom}
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# partial update: only the provided fields change (recompiles if 'tokens' given)
@app.patch("/api/v1/axioms/{object_id}")
async def patch_axiom(object_id: str, payload: AxiomPatch):
    axiom = _get_axiom_or_404(object_id)
    try:
        updates = payload.model_dump(exclude_unset=True)
        if "tokens" in updates:
            fields = _compile_axiom_fields(updates.pop("tokens"))
            axiom.original = fields["original"]
            axiom.zip = fields["zip"]
            axiom.raw = fields["raw"]
        for key, value in updates.items():
            setattr(axiom, key, value)
        # mantieni coerente il timestamp di archiviazione
        if "archived" in updates:
            axiom.archivedAt = int(time.time()) if axiom.archived else None
        axiom.save()
        return {"status": "complete", "data": axiom}
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# replacement update: recompiles the sentence and resets flags to the body
@app.put("/api/v1/axioms/{object_id}")
async def put_axiom(object_id: str, payload: AxiomReplace):
    axiom = _get_axiom_or_404(object_id)
    try:
        fields = _compile_axiom_fields(payload.tokens)
        axiom.original = fields["original"]
        axiom.zip = fields["zip"]
        axiom.raw = fields["raw"]
        axiom.trusted = payload.trusted
        axiom.archived = payload.archived
        axiom.readonly = payload.readonly
        axiom.archivedAt = int(time.time()) if payload.archived else None
        axiom.save()
        return {"status": "complete", "data": axiom}
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# delete an axiom
@app.delete("/api/v1/axioms/{object_id}")
async def delete_axiom(object_id: str):
    axiom = _get_axiom_or_404(object_id)
    axiom.delete()
    return {"status": "complete", "data": {"deleted": object_id}}

# ------------------------
# TKLLC endpoints
# ------------------------
@app.get("/api/v1/tkllc")
async def process(tokens: str = Query(..., min_length=3, description="Sentence to submit"), output: int = 0, prepare: int = 0, talker: str = "unknown"):
    try:
        # get talker entity from memory, or create it if not exists
        talkerEntity = get_stakeholder(talker, channel=MEMChannels.API)

        # pipeline pre (if prepare), recursive, flat, raw, output (if output)
        preparsedTokens = await preparser_prepare(tokens) if prepare == 1 else tokens
        recursiveResult = parser(preparsedTokens, talkerEntity, app.state.tokeniko, app.state.ai_client)
        recursiveResultCopy: TKStatements = copy.deepcopy(recursiveResult)
        flatResult: tuple[TKLLC, TKZip] = compiler_compile(recursiveResultCopy)
        rawResult = decompiler_raw(flatResult[0]) if flatResult[0] else ''
        outputResult = await decompiler_decompile(rawResult) if output == 1 else ''
       
        res = {
            "original": tokens,
            "raw output": rawResult,
            "polished output": outputResult,
            "llc flat": flatResult[0],
            "llc recursive": recursiveResult,
        }
        status = "complete"

        # store in memory
        if flatResult:
            memory_doc: TKMemoryItemDoc = TKMemoryItemDoc(
                original=tokens,
                zip=flatResult[1],
                raw=rawResult,
                sourceId=str(talkerEntity.id),
                targetId=str(app.state.tokeniko.id),
                channel=MEMChannels.API
            )
            memory_doc.insert()

    except Exception as error:
        res = repr(error)
        status = "failed"
    return {"status": status, "data": res}

@app.get("/api/v1/render", response_class=HTMLResponse)
async def render(tokens: str = Query(..., min_length=3, description="Sentence to submit"), prepare: int = 0):
    preparsedTokens = await preparser_prepare(tokens) if prepare == 1 else tokens
    res = parser_diagram(preparsedTokens)
    return res

# ------------------------
# TKLL endpoints
# ------------------------
@app.get("/api/v1/dict")
async def search(token: str, prepare: int = 0):
    preparsedTokens = await preparser_prepare(token) if prepare == 1 else token
    doc = tkll_searchSimilarTokens(preparsedTokens)

    return doc

@app.get("/api/v1/markers")
async def search(token: str):
    result = compiler_zipGetBaseMarker(token)
    return result

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
async def out(tokens: str):
    res = await decompiler_decompile(tokens)
    return res