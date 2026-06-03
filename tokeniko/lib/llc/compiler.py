# ------------------------------------------------------------------------------------------------
# FLAT compiler: transform TKStatements into a flat list of TKLLCItem (with TKEntity as predicate) 
# and TKEntity as entities (subjects, direct and indirect objects)
#

# manage spacetime (temporal and spatial modifiers) line 85
# ------------------------------------------------------------------------------------------------
import copy

import spacy
from lib.core.tk import LLCItemPayload, TKClauseType, TKEntity, TKEntityReference, TKMarker, TKOperator, TKStatement, TKStatements
from lib.core.tkllc import TKLLC, TKLLCContent, TKLLCItem, TKLLEntity, TKLLEntityProperty, TKLLEntityReference, TKLLProperties, TKLLSpacetime, TKLLSpacetimeMap, TKLLUniqueEntity
from lib.llc.constants import _PRONOUNS_BASE_ANCHORS, _SPACY_MODEL, _SUBORDINATE_TYPE_BASE_ANCHORS, _SUBORDINATE_TYPE_SIMILARITY_THRESHOLD, _LISTENER_ID, _TALKER_ID