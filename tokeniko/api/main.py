import copy
import os
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from lib.llc.parser import parser, parser_diagram, parser_init
from lib.core.io import get_stakeholder, get_tokeniko, init_io, upsert_individual
from lib.core.models import TKMemoryItemDoc
from lib.core.evaluation_harness import zip_senses
from lib.llc.preparser import preparser_init, preparser_prepare, preparser_translate, preparser_typos
from lib.llc.utils import utils_searchDissimilarTokens, utils_searchSimilarTokens
from lib.llc.decompiler import decompiler_decompile, decompiler_init, decompiler_raw
from lib.core.tk import TKStatements
from lib.core.tkllc import TKLLC
from lib.core.memory import MEMChannels, MEMProvenance
from lib.llc.compiler import compiler_compile, compiler_zipGetBaseMarker
from lib.core.tkzip import TKZip
from api.services import AxiomService, DefinitionService, TheoremService, StakeholderService, MemoryService, EvaluationService
from api.schemas import (
    AxiomIn, AxiomPatch, AxiomReplace, AxiomSummary, axiom_or_http,
    DefinitionIn, DefinitionPatch, DefinitionReplace, DefinitionSummary, definition_or_http,
    TheoremIn, TheoremPatch, TheoremReplace, TheoremMaterializeIn, TheoremSummary, theorem_or_http,
    EvaluateIn,
    StakeholderSummary, stakeholder_or_http,
    MemoryIn, MemorySummary, memory_or_http,
    create_or_http,
)

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

    # service layer (business logic + mongo ops)
    app.state.axiom_service = AxiomService(tokeniko, ai_client)
    app.state.definition_service = DefinitionService(tokeniko, ai_client)
    app.state.theorem_service = TheoremService(tokeniko, ai_client)
    app.state.stakeholder_service = StakeholderService()
    app.state.memory_service = MemoryService()
    app.state.evaluation_service = EvaluationService(tokeniko, ai_client)

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
# AXIOMS resource (/api/v1/axioms)
# ------------------------
# list axioms (summary view, no zip); optional filter by archived
@app.get("/api/v1/axioms")
async def list_axioms(archived: Optional[bool] = None):
    axioms = app.state.axiom_service.list(archived=archived, projection=AxiomSummary)
    return {"status": "complete", "data": axioms}

# get a single axiom (full document, including zip)
@app.get("/api/v1/axioms/{object_id}")
async def get_axiom(object_id: str):
    axiom = axiom_or_http(lambda: app.state.axiom_service.get(object_id))
    return {"status": "complete", "data": axiom}

# insert a new axiom, given a sentence
@app.post("/api/v1/axioms")
async def create_axiom(payload: AxiomIn):
    try:
        axiom = create_or_http(lambda: app.state.axiom_service.create(payload.tokens))
        return {"status": "complete", "data": axiom}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# partial update: only the provided fields change (recompiles if 'tokens' given)
@app.patch("/api/v1/axioms/{object_id}")
async def patch_axiom(object_id: str, payload: AxiomPatch):
    updates = payload.model_dump(exclude_unset=True)
    try:
        axiom = create_or_http(lambda: axiom_or_http(lambda: app.state.axiom_service.patch(object_id, updates)))
        return {"status": "complete", "data": axiom}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# replacement update: recompiles the sentence and resets flags to the body
@app.put("/api/v1/axioms/{object_id}")
async def put_axiom(object_id: str, payload: AxiomReplace):
    try:
        axiom = create_or_http(lambda: axiom_or_http(lambda: app.state.axiom_service.replace(object_id, **payload.model_dump())))
        return {"status": "complete", "data": axiom}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# delete an axiom
@app.delete("/api/v1/axioms/{object_id}")
async def delete_axiom(object_id: str):
    axiom_or_http(lambda: app.state.axiom_service.delete(object_id))
    return {"status": "complete", "data": {"deleted": object_id}}

