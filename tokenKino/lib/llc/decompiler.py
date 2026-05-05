# (DOING) parse content object (recursively)
from lib.core.entities import TKLLC, LLCItemPayload, TKLLCContent, TKLLEntity, TKLLEntityReference, TKOperator

# process single entity with properties and marker
def llc_raw_entity(ref: TKLLEntityReference, entities: list[TKLLEntity]) -> str:

    entity: str = next((e.tokens for e in entities if e.id == ref.id), "")
    
    preProperties: str = ""
    i: int = 0
    for pp in (p for p in ref.properties if not p.reference.marker):
        op = pp.op if i > 0 or pp.op != TKOperator.AND else ''
        preProperties += op + " " + llc_raw_entity(pp.reference, entities)
        i += 1
    
    i: int = 0
    postProperties: str = ""
    for pp in (p for p in ref.properties if p.reference.marker):
        op = pp.op if i > 0 or pp.op != TKOperator.AND else ''
        postProperties += op + " " + pp.reference.marker.lemma + " " + llc_raw_entity(pp.reference, entities)
        i += 1

    result = f"{preProperties.strip()} {entity.strip()} {postProperties.strip()}"

    return result

# (DOING) recurse content to output raw sentences
def llc_raw_recursive(content: LLCItemPayload, entities: list[TKLLEntity]) -> str:
    
    result: str = ""
    if isinstance(content, TKLLCContent):

        subject = llc_raw_entity(content.subject, entities) if content.subject else ''
        predicate = llc_raw_entity(content.predicate, entities) if content.predicate else ''
        direct = llc_raw_entity(content.direct,entities) if content.direct else ''
        indirects = ' '.join([llc_raw_entity(i, entities) for i in content.indirects]) if content.indirects else ''

        result = f"{subject} {predicate} {direct} {indirects}"
    elif isinstance(content, list):
        i: int = 0
        for item in content:
            op = item.op.value if i > 0 or item.op.value != TKOperator.AND else ''
            result += f" {op} ({llc_raw_recursive(item.content, entities)})"
            i += 1

    return result.strip()

# (DOING) get raw output from TKLLC
def llc_raw(tkLLC: TKLLC) -> str:

    result: str = ""
    i: int = 0
    for item in tkLLC.items:
        op = item.op if i > 0 or item.op != TKOperator.AND else ''
        result += op + ' (' + llc_raw_recursive(item.content, tkLLC.entities) + ') '
        i += 1

    # clean text
    result = " ".join(result.split())

    return result
