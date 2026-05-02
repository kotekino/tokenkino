# (DONE) pre parser based on Phi-3 via Ollama: fix the sentences not understandable by llc
import json
from lingua import LanguageDetectorBuilder
import spacy
from symspellpy import SymSpell
import pkg_resources
from lib.core.entities import TKStatements
from lib.llc.constants import _ERRORS_UNABLE_TO_PROCESS, _MIN_SIMILARITY, _OLLAMA_MODEL1, _OLLAMA_MODEL2, _OLLAMA_TRANS1, _OLLAMA_TRANS2, _PRE_SIMILARITY_THRESHOLD, _SPACY_MODEL
from lib.llc.parser import llc_core
from ollama import AsyncClient as OllamaClient
import asyncio
from collections import Counter
from lib.llc.translator import TKTranslator

# global state
_init: bool = False
_ollamaClient: OllamaClient = None
_required_models = [_OLLAMA_MODEL1, _OLLAMA_MODEL2, _OLLAMA_TRANS1, _OLLAMA_TRANS2]

# sym spell
sym_spell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)
dictionary_path = pkg_resources.resource_filename(
    "symspellpy", "frequency_dictionary_en_82_765.txt"
)
sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)

# lingua
_detector = LanguageDetectorBuilder.from_all_languages().build()
_translator: TKTranslator = TKTranslator()
_nlp = spacy.load(_SPACY_MODEL)

# initializer
async def llc_pre_init(ollamaClient: OllamaClient = None):
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

# polish a sentence from the typos
async def llc_pre_typos(tokens: str) -> str:
    global _init, _ollamaClient

    # no ollama available
    if not _ollamaClient or not _init: 
        raise Exception(_ERRORS_UNABLE_TO_PROCESS)

    # Prompt strutturato a blocchi logici (senza negazioni complesse)
    systemPrompt = "You're an autocorrect. You ONLY return a JSON object with the key 'corrected_text'.If not able to correct, the key 'corrected_text' must be the original input.No comments."

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
        nt1 = json.loads(o1_res['response'].lower())['corrected_text']
    except Exception as e:
        nt1 = ''
    try:
        nt2 = json.loads(o2_res['response'].lower())['corrected_text']
    except Exception as e:
        nt2 = ''       
    
    suggestions = sym_spell.lookup_compound(tokens, max_edit_distance=2)
    nt3 = suggestions[0].term

    results = [nt1, nt2, nt3]
    counter = Counter(results)
    common, occurrences = counter.most_common(1)[0]

    if occurrences >= 2:
        fixed = common
    else:
        fixed = nt3
    
    return fixed

# translate in english
async def llc_pre_translate(tokens: str) -> str:
    global _init, _ollamaClient, _nlp

    # Controllo stato iniziale
    if not _ollamaClient or not _init: 
        raise Exception(_ERRORS_UNABLE_TO_PROCESS)

    # Prompt di sistema draconiano con inserimento dinamico della lingua target
    systemPrompt = (
        f"You are a professional translator. Translate the input text strictly into english. "
        "You ONLY return a JSON object with the key 'translation'. "
        "If you are not able to translate, the key 'translation' must be the original input. "
        "Do not add notes, markdown, or comments."
    )

    user_prompt = f"Input: '{tokens}'"

    # Preparo i due task concorrenti
    r1 = _ollamaClient.generate(
        model=_OLLAMA_TRANS1, # aya
        prompt=user_prompt, 
        system=systemPrompt,
        format='json',
        stream=False,
        options={
            'temperature': 0.1, # Leggermente > 0 per permettere traduzioni più naturali, ma molto basso
        }
    )
    r2 = _ollamaClient.generate(
        model=_OLLAMA_TRANS2, # gemma
        prompt=user_prompt, 
        system=systemPrompt,
        format='json',
        stream=False,
        options={
            'temperature': 0.1
        }
    )

    # Eseguo i task in parallelo
    o1_res, o2_res = await asyncio.gather(r1, r2)

    # Estrazione sicura dai JSON
    t1 = ""
    try:
        # Usa .strip() per pulire la stringa, non .lower() per mantenere le maiuscole corrette!
        t1 = json.loads(o1_res['response'])['translation'].strip()
    except Exception as e:
        print(f"Modello 1 ha fallito: {e}")

    t2 = ""
    try:
        t2 = json.loads(o2_res['response'])['translation'].strip()
    except Exception as e:
        print(f"Modello 2 ha fallito: {e}")

    # LOGICA DI RISOLUZIONE (Gerarchica invece che per Consenso)
    t3 = _translator.translate(tokens)

    # check vector
    t1doc = _nlp(t1) if t1 else None
    t2doc = _nlp(t2) if t2 else None
    t3doc = _nlp(t3) if t3 else None
    s1 = t1doc.similarity(t2doc) if t1doc and t2doc else -1.0
    s2 = t1doc.similarity(t3doc) if t1doc and t3doc else -1.0
    s3 = t2doc.similarity(t3doc) if t2doc and t3doc else -1.0
    best = max(s1, s2, s3)

    if best < _MIN_SIMILARITY:
        return tokens

    # 1. Se il Modello Principale (Llama 3) ha restituito qualcosa di sensato, vince sempre lui.
    if best == s1:
        return t1
    elif best == s2 or best == s3:
        return t3
    else:
        return tokens # fallback, input

# get language
async def llc_pre_getLanguage(tokens: str) -> str:
    if not tokens or not tokens.strip():
        return "en"
    try:
        language = _detector.detect_language_of(tokens)
        if language is None:
            return "en"
        return language.iso_code_639_1.name.lower()     
    except Exception as e:
        return "en"

# prepare text
async def llc_pre_prepare(tokens: str) -> str:
    global _nlp

    # translate if not en
    language = await llc_pre_getLanguage(tokens)
    if language != "en":
        tokens = await llc_pre_translate(tokens)

    # remove typos
    result = await llc_pre_typos(tokens)

    # check vector
    inputDoc = _nlp(tokens)
    outputDoc = _nlp(result)

    # compare vectors
    similarity = inputDoc.similarity(outputDoc)
    
    if similarity > _PRE_SIMILARITY_THRESHOLD:
        return result
    else:
        return tokens