# ------------------------
# DEFINITIONS resource (/api/v1/definitions) — semantic statements (single OR multi clause; TKZip)
# ------------------------
# list definitions (summary view, no zip); optional filter by archived
# WRITE-PATH INVARIANT (Brain v1.1 step 1): definitions are the DESIGN-TIME vocabulary — no runtime
# path may write them (runtime learning writes AXIOMS; theorems are derived-only via /materialize).
# TOKENIKO_DESIGN_TIME=0 locks every mutating /definitions route (403) so an embodied, live tokeniko
# physically cannot have its vocabulary edited through the API; unset/1 (the default) keeps the
# design bench open. Reads are always allowed.
def _require_design_time():
    if os.getenv("TOKENIKO_DESIGN_TIME", "1").lower() in ("0", "false", "no"):
        raise HTTPException(
            status_code=403,
            detail="definitions are design-time only (write-path invariant); "
                   "runtime learning writes axioms — set TOKENIKO_DESIGN_TIME=1 to edit the vocabulary",
        )


@app.get("/api/v1/definitions")
async def list_definitions(archived: Optional[bool] = None):
    definitions = app.state.definition_service.list(archived=archived, projection=DefinitionSummary)
    return {"status": "complete", "data": definitions}

# get a single definition (full document, including zip)
@app.get("/api/v1/definitions/{object_id}")
async def get_definition(object_id: str):
    definition = definition_or_http(lambda: app.state.definition_service.get(object_id))
    return {"status": "complete", "data": definition}

# insert a new definition, given a sentence (single OR multi clause)
@app.post("/api/v1/definitions")
async def create_definition(payload: DefinitionIn):
    _require_design_time()
    try:
        definition = create_or_http(lambda: app.state.definition_service.create(payload.tokens))
        return {"status": "complete", "data": definition}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# partial update: only the provided fields change (recompiles if 'tokens' given)
@app.patch("/api/v1/definitions/{object_id}")
async def patch_definition(object_id: str, payload: DefinitionPatch):
    _require_design_time()
    updates = payload.model_dump(exclude_unset=True)
    try:
        definition = create_or_http(lambda: definition_or_http(lambda: app.state.definition_service.patch(object_id, updates)))
        return {"status": "complete", "data": definition}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# replacement update: recompiles the sentence and resets flags to the body
@app.put("/api/v1/definitions/{object_id}")
async def put_definition(object_id: str, payload: DefinitionReplace):
    _require_design_time()
    try:
        definition = create_or_http(lambda: definition_or_http(lambda: app.state.definition_service.replace(object_id, **payload.model_dump())))
        return {"status": "complete", "data": definition}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# delete a definition
@app.delete("/api/v1/definitions/{object_id}")
async def delete_definition(object_id: str):
    _require_design_time()
    definition_or_http(lambda: app.state.definition_service.delete(object_id))
    return {"status": "complete", "data": {"deleted": object_id}}

# ------------------------
# THEOREMS resource (/api/v1/theorems) — derived knowledge (full TKZip). No `readonly` flag.
# ------------------------
# list theorems (summary view, no zip); optional filter by archived
@app.get("/api/v1/theorems")
async def list_theorems(archived: Optional[bool] = None):
    theorems = app.state.theorem_service.list(archived=archived, projection=TheoremSummary)
    return {"status": "complete", "data": theorems}

# get a single theorem (full document, including zip)
@app.get("/api/v1/theorems/{object_id}")
async def get_theorem(object_id: str):
    theorem = theorem_or_http(lambda: app.state.theorem_service.get(object_id))
    return {"status": "complete", "data": theorem}

# insert a new theorem, given a sentence
@app.post("/api/v1/theorems")
async def create_theorem(payload: TheoremIn):
    try:
        theorem = create_or_http(lambda: app.state.theorem_service.create(payload.tokens))
        return {"status": "complete", "data": theorem}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# MATERIALIZE a DERIVED conclusion as a first-class theorem (wondering-v2 / brain→API seam): ACTIVE +
