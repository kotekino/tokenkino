from typing import Any

from ollama import Client as OllamaClient
import spacy
from spacy import displacy
from spacy.tokens import Token
import stanza
import spacy_stanza
import numpy as np
from lib.core.entities import TKComplement, TKFlatStatements, TKFullEntity, TKContext, TKDictionary, TKGeneric, TKName, TKOperator, TKStatement, TKStatements
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper

# define constants
_SIMILAR_RESULTS: int = 5
_UNABLE_TO_PROCESS: str = "Unable to process the sentence"
_SPACY_MODEL = "en_core_web_lg" # alternatives: en_core_web_md (fast), en_core_web_lg (ok), en_core_web_trf (best)

# stanza
stanza.download("en", package="lines")

# --- INIZIO PATCH PYTORCH ---
import torch
_original_torch_load = torch.load
def _patched_torch_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_torch_load(*args, **kwargs)
torch.load = _patched_torch_load
# --- FINE PATCH PYTORCH ---

# load spacy model
nlp_stanza = spacy_stanza.load_pipeline("en", package="lines")
nlp = spacy.load(_SPACY_MODEL)

# global variables
_context: TKContext = None
_ollamaClient: OllamaClient = None

# (ONGOING) get properties
def llc_getProperties(tokens: list[Token]) -> list[TKFullEntity]:
    doc_properties: list[TKFullEntity] = []
    property: TKFullEntity = None

    for t in tokens:
        fullEntity = None
        if t.dep_ == "advmod" or t.dep_ == "nummod" or t.dep_ == "amod" or t.dep_ == "nmod" or t.dep_ == "nmod:poss" or t.dep_ == "det":
            property = llc_getFullEntity(t) 
        elif t.dep_ == "conj":
            property = llc_getFullEntity(t)
        elif t.dep_ == "cc":
            property = llc_getFullEntity(t)
        
        if property: doc_properties.append(property)

    return doc_properties

# (ONGOING) get seamntic value from dictionary + properties
def llc_getFullEntity(token: Token) -> TKFullEntity:
    
    # related tokens to the entity
    tokens = list(token.subtree)

    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_result: TKDictionary = None
    doc_properties: list[TKFullEntity] = []
    tkComplement = None

    # should be in the dictionary
    if len(pos) > 0:
        for p in pos:
            # search in dictionary
            doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": p}).run()
            if doc_result: break
                
        # semantic fallback
        for p in pos:
            if not doc_result:
                newDoc = nlp.tokenizer(token.lemma_)
                if newDoc and len(list(newDoc)) > 0:
                    query_vector = np.asarray([newDoc[0].vector])
                    most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SIMILAR_RESULTS)
                    similar_keys = most_similar[0][0]
                    for key in similar_keys:
                        fallback_lemma = nlp.vocab.strings[key].lower()
                        doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": p}).run()
                        if doc_result:
                            break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else: 
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            tkMeaning = TKName(name=token.lemma_)

    # if still no result, generic (it is used to manage unknown semantics)
    knownPos = pos[0] if len(pos) > 0 else ""
    if not doc_result: tkMeaning = TKGeneric(token=token.lemma_, pos=knownPos, upos=token.pos_)

    # get properties (for each token directly bound to the result)
    doc_properties = llc_getProperties([s for s in tokens if s.head == token])

    # get complement
    complement = next((s for s in token.children if s.dep_ == "case" or s.dep_ == "mark"), None)
    if complement and complement.has_vector: tkComplement = TKComplement(type=complement.dep_, lemma=complement.lemma_, vector=complement.vector)    

    # return result found
    return TKFullEntity(entity=tkMeaning, complement=tkComplement, properties=doc_properties)

# (ONGOING) get all indirect complements (cycling remaining tokens)
def llc_getIndirects(tokens: list[Token]) -> list[TKFullEntity]: 
    
    indirectTokens: list[TKFullEntity] = []

    for t in tokens:
        # reset indirect
        indirectToken: Token = None
        indirectEntity: TKFullEntity = None

        # case dative (can be a name [take the entity] or a prep [take the first child])
        if t.dep_ == "obl":
            indirectToken = t
            indirectEntity = llc_getFullEntity(indirectToken)
        elif t.dep_ == "iobj":
            indirectToken = t
            indirectEntity = llc_getFullEntity(indirectToken)     
        elif t.dep_ == "csubj" or t.dep_ == "xcomp":
            indirectToken = t
            statement = llc_parseSentence(indirectToken, list(indirectToken.subtree))
            if statement:
                indirectEntity = TKFullEntity(entity=statement, complement=None, properties=[])

        # if found 
        if indirectToken: 
            indirectTokens.append(indirectEntity)

    return indirectTokens

