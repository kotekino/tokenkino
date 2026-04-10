import spacy

# can get the language


# English pipelines include a rule-based lemmatizer
nlp = spacy.load("en_core_web_md")
lemmatizer = nlp.get_pipe("lemmatizer")
doc = nlp("While I was reading the paper, I found a great idea.")

for token in doc:
    print(f"{token.text} -> {token.lemma_}")