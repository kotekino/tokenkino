from typing import Annotated, Literal # <--- Importante
from bunnet import Document, Indexed
from lib.core.entities import MEMAxiom, MEMItem, MEMStakeholder, MEMTheorem, TKBase, TKDictionary, TKName, TKPlace

_VECTOR_INDEX = "vector_index"

# --------------------------------------------------------------
# knowledge base documents
# --------------------------------------------------------------

# document for base words
class TKBaseDoc(TKBase, Document):
    # Diciamo: "Il tipo è str, ed è indicizzato come unico"
    word: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "base"

# document for the dictionary
class TKDictionaryDoc(TKDictionary, Document):
    word: Annotated[str, Indexed()]
    
    class Settings:
        name = "dictionary"

# document for proper names
class TKNameDoc(TKName, Document):
    name: Annotated[str, Indexed(unique=True)]

    class Settings:
        name = "names"

# document for places
class TKPlaceDoc(TKPlace, Document):
    name: Annotated[str, Indexed()]

    class Settings:
        name = "places"

# --------------------------------------------------------------
# tokeniko memory
# --------------------------------------------------------------

# axioms: the truths that tokeniko holds about the world, that it will use as basis for reasoning and deriving new knowledge
class TKAxiomDoc(MEMAxiom, Document):
    class Settings:
        name = "axioms"

# theorems: the truths that tokeniko has derived from the axioms, that it will use as basis for reasoning and deriving new knowledge
class TKTheoremDoc(MEMTheorem, Document):
    class Settings:
        name = "theorems"

# items of the conversations
class TKMemoryItemDoc(MEMItem, Document):
    class Settings:
        name = "memory_items"

# entities involved in the conversations
class TKMemoryStakeholdersDoc(MEMStakeholder, Document):
    uid: Annotated[str, Indexed(unique=True)]
    class Settings:
        name = "stakeholders"