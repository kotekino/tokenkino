# ------------------------------------------------------------------------------------------------
# FLAT compiler V2 — orchestrator
# compile a recursive TKStatements into the flat TKLLC and the numeric TKZip.
# ------------------------------------------------------------------------------------------------
from lib.core.tk import TKOperator, TKStatements
from lib.core.tkllc import TKLLC, TKLLCItem
from lib.core.tkzip import TKZip, TKZipItem

from .c_state import _entities, reset_entities
from .c_entities import compiler_resolveEntities
from .c_subordinates import compiler_resolveSubordinateSubjects
from .c_statements import compiler_resolveStatements
from .c_spacetime import compiler_spacetimeResolveTime, compiler_spacetimeResolveSpace, compiler_spacetimeNormalize, compiler_spacetimeResolveVelocity
from .c_untangle import compiler_untangleGenus, compiler_untangleSubject
from .c_zip import compiler_zip

def compiler_compile(tkStatements: TKStatements) -> tuple[TKLLC, TKZip]:
    # reset entities (in place, so the shared list stays bound across modules)
    reset_entities()

    # resolve relative / anaphoric / implicit subordinate subjects before flattening
    for tks in tkStatements:
        compiler_resolveSubordinateSubjects(tks)

    # tkllc
    compiler_resolveEntities(tkStatements)
    statements: list[TKLLCItem] = compiler_resolveStatements(tkStatements)
    compiler_spacetimeResolveTime(statements)
    compiler_spacetimeResolveSpace(statements)
    map = compiler_spacetimeNormalize(statements)
    compiler_spacetimeResolveVelocity(statements)
    tkllc = TKLLC(map=map, items=statements, entities=[e.entity for e in _entities])

    # graph-constrained GENUS untangle (the definitions-as-rules ingestion gate): re-resolve each
    # "X is a <genus>" genus to the sense consistent with the subject's taxonomy — kills homophony at
    # the source (organ-the-fish, state-the-country) using tokeniko's own is_a graph. Mutates entity
    # senses (+ their vectors) IN PLACE before the zip is built, so the zip carries the corrected sense.
    compiler_untangleGenus(tkllc.items)

    # graph-constrained SUBJECT untangle (step 5 — the runtime mirror; definitions get exact
    # gloss-pinning instead): after the genus pass, snap a still-inconsistent subject to the sense of
    # the same word that bedrock already places under the genus. Named individuals are never touched
    # (type-centroid sense). Conservative: no consistent candidate -> the new edge stands as claimed.
    compiler_untangleSubject(tkllc.items)

    # tkzip
    zipmap = map.tbounds + map.xbounds + map.ybounds + map.zbounds
    tkzip: TKZip = TKZip(map=zipmap, items=TKZipItem(op=TKOperator.AND, content=compiler_zip(tkllc.items)))

    return tkllc, tkzip