# (ONGOING) parse sentence (simple or compoung)
def llc_parseSentence(root: Token, tokens: list[Token]) -> TKStatement: 
    
    # ------------------------------
    # root is predicate
    # ------------------------------

    # the root is a verb or an adjective, assign (auxiliaries are properties)
    tkPredicate = llc_getFullEntity(root)
    if tkPredicate: tokens.remove(root)

    # ------------------------------
    # search subject
    # ------------------------------
    subjectToken = next((s for s in tokens if s.dep_ == "nsubj" and s.head == root), None)
    if subjectToken:
        tkSubject = llc_getFullEntity(subjectToken)
        if tkSubject: tokens.remove(subjectToken)

    # ------------------------------
    # search direct
    # ------------------------------
    directToken = next((s for s in tokens if s.dep_ == "obj" and s.head == root), None)
    if directToken: 
        tkDirect = llc_getFullEntity(directToken)
        if tkDirect: tokens.remove(directToken)

    # ------------------------------
    # search indirect
    # ------------------------------
    indirectTokens = llc_getIndirects(tokens)

    # main statement
    tkMain = TKStatement()      
    if tkPredicate: 
        predicateId = tkMain.create_predicate(payload=tkPredicate.entity, complement=tkPredicate.complement)
        # add properties
        if len(tkPredicate.properties) > 0: tkMain.add_properties(tkPredicate.properties, predicateId)

    if subjectToken: 
        subjectId = tkMain.create_subject(payload=tkSubject.entity, complement=tkSubject.complement)
        # add properties
        if len(tkSubject.properties) > 0: tkMain.add_properties(tkSubject.properties, subjectId)

    if directToken: 
        directId = tkMain.create_direct(payload=tkDirect.entity, complement=tkDirect.complement)
        # add properties
        if len(tkDirect.properties) > 0: tkMain.add_properties(tkDirect.properties, directId)

    for it in indirectTokens:
        indirectId = tkMain.create_indirect(payload=it.entity, complement=it.complement)
        # add properties
        if len(it.properties) > 0: tkMain.add_properties(it.properties, indirectId)

    #return statement
    return tkMain

# (DONE, REFINE) core internal recursive function to parse a list of token into a TKStatements
def llc_core(tokens: list[Token]) -> TKStatements: 

    # init statement
    statements = TKStatements()

    # search separate predicates
    roots = [s for s in tokens if s.dep_ == "root"] # number of separate sentences
    
    # check for recursion
    if len(roots) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        # recursive iteration for each predicate 
        for p in roots:
            statements += llc_core(list(p.subtree))

    elif len(roots) == 1:
        statements.append(llc_parseSentence(roots[0], list(roots[0].subtree)))

    return statements

# (DONE, REFINE) pre parser based on Phi-3 via Ollama: fix the sentences not understandable by llc
def llc_preparser(tokens: str) -> TKStatements | None:

    # no ollama available
    if not _ollamaClient: raise Exception(_UNABLE_TO_PROCESS)

    # Prompt strutturato a blocchi logici (senza negazioni complesse)
    systemPrompt = """You are a strict syntax normalizer.
    Your ONLY job is to rewrite elliptical phrases, exclamations, greetings, or short answers into explicit Subject-Verb-Object (SVO) sentences.

    Rules:
    - Keep the exact original meaning.
    - Maintain the original grammatical person. Assume 1st person singular ('I') for general exclamations or greetings unless stated otherwise.
    - Output ONLY the final sentence. Absolutely no explanations, no notes, and do not write "You are expressing...".

    Examples:
    Input: 'Silence!'
    Output: 'You must stay silent.'

    Input: 'Exactly.'
    Output: 'That is exactly right.'

    Input: 'mornin guys'
    Output: 'I wish you a good morning.'

    Input: 'oh god'
    Output: 'I am shocked.'

    Input: 'What a cold day!'
    Output: 'This day is cold.'
    """

    # ask ollama to rephrase
    user_prompt = f"Input: '{tokens}'\nOutput:"

    # get the answer
    response = _ollamaClient.generate(
        model='phi3', 
        prompt=user_prompt, 
        system=systemPrompt,
        options={
            'temperature': 0.0,
            'top_k': 10,
            'top_p': 0.5
        }
    )

    # normalized text
    normalized_text = response['response'].strip().strip("'").strip('"')

    # check semantic value via spacy
    # CRITICAL HERE: remove any noise with 100% confidence
    
    unable: bool = False
    if unable: return None

    # parse the rearranged sentence and return the TKStatements result 
    return llc_core(normalized_text)

# (ONGOING)
def llc_flat(tkStatements: TKStatements) -> TKFlatStatements | None:
    
    result: TKFlatStatements = []
    #for s in tkStatements:
        #tkFlat = TKFlatStatement(
        #    op=s.op,
        #    ...
        #)
        #result.append(tkFlat)

    return result

# --------------------------------------------------------------
# (DONE, REFINE) MAIN entry point to parse an input text
# --------------------------------------------------------------
def llc(tokens: str, context: TKContext = None, ollamaClient: OllamaClient = None) -> tuple[TKFlatStatements, TKStatements]:

    # assign variables
    _context = context
    _ollamaClient = ollamaClient

    # spacy parse
    doc = nlp_stanza(tokens)

    # get all tokens
    tkStatements: TKStatements = llc_core(list(doc))

    # flat statements
    tkFlatStatements: TKFlatStatements = llc_flat(tkStatements)

    # return statement
    return [tkFlatStatements, tkStatements]

# (DONE) wrap the displacy dep diagram
def llc_diagram(tokens: str) -> str:
    
    # spacy parse
    doc = nlp_stanza(tokens)
    diagram = displacy.render(doc, style = "dep")

    html = '<html><body>' + diagram + '</body></html>'

    return html

# reference: https://universaldependencies.org/u/dep/acl.html

# acl: clausal modifier of noun (adnominal clause)
# https://universaldependencies.org/u/dep/acl.html#acl-clausal-modifier-of-noun-adnominal-clause
# ->

# acl:relcl: relative clause modifier
# https://universaldependencies.org/u/dep/acl-relcl.html
# -> double the sentence object for both sentences

# advcl: adverbial clause modifier
# https://universaldependencies.org/u/dep/advcl.html#advcl-adverbial-clause-modifier
# ->

# advcl:relcl: adverbial relative clause modifier
# https://universaldependencies.org/u/dep/advcl-relcl.html
# ->