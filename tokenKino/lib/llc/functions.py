from ollama import Client as ollamaClient
import spacy
from spacy.tokens import Token
import numpy as np
from lib.core.entities import EntityPayload, TKContext, TKDictionary, TKEntityReference, TKGeneric, TKName, TKOperator, TKPlace, TKStatement, TKStatements
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper

# define constants
_SIMILAR_RESULTS: int = 5

# load core web
nlp = spacy.load("en_core_web_md")

# (DONE, CHECK) get seamntic value from dictionary
def llc_getEntity(token: Token, tokens: list[Token], context: TKContext = None) -> EntityPayload:
    
    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)

    # try finding the meaning (in our dictionary)
    doc_result: TKDictionary = None

    # should be in the dictionary
    if pos:
        # search in dictionary
        doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": pos}).run()
                
        # semantic fallback
        if not doc_result:
            query_vector = np.asarray([token.vector])
            most_similar = nlp.vocab.vectors.most_similar(query_vector, n=_SIMILAR_RESULTS)
            similar_keys = most_similar[0][0]
            for key in similar_keys:
                fallback_lemma = nlp.vocab.strings[key]     
                doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": "v"}).run()
                if doc_result:
                    break

        # assign result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    else: 
        # not in the dictionary [avrns] -> (cconj, pron, propn, intj, num, particle, punctuation, sconj, sym, x)
        if token.pos_ == "PROPN":
            tkMeaning = TKName(name=token.lemma_)

    # if still no result, generic (it is used to manage unknown semantics)
    if not doc_result: tkMeaning = TKGeneric(token=token.lemma_, pos=pos, upos=token.pos_, context=context)

    # return result found
    return tkMeaning

# (ONGOING) parse primary and subordinate clauses
def llc_parseClause(root: Token, tokens: list[Token], context: TKContext = None, ollamaClient: ollamaClient = None) -> TKStatements: 
    
    # init statement
    statements = TKStatements()
    
    # ------------------------------
    # root predicate [verb, aux] (necessary: if missing then implied, rephrase)
    # ------------------------------

    # STOP llc_preparser: rearrange the sentence (elliptic, exclamation, colloquial) and override
    if (root.pos_ != "VERB" and root.pos_ != "AUX"): return llc_preparser(tokens, context, ollamaClient)
        
    # the root is a verb, assign
    tkPredicate = llc_getEntity(root, [t for t in tokens if t.head == root], context)

    # ------------------------------
    # search subject (necessary: if missing then implied, rephrase)
    # ------------------------------
    subjectToken = next((s for s in tokens if s.dep_ == "nsubj"), None)

    # STOP llc_preparser: rearrange the sentence (verb present but no subject)
    if not subjectToken: return llc_preparser(tokens, context, ollamaClient)

    # the subject is found, assign subject
    tkSubject = llc_getEntity(subjectToken, [t for t in tokens if t.head == subjectToken], context)

    # ------------------------------
    # search object (optional)
    # ------------------------------
    objectToken = next((s for s in tokens if s.dep_ == "dobj"), None)
    if objectToken: tkObject = llc_getEntity(objectToken, [t for t in tokens if t.head == objectToken], context)

    # put operator
    tkOp = TKOperator.AND # default

    # main statement
    tkMain = TKStatement()      
    tkMain.op = tkOp
    if tkPredicate: 
        tkMain.predicate = tkMain.create_entity(payload=tkPredicate)
        # add properties

    if subjectToken: 
        tkMain.subject = tkMain.create_entity(payload=tkSubject)
        # add properties

    if objectToken: 
        tkMain.object = tkMain.create_entity(payload=tkObject)
        # add properties

    # search for more (decouple logical operators multiplying the statements)
    # ...

    # build output
    statements.append(tkMain)

    return statements

# (DONE, CHECK) core internal recursive function to parse a list of token into a TKStatements
def llc_core(tokens: list[Token], context: TKContext = None, ollamaClient: ollamaClient = None) -> TKStatements: 

    # init statement
    statements = TKStatements()

    # search separate predicates
    roots = [s for s in tokens if s.dep_ == "ROOT"] # number of separate sentences
    
    # check for recursion
    if len(roots) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        # recursive iteration for each predicate 
        for p in roots:
            statements += llc_core(list(p.subtree), context, ollamaClient)

    elif len(roots) == 1:
        root = roots[0] # get the only root

        # split every root in chunk to manage suboordinates and auxiliary verbs
        clausesRoots: list[Token] = [root] # introduce the logic
        
        # cycle clauses
        for clauseRoot in clausesRoots:
            statements += llc_parseClause(clauseRoot, list(clauseRoot.subtree), context, ollamaClient)

    return statements

# (DONE, REFINE) pre parser based on Phi-3 via Ollama: fix the sentences not understandable by llc
def llc_preparser(tokens: str, context: TKContext = None, ollamaClient: ollamaClient = None) -> TKStatements | None:

    # no ollama available
    if not ollamaClient: return None

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
    response = ollamaClient.generate(
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
    return llc_core(normalized_text, context, ollamaClient)

# ------------------------------------------
# (DONE, CHECK) MAIN entry point to parse an input text
# ------------------------------------------
def llc(tokens: str, context: TKContext = None, ollamaClient: ollamaClient = None) -> TKStatements:

    # spacy parse
    doc = nlp(tokens)

    # get all tokens
    tkStatements: TKStatements = llc_core(list(doc), context, ollamaClient)

    # return statement
    return tkStatements