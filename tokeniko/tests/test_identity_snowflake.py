"""Identity-on-snowflake (the rename fission, live specimen 2026-07-13 → fixed 2026-07-14).

A Discord rename (test-probe-hellen → playbot-hellen, same snowflake) minted a SECOND soul: the
uid embeds the mutable display name, and resolution went by uid alone — trust history orphaned,
fold reset. Fix (author-ratified option A + aliases): resolution goes uid → channel-native
contextKey ("discord:<snowflake>", name-free) → mint; a contextKey hit with a fresh name is a
RENAME — the doc keeps its uid as minted (immutable: circulating references stay valid), updates
`name`, and remembers the old one in `aliases`. Individuals are EXCLUDED from the fallback (their
contextKey is the talker SCOPE, shared by every individual that talker mentions). Runs on the
sandbox memory DB (`_io`), cleaning up after itself.
"""
import pytest


@pytest.fixture()
def clean_souls(_io):
    from lib.core.models import TKMemoryStakeholdersDoc
    keys = ["discord:9001", "discord:9002", "discord:sf-talker@discord:9001"]
    def _wipe():
        TKMemoryStakeholdersDoc.find({"contextKey": {"$in": keys}}).delete().run()
    _wipe()
    yield
    _wipe()


def test_rename_resolves_to_the_same_soul(clean_souls):
    from lib.core.io import get_stakeholder
    born = get_stakeholder("sf-old@discord:9001", display_name="sf-old")
    renamed = get_stakeholder("sf-new@discord:9001", display_name="sf-new")
    assert renamed.id == born.id                      # one snowflake, one soul
    assert renamed.uid == "sf-old@discord:9001"       # the uid is immutable (as minted)
    assert renamed.name == "sf-new"                   # the display name follows the rename
    assert renamed.aliases == ["sf-old"]              # the biography remembers


def test_second_rename_appends_alias(clean_souls):
    from lib.core.io import get_stakeholder
    get_stakeholder("sf-a@discord:9001", display_name="sf-a")
    get_stakeholder("sf-b@discord:9001", display_name="sf-b")
    third = get_stakeholder("sf-c@discord:9001", display_name="sf-c")
    assert third.name == "sf-c" and third.aliases == ["sf-a", "sf-b"]


def test_different_snowflake_is_a_different_soul(clean_souls):
    from lib.core.io import get_stakeholder
    a = get_stakeholder("sf-one@discord:9001", display_name="sf-one")
    b = get_stakeholder("sf-one@discord:9002", display_name="sf-one")
    assert a.id != b.id                               # same name, different person


def test_individuals_are_never_unified_by_scope(clean_souls):
    from lib.core.io import get_stakeholder, upsert_individual
    # an INDIVIDUAL whose contextKey happens to be a talker scope containing a snowflake
    ind = upsert_individual("sf-newton", "sf-newton@discord:sf-talker@discord:9001",
                            "PERSON", None, "discord:sf-talker@discord:9001")
    # a participant lookup keyed on that same scope must NOT capture the individual
    p = get_stakeholder("sf-someone@discord:sf-talker@discord:9001", display_name="sf-someone")
    assert p.id != ind.id


def test_resolve_canonical_follows_the_snowflake(clean_souls):
    from lib.core.io import get_stakeholder
    from lib.core.trust import resolve_canonical
    born = get_stakeholder("sf-old@discord:9002", display_name="sf-old")
    # the NEW surface uid (post-rename string) resolves to the same soul without minting
    hit = resolve_canonical("sf-brandnew@discord:9002")
    assert hit is not None and hit.id == born.id
