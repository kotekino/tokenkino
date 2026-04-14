import spacy
from spacy import displacy

from tokenKino.lib.core.entities import TKStatement

# example
s1_it = "Siccome il cane bianco e nero che sono andato a prendere ieri si è rivelato essere un cane molto simpatico e intelligente, e mia moglie mari lo ha adorato dal primo momento che lo ha visto, pensiamo che adottarlo sia la prossima mossa"
s1_en = "Since the black-and-white dog I went to pick up yesterday turned out to be a very friendly and intelligent dog, and my wife Mari loved him from the moment she saw him, we think adopting him is the next step"
s2_en = "I and Mari lift the couch in the living room, because we are a team and we help each other"

# English pipelines include a rule-based lemmatizer
nlp = spacy.load("en_core_web_md")
doc = nlp(s2_en)

# init statement
statement: TKStatement = TKStatement()

# cycle over tokens and print their text, dependency label, head text, head POS tag, and children
for token in doc:
    print(token.text, token.dep_, token.pos_, token.head.text, token.head.pos_)
    #print(token.text, token.dep_, token.head.text, token.head.pos_,
    #        [child for child in token.children])

