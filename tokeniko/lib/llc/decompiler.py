import asyncio
from collections import Counter
import json
from lib.core.tk import TKOperator
from lib.core.tkllc import TKLLC, TKLLCContent, TKLLEntity, TKLLEntityReference, TKLLUniqueEntity, LLCItemPayload
from ollama import AsyncClient as OllamaClient
from lib.llc.constants import _ERRORS_UNABLE_TO_PROCESS, _OLLAMA_MODEL1, _OLLAMA_MODEL2

# global state
_init: bool = False
_ollamaClient: OllamaClient = None
_required_models = [_OLLAMA_MODEL1, _OLLAMA_MODEL2]

# grammatical framework to build the output
# https://www.grammaticalframework.org/doc/tutorial/gf-tutorial.html#toc17

# initializer
async def decompiler_init(ollamaClient: OllamaClient = None):
    global _init, _ollamaClient
    
    if not ollamaClient: 
        _init = False
        return
    
    # assign the client
    _ollamaClient = ollamaClient

    # download models, if necessary
    local_models = await _ollamaClient.list()
    available_names = [m['model'] for m in local_models['models']]

    for model in _required_models:
        if model not in available_names:
            await _ollamaClient.pull(model)

    # if all good
    _init = True
    return

# decode entity from unique entities
def decompiler_decodeRealEntity(entity: TKLLEntity, uniqueEntities: list[TKLLUniqueEntity]) -> str:
    if entity.entity_type == "pronoun":
        uniqueEntity: TKLLUniqueEntity = next((ue for ue in uniqueEntities if entity.id in ue.references), None)
        return uniqueEntity.token if uniqueEntity else entity.token
    else: 
        return entity.token

# process single entity with properties and marker
def decompiler_raw_entity(ref: TKLLEntityReference, entities: list[TKLLEntity], uniqueEntities: list[TKLLUniqueEntity]) -> str:

    entity: str = next((decompiler_decodeRealEntity(e, uniqueEntities) for e in entities if e.id == ref.id), "")
    
    # property pre poned (not marker, first)
    firstProp = next((p for p in ref.properties if not p.reference.marker), None)
    preProperty: str = decompiler_raw_entity(firstProp.reference, entities, uniqueEntities) if firstProp else ''
    
    # properties postponed
    i: int = 0
    postProperties: str = ""
    for pp in (p for p in ref.properties if p.reference.id != firstProp.reference.id):
        op = pp.op.value if pp.op and (i > 0 or pp.op != TKOperator.AND) else ""
        postProperties += op + " " + decompiler_raw_entity(pp.reference, entities, uniqueEntities)
        i += 1

    # marker only for complements
    marker = ''
    if ref.marker: marker: str = ref.marker.lemma if not ref.marker.connect_clause else ""
    
    # entity op
    opString: str = ref.op.value if ref.op and ref.op != TKOperator.AND else ""

    # entity aux
    auxString: str = ref.aux.lemma if ref.aux else ""

    result = f"{opString} {marker} {auxString.strip()} {preProperty.strip()} {entity.strip()} {postProperties.strip()}"

    return result

# recurse content to output raw sentences
def decompiler_raw_recursive(content: LLCItemPayload, entities: list[TKLLEntity], uniqueEntities: list[TKLLUniqueEntity]) -> str:
    
    result: str = ""
    if isinstance(content, TKLLCContent):
        subject = decompiler_raw_entity(content.subject, entities, uniqueEntities) if content.subject else ''
        predicate = decompiler_raw_entity(content.predicate, entities, uniqueEntities) if content.predicate else ''
        direct = decompiler_raw_entity(content.direct, entities, uniqueEntities) if content.direct else ''
        indirects = ' '.join([decompiler_raw_entity(i, entities, uniqueEntities) for i in content.indirects]) if content.indirects else ''
        result = f"{subject} {predicate} {direct} {indirects}"
    elif isinstance(content, list):
        i: int = 0
        for item in content:
            op = item.op.value if i > 0 or item.op.value != TKOperator.AND else ''
            result += f" {op} ({decompiler_raw_recursive(item.content, entities, uniqueEntities)})"
            i += 1

    return result.strip()

# get raw output from TKLLC
def decompiler_raw(tkLLC: TKLLC) -> str:

    result: str = ""
    i: int = 0
    for item in tkLLC.items:
        op = item.op if i > 0 or item.op != TKOperator.AND else ''
        result += op + ' (' + decompiler_raw_recursive(item.content, tkLLC.entities, tkLLC.uniqueEntities) + ') '
        i += 1

    # clean text
    result = " ".join(result.split())

    return result

# (DOING) build natural language output
async def decompiler_decompile(tokens: str) -> str:
    global _init, _ollamaClient

    # no ollama available
    if not _ollamaClient or not _init: 
        raise Exception(_ERRORS_UNABLE_TO_PROCESS)

    # Prompt strutturato a blocchi logici (senza negazioni complesse)
    systemPrompt = (
        f"You are a professional Logic-to-English syntactic decoder (System 2 Engine). "
        "Your goal is to transform a flattened logical sequence (TKLL) into a natural, fluent English sentence."
        "LOGICAL OPERATORS RULES:"
        "- 'AND': Translate as 'and'."
        "- 'OR': Translate as 'or'."
        "- 'IMPLY (A IMPLY B)': Translate as a conditional: 'If A, then B'."
        "- 'CONV (B CONV A)': Translate as a causal link: 'B because A' (or 'B since A')."
        "STRICT SYNTACTIC RULES:"
        "1. NO HALLUCINATIONS: Do not add adjectives, objects, or concepts not present in the TKLL."
        "2. COPULA INSERTION: Add 'to be' verbs for logical states (e.g., '[I] [happy]' -> 'I am happy')."
        "3. POSSESSIVE MAPPING: Convert 'of [PRONOUN]' to possessive adjectives (e.g., 'cat of I' -> 'my cat')."
        "4. VERB CONJUGATION: Conjugate verbs properly according to the subject."
        "5. FLOW: Ensure the final sentence is fluent but preserves the exact logical meaning."
        "OUTPUT FORMAT:"
        "Return ONLY a JSON object: {'translation': 'your sentence'}. No explanations."
        "Example Input: ((I happy) CONV (I play with (white AND gray) cat of I))"
        "Example Output: {'translation': 'I am happy because I play with my white and gray cat.'}"
    )

    # ask ollama to rephrase
    user_prompt = f"Input: '{tokens}'"

    # get the answer
    r1 = _ollamaClient.generate(
        model=_OLLAMA_MODEL1, 
        prompt=user_prompt, 
        system=systemPrompt,
        format='json',
        stream=False,
        options={
            'temperature': 0.0,
        }
    )
    r2 = _ollamaClient.generate(
        model=_OLLAMA_MODEL2, 
        prompt=user_prompt, 
        system=systemPrompt,
        format='json',
        stream=False,
        options={
            'temperature': 0.0
        }
    )

    o1_res, o2_res = await asyncio.gather(r1, r2)

    # normalized texts
    try:
        nt1 = json.loads(o1_res['response'])['translation']
    except Exception as e:
        nt1 = ''
    try:
        nt2 = json.loads(o2_res['response'])['translation']
    except Exception as e:
        nt2 = ''       
    
    # check semantic nt1 and nt2 with the original
    
    return {
        _OLLAMA_MODEL1: nt1, 
        _OLLAMA_MODEL2: nt2
    }