# trusted, carrying its provenance (premises + chain), deduped on the SEMANTIC conclusion. The brain
# (parser-free) renders a derived conclusion to NL and POSTs it here; the service compiles it through
# the real pipeline. Returns the existing theorem (no write) when the conclusion is already held.
@app.post("/api/v1/theorems/materialize")
async def materialize_theorem(payload: TheoremMaterializeIn):
    provenance = MEMProvenance(premises=payload.premises, chain=payload.chain, derived_by=payload.derived_by)
    try:
        theorem = create_or_http(lambda: app.state.theorem_service.materialize(payload.tokens, provenance, trusted=payload.trusted, senses=payload.senses, postable=payload.postable))
        return {"status": "complete", "data": theorem}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# partial update: only the provided fields change (recompiles if 'tokens' given)
@app.patch("/api/v1/theorems/{object_id}")
async def patch_theorem(object_id: str, payload: TheoremPatch):
    updates = payload.model_dump(exclude_unset=True)
    try:
        theorem = create_or_http(lambda: theorem_or_http(lambda: app.state.theorem_service.patch(object_id, updates)))
        return {"status": "complete", "data": theorem}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# replacement update: recompiles the sentence and resets flags to the body
@app.put("/api/v1/theorems/{object_id}")
async def put_theorem(object_id: str, payload: TheoremReplace):
    try:
        theorem = create_or_http(lambda: theorem_or_http(lambda: app.state.theorem_service.replace(object_id, **payload.model_dump())))
        return {"status": "complete", "data": theorem}
    except HTTPException:
        raise
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# delete a theorem
@app.delete("/api/v1/theorems/{object_id}")
async def delete_theorem(object_id: str):
    theorem_or_http(lambda: app.state.theorem_service.delete(object_id))
    return {"status": "complete", "data": {"deleted": object_id}}

# ---------------------------------
# STAKEHOLDERS resource (/api/v1/stakeholders) (LIST, GET) — read-only
# ---------------------------------
# list stakeholders (summary view)
@app.get("/api/v1/stakeholders")
async def list_stakeholders():
    stakeholders = app.state.stakeholder_service.list(projection=StakeholderSummary)
    return {"status": "complete", "data": stakeholders}

# get a single stakeholder (full document)
@app.get("/api/v1/stakeholders/{object_id}")
async def get_stakeholder_resource(object_id: str):
    stakeholder = stakeholder_or_http(lambda: app.state.stakeholder_service.get(object_id))
    return {"status": "complete", "data": stakeholder}

# ---------------------------------
# MEMORY resource (/api/v1/memory) (CREATE, LIST, GET, SEARCH) — timeseries log, no update
# ---------------------------------
# list recent memory items (summary view, no zip); optional limit
@app.get("/api/v1/memory")
async def list_memory(limit: int = 100):
    items = app.state.memory_service.list(projection=MemorySummary, limit=limit)
    return {"status": "complete", "data": items}

# search the memory log by timeframe / source / target / channel.
# NOTE: declared BEFORE /memory/{object_id} so "search" isn't captured as an id.
# `from`/`to` are epoch SECONDS (int); `from` is aliased since it is a Python keyword.
@app.get("/api/v1/memory/search")
async def search_memory(
    frm: Optional[int] = Query(None, alias="from"),
    to: Optional[int] = None,
    source: Optional[str] = None,
    target: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 100,
):
    items = app.state.memory_service.search(
        frm=frm, to=to, source=source, target=target, channel=channel, limit=limit
    )
    return {"status": "complete", "data": items}

# get a single memory item (full document)
@app.get("/api/v1/memory/{object_id}")
async def get_memory(object_id: str):
    item = memory_or_http(lambda: app.state.memory_service.get(object_id))
    return {"status": "complete", "data": item}

# append a new memory item (plain log entry; no compilation)
@app.post("/api/v1/memory")
async def create_memory(payload: MemoryIn):
    try:
        item = app.state.memory_service.create(
            original=payload.original,
            sourceId=payload.sourceId,
            targetId=payload.targetId,
            channel=payload.channel,
            metadata=payload.metadata,
        )
        return {"status": "complete", "data": item}
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# ---------------------------------
# EVALUATE action (/api/v1/evaluate) — compile a sentence and evaluate its truth against tokeniko's
# knowledge (definitions + axioms + theorems). Pure: stores nothing.
# ---------------------------------
@app.post("/api/v1/evaluate")
async def evaluate(payload: EvaluateIn):
    try:
        result = app.state.evaluation_service.evaluate(payload.tokens)
        return {"status": "complete", "data": result}
    except Exception as error:
        return {"status": "failed", "data": repr(error)}

