from pymongo import MongoClient
import spacy
from spacy.tokens import Token
from lib.core.entities import TKDictionary, TKGeneric, TKName, TKOperator, TKStatement, TKStatements
from lib.core.io import init_io
import numpy as np

# load core web
nlp = spacy.load("en_core_web_md")

def llc_core(tokens: list[Token], mongoClient: MongoClient) -> TKStatements: 

    db = mongoClient[1]
    dictionary = db["dictionary"]

    # init statement
    statements = TKStatements()

    # search separate predicates
    predicates = [s for s in tokens if s.dep_ == "ROOT"] # number of separate sentences

    # check for recursion
    if len(predicates) > 1:
        # recurse condition with > 1 sentences (multiple roots)
        print("multiple roots")

        # recursive iteration for each predicate 
        for p in predicates:
            statements += llc_core(list(p.subtree), mongoClient)

    elif len(predicates) == 1:
        # recurse condition with 1 sentence (1 root)
        print("one root")

        predicate = predicates[0]

        # search predicate (as verb)
        if (predicate.pos_ == "VERB" or predicate.pos_ == "AUX"):
            doc_result = dictionary.find_one({"word": predicate.lemma_, "pos": "v"})
            
            # semantic fallback
            if not doc_result:
                query_vector = np.asarray([predicate.vector])
                most_similar = nlp.vocab.vectors.most_similar(query_vector, n=5)
                similar_keys = most_similar[0][0]
                for key in similar_keys:
                    fallback_lemma = nlp.vocab.strings[key]     
                    doc_result = dictionary.find_one({"word": fallback_lemma, "pos": "v"})
                    if doc_result:
                        break

            # if still no result, generic, otherwise build dictionary
            if doc_result: tkPredicate = TKDictionary(**doc_result)      
            else: tkPredicate = TKGeneric(token=predicate.lemma_, pos=predicates[0].pos_, definition="")
        else:
            # not a verb: predicato nominale, frase elittica, esclamazione
            tkPredicate = TKGeneric(token=predicate.lemma_, pos=predicates[0].pos_, definition="")

        # search subject
        subjectToken = next((s for s in tokens if s.dep_ == "nsubj"), None)
        tkSubject = TKName(name=subjectToken.text)

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
        tkMain.subject = tkMain.create_entity(payload=tkSubject)
        tkMain.predicate = tkMain.create_entity(payload=tkPredicate)
        if objectToken: tkMain.object = tkMain.create_entity(payload=tkObject)
 
        # search for more (decouple logical operators multiplying the statements)
        # ...

        # build output
        statements.append(tkMain)

    else:
        # exit condition (no sentences)
        print("0 root")

    return statements

def llc(tokens: str, mongoClient: MongoClient=None) -> TKStatements:

    # spacy parse
    doc = nlp(tokens)

    # get all tokens
    tkStatements: TKStatements = llc_core(list(doc), mongoClient)

    # return statement
    return tkStatements


# simulation of external call, remove this
uri = "mongodb://localhost:49326/?directConnection=true"
db_name = "semantic_engine"
client = init_io(connection_string=uri, db_name=db_name)

str1 = "I and Mari lift the couch in the living room, because we are a team and we help each other"
str1 = "Renzo is intelligent. Io am Renzo."
llc(str1, client)