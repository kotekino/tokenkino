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

    # tkzip
    zipmap = map.tbounds + map.xbounds + map.ybounds + map.zbounds
    tkzip: TKZip = TKZip(map=zipmap, items=TKZipItem(op=TKOperator.AND, content=compiler_zip(tkllc.items)))

    return tkllc, tkzip
