"""Band-assert helpers — importable from test modules (`from tests.asserts import ...`).

BAND-ASSERTS, never exact floats. EvaluatorStatus .value strings (confirmed against
lib/core/evaluation.py): RESOLVED="resolved", INSUFFICIENT="insufficient_knowledge",
INCONSISTENT="inconsistent".
"""


def assert_resolved_true(r):
    assert r.status.value == "resolved" and r.truth > 0.85, (r.status, r.truth)


def assert_resolved_false(r):
    assert r.status.value == "resolved" and r.truth < 0.15, (r.status, r.truth)


def assert_insufficient(r):
    assert r.status.value == "insufficient_knowledge" and 0.35 < r.truth < 0.65, (r.status, r.truth)


def assert_inconsistent(r):
    assert r.status.value == "inconsistent" and r.truth < 0.05, (r.status, r.truth)
