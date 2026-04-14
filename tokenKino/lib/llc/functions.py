from pymongo import MongoClient
import spacy
from spacy.tokens import Doc
from lib.core.entities import TKEntity, TKStatement

# load core web
nlp = spacy.load("en_core_web_md")

def llc_core(doc: Doc) -> TKStatement: 

    # init statement
    statement = TKStatement()

    subject = statement.create_entity(type="person", name="Renzo")
    predicate = statement.create_entity(type="action")
    statement.subject = subject
    statement.predicate = predicate

    root = next(doc.sents).root

    return statement

def llc(tokens: str, mongoClient: MongoClient=None) -> TKStatement:

    # use spacy
    tkStatement: TKStatement = llc_core(nlp(tokens))

    doc = nlp(tokens)

    # debug
    for token in doc:
        print(
            token.text, 
            token.dep_, 
            spacy.explain(token.dep_), 
            token.pos_, 
            token.head.text, 
            token.head.pos_, 
            sep="|", 
            end="\n\n"
            )

    return tkStatement

str1 = "I and Mari lift the couch in the living room, because we are a team and we help each other"
llc(str1)
