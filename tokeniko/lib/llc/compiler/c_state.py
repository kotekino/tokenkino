# ------------------------------------------------------------------------------------------------
# SHARED COMPILER STATE
# the flat entity map and the spaCy model, shared across the c_* modules of a single compile.
# ------------------------------------------------------------------------------------------------
import spacy

from lib.core.tkllc import TKLLEntityMap
from lib.llc.constants import _SPACY_MODEL

# the flat entity map, populated by c_entities during a compile and read by statements/spacetime/
# zip/main. reset MUST mutate in place (clear), never reassign, so `from .c_state import _entities`
# stays bound to the same object in every module.
_entities: list[TKLLEntityMap] = []

# spaCy model (loaded once at import), used by c_statements (parseMarker) and c_zip (base marker)
nlp = spacy.load(_SPACY_MODEL)

# reset the shared entity map at the start of a compile (in place, see note above)
def reset_entities() -> None:
    _entities.clear()