# ------------------------
# UTILS endpoints (debugging; may be removed later)
# ------------------------
@app.get("/api/v1/utils/dict")
async def search(token: str, prepare: int = 0, opposite: int = 0):
    preparsedTokens = await preparser_prepare(token) if prepare == 1 else token
    if opposite == 0:
        doc = utils_searchSimilarTokens(preparsedTokens) 
    else:
        doc = utils_searchDissimilarTokens(preparsedTokens) 

    return doc

@app.get("/api/v1/utils/markers")
async def search(token: str):
    result = compiler_zipGetBaseMarker(token)
    return result

@app.get("/api/v1/utils/polish")
async def polish(tokens: str):
    res = await preparser_typos(tokens)
    return res

@app.get("/api/v1/utils/prepare")
async def prepare(tokens: str):
    res = await preparser_prepare(tokens)
    return res

@app.get("/api/v1/utils/translate")
async def prepare(tokens: str):
    res = await preparser_translate(tokens)
    return res

@app.get("/api/v1/utils/render", response_class=HTMLResponse)
async def render(tokens: str = Query(..., min_length=3, description="Sentence to submit"), prepare: int = 0):
    preparsedTokens = await preparser_prepare(tokens) if prepare == 1 else tokens
    res = parser_diagram(preparsedTokens)
    return res

# ------------------------
# COMPILER endpoints
# ------------------------
# walk the recursive parse for entity-linked named individuals (TKName with a uid) — recurses into
# nested statements. exposes the full name payload (uid + ner + 2925 type centroid) so the storing
# path can home each individual in the stakeholders collection.
def _collect_individuals(statements) -> list:
    found = []
    for stat in statements:
        for ent in getattr(stat, "entities", []):
            payload = ent.payload
            if getattr(payload, "entity_type", None) == "statement":
                found.extend(_collect_individuals([payload]))
            elif getattr(payload, "entity_type", None) == "name" and getattr(payload, "uid", None):
                found.append(payload)
    return found

@app.get("/api/v1/input")
async def process(tokens: str = Query(..., min_length=3, description="Sentence to submit"), output: int = 0, prepare: int = 0, talker: str = "unknown",
                  talker_name: Optional[str] = None, channel: str = MEMChannels.API.value,
                  metadata: Optional[str] = None, directedness: float = 1.0):
    try:
        # the perceiving channel (senses passes "discord"; a bad value falls back to API). metadata is
        # the channel's reply coordinates (a JSON string, e.g. {"channel_id","message_id"}) that ride
        # the memory item so a directed answer can thread back; directedness is the fuzzy addressing
        # carrier (see MEMItem). talker is a channel-scoped uid ("renzo@discord:12345"), talker_name
        # the human display name.
        try:
            channel_enum = MEMChannels(channel)
        except ValueError:
            channel_enum = MEMChannels.API

        # get talker entity from memory, or create it if not exists
        talkerEntity = get_stakeholder(talker, channel=channel_enum, display_name=talker_name)

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
                senses=zip_senses(flatResult[1]),
                raw=rawResult,
                sourceId=str(talkerEntity.id),
                targetId=str(app.state.tokeniko.id),
                channel=channel_enum,
                metadata=metadata,
                directedness=directedness,
            )
            memory_doc.insert()

            # home any entity-linked named individuals in the stakeholders collection (storing path
            # only — NOT /evaluate). contextKey = the scope after "@" in the parser-minted uid.
            for individual in _collect_individuals(recursiveResult):
                context_key = individual.uid.split("@", 1)[1] if "@" in individual.uid else None
                upsert_individual(
                    name=individual.name,
                    uid=individual.uid,
                    ner_type=individual.ner,
                    vector=individual.vector,
                    context_key=context_key,
                    channel=talkerEntity.channel,
                )

    except Exception as error:
        res = repr(error)
        status = "failed"
    return {"status": status, "data": res}

@app.get("/api/v1/output")
async def out(tokens: str):
    res = await decompiler_decompile(tokens)
    return res
