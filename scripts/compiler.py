import spacy
from spacy import displacy

# example
s1_it = "Siccome il cane bianco e nero che sono andato a prendere ieri si è rivelato essere un cane molto simpatico e intelligente, e mia moglie mari lo ha adorato dal primo momento che lo ha visto, pensiamo che adottarlo sia la prossima mossa"
s1_en = "Since the black-and-white dog I went to pick up yesterday turned out to be a very friendly and intelligent dog, and my wife Mari loved him from the moment she saw him, we think adopting him is the next step"

# English pipelines include a rule-based lemmatizer
nlp = spacy.load("en_core_web_md")
lemmatizer = nlp.get_pipe("lemmatizer")
doc = nlp(s1_en)

for token in doc:
    print(token.text, token.lemma_, token.pos_, token.tag_, token.dep_,
            token.shape_, token.is_alpha, token.is_stop)


# displacy.serve(doc, style='ent', port=3000)
# displacy.serve(doc, style='dep', port=3001)
# displacy.serve(doc, style='parse', port=3002)