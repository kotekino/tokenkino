from ollama import Client as ollamaClient
from pymongo import MongoClient
import spacy
from spacy.tokens import Token
import numpy as np
from lib.core.entities import TKContext, TKDictionary, TKGeneric, TKName, TKOperator, TKStatement, TKStatements
from lib.core.io import init_io
from lib.core.models import TKDictionaryDoc
from lib.core.mappers import TKPosMapper

# define constants
SIMILAR_RESULTS: int = 5

# load core web
nlp = spacy.load("en_core_web_md")

# get seamntic value from dictionary
def llc_meaning(token: Token, context: TKContext = None) -> TKDictionary:
    
    # get wn pos
    pos = TKPosMapper.get_wn_pos(token.pos_)
    doc_result: TKDictionary = None
    if pos:
        # search in dictionary
        doc_result = TKDictionaryDoc.find_one({"word": token.lemma_, "pos": pos}).run()
                
        # semantic fallback
        if not doc_result:
            query_vector = np.asarray([token.vector])
            most_similar = nlp.vocab.vectors.most_similar(query_vector, n=SIMILAR_RESULTS)
            similar_keys = most_similar[0][0]
            for key in similar_keys:
                fallback_lemma = nlp.vocab.strings[key]     
                doc_result = TKDictionaryDoc.find_one({"word": fallback_lemma, "pos": "v"}).run()
                if doc_result:
                    break

        # fallback result
        if doc_result: tkMeaning = TKDictionary(**doc_result.model_dump(exclude={"id"}))
    
    # if still no result, generic (it is used to manage unknown semantics)
    if not doc_result: tkMeaning = TKGeneric(token=token.lemma_, pos=pos, upos=token.pos_, context=context)

    # return result found
    return tkMeaning

# core internal recursive function to parse a list of token into a TKStatements
def llc_core(tokens: list[Token], context: TKContext = None) -> TKStatements: 

    # init statement
    statements = TKStatements()

    # search separate predicates
    roots = [s for s in tokens if s.dep_ == "ROOT"] # number of separate sentences

    # check for recursion
    if len(roots) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        print("multiple roots")

        # recursive iteration for each predicate 
        for p in roots:
            statements += llc_core(list(p.subtree), context)

    elif len(roots) == 1:
        # recurse condition with 1 sentence (1 root)
        print("one root")

        root = roots[0]

        # search predicate (as verb)
        if (root.pos_ == "VERB" or root.pos_ == "AUX"):
            tkPredicate = llc_meaning(root, context)
        else:
            # todo
            
            # not a verb: predicato nominale, frase elittica, esclamazione
            tkPredicate = llc_meaning(root, context)

        # search subject
        subjectToken = next((s for s in tokens if s.dep_ == "nsubj"), None)
        if subjectToken: tkSubject = TKName(name=subjectToken.text)

        # search object
        objectToken = next((s for s in tokens if s.dep_ == "dobj"), None)
        if objectToken: tkObject = TKName(name=objectToken.text)

        # complete other fields
        # ...

        # put operator
        tkOp = TKOperator.AND # default

        # main statement
        tkMain = TKStatement()      
        tkMain.op = tkOp
        if tkPredicate: tkMain.predicate = tkMain.create_entity(payload=tkPredicate)
        if subjectToken: tkMain.subject = tkMain.create_entity(payload=tkSubject)
        if objectToken: tkMain.object = tkMain.create_entity(payload=tkObject)
 
        # search for more (decouple logical operators multiplying the statements)
        # ...

        # build output
        statements.append(tkMain)

    else:
        # exit condition (no sentences)
        print("0 root")

    return statements

# main entry point to parse an input text
def llc(tokens: str, ollamaClient: ollamaClient, context: TKContext = None) -> TKStatements:

    # spacy parse
    doc = nlp(tokens)

    # get all tokens
    tkStatements: TKStatements = llc_core(list(doc), context)

    # return statement
    return tkStatements

# pre parser based on Phi-3 via Ollama: fix the sentences not understandable by llc
def llc_preparser(tokens: str, context: TKContext, ollamaClient: ollamaClient) -> str:

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

    user_prompt = f"Input: '{tokens}'\nOutput:"

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

    normalized_text = response['response'].strip().strip("'").strip('"')

    return normalized_text