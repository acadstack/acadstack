"""Does the versioned policy schema actually fit the rules it is for?

No rules move onto the store in this phase, so the risk is designing a
shape that turns out not to hold the real thing. These tests answer that
against the live domain objects -- not against copied literals -- so they
fail if either side moves:

1. ``DEFAULT_GRADING_POLICY`` round-trips through the store and comes
   back as an equal ``GradingPolicy``;
2. the "PhD passing grades introduced in 2021" amendment is reproduced
   session for session by ordinary effective-dated versions, checked
   against ``apply_phd_amendment`` itself; and
3. a stored ruleset NEUTRALISES that function, which is what lets the
   rules move onto the store without touching ``compute_cgpa_sgpa_ec``
   in the same change.

Test 2 also documents something uncomfortable that fell out of writing
it; see test_the_2021_amendment_is_not_chronologically_monotonic.
"""
import dataclasses
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import acad_session as AS  # noqa: E402
import policy_store as PS  # noqa: E402
import settings_store as SS  # noqa: E402
from domain import policy as POL  # noqa: E402


@pytest.fixture
def policy(db):
    saved = dict(PS._REGISTRY)
    PS.invalidate_cache()
    SS.invalidate_cache()
    # domain/policy.py declares "grading" at import time; re-declare in
    # case another test cleared the registry.
    PS.declare_policy_group(
        POL.GRADING, doc=POL.GRADING_GROUP.doc,
        builder=POL.build_grading_policy,
        validator=POL.validate_grading_payload)
    yield PS
    PS._REGISTRY.clear()
    PS._REGISTRY.update(saved)
    PS.invalidate_cache()
    SS.invalidate_cache()


DEFAULT = POL.DEFAULT_GRADING_POLICY

# The four PhD grade sets the 2021 amendment moves between, taken from
# the live policy object rather than retyped.
D_EC = DEFAULT.phd_ec_grades
D_PASS = DEFAULT.phd_ec_pass_grades
A_EC = DEFAULT.phd_ec_grades_amended
A_PASS = DEFAULT.phd_ec_pass_grades_amended


# ===================== Round-trip =====================

def test_todays_rules_round_trip_through_the_store(policy):
    """The exact policy object computation uses today, stored and
    resolved back, field for field."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT),
                     note="Rules as at the time of the policy-store work")

    built = policy.policy_for(POL.GRADING, "2024-I")

    # Everything is carried across unchanged except the two *_amended
    # fields, which a stored version collapses onto its own sets (see
    # build_grading_policy, and the neutralisation test below).
    expected = dataclasses.replace(
        DEFAULT,
        phd_ec_grades_amended=DEFAULT.phd_ec_grades,
        phd_ec_pass_grades_amended=DEFAULT.phd_ec_pass_grades)

    assert isinstance(built, POL.GradingPolicy)
    assert built == expected


def test_round_trip_preserves_the_string_shape_the_computation_expects(
        policy):
    """Storage uses JSON arrays; the computation matches with `in` on
    comma-separated strings. The builder joins them back, so nothing
    downstream sees the change of shape."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    built = policy.policy_for(POL.GRADING, "2024-I")

    assert built.ug_ec_grades == DEFAULT.ug_ec_grades
    assert isinstance(built.ug_ec_grades, str)
    assert built.ec_grades_for("BTE", built.phd_ec_grades) == \
        DEFAULT.ug_ec_grades
    # The stored form really is an array, though.
    stored = policy.resolve(POL.GRADING, "2024-I").payload
    assert stored["ug_ec_grades"] == tuple(DEFAULT.ug_ec_grades.split(","))


def test_grade_sets_must_be_arrays_not_comma_separated_strings(policy):
    """The stringly-typed sets in the computation are matched with `in`,
    i.e. substring matching. Storage refuses that shape outright so the
    quirk cannot be carried across by accident."""
    bad = POL.grading_payload_from(DEFAULT)
    bad["ug_ec_grades"] = DEFAULT.ug_ec_grades  # the in-code shape
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", bad)
    assert "must be an array" in str(ei.value)


def test_incomplete_ruleset_is_refused(policy):
    partial = POL.grading_payload_from(DEFAULT)
    del partial["phd_ec_pass_grades"]
    del partial["grade_points"]
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", partial)
    assert "grade_points" in str(ei.value)
    assert "phd_ec_pass_grades" in str(ei.value)


def test_a_version_is_complete_not_a_patch(policy):
    """Each version states the whole ruleset, so resolving a 2019
    transcript never has to replay the versions before it."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-I",
                     POL.grading_payload_from(DEFAULT, phd_ec_grades=A_EC))

    old = policy.policy_for(POL.GRADING, "2019-I")
    new = policy.policy_for(POL.GRADING, "2021-I")
    assert old.grade_points == new.grade_points  # carried, not inherited
    assert old.phd_ec_grades != new.phd_ec_grades


# ===================== The 2021 PhD amendment =====================

#: The amendment as effective-dated versions: the session a ruleset takes
#: effect from, and the PhD grade sets it states. Authored by hand -- this
#: is the data a migration would seed -- and cross-checked below against
#: apply_phd_amendment itself. Nothing here branches on anything.
AMENDMENT_AS_VERSIONS = [
    ("2000-T1", D_EC, A_PASS),
    ("2021-T1", A_EC, D_PASS),
    ("2021-T3", D_EC, D_PASS),
    ("2021-I", A_EC, A_PASS),
    ("2021-II", A_EC, D_PASS),
]

ALL_SESSIONS_IN_WINDOW = [f"{y}-{s}"
                          for y in range(2019, 2024)
                          for s in AS.SUFFIXES]


def _load_amendment(policy):
    for session, phd_ec, phd_pass in AMENDMENT_AS_VERSIONS:
        policy.supersede(
            POL.GRADING, session,
            POL.grading_payload_from(DEFAULT, phd_ec_grades=phd_ec,
                                     phd_ec_pass_grades=phd_pass),
            note="PhD passing grades, 2021 amendment")


def test_2021_phd_amendment_is_reproduced_exactly_by_versions(policy):
    """The point of the whole design: a hardcoded branch on the year
    becomes rows, and resolution reproduces it session for session --
    checked against the live function, not a copy of it."""
    _load_amendment(policy)

    for session in ALL_SESSIONS_IN_WINDOW:
        expected = POL.apply_phd_amendment(DEFAULT, session)
        built = policy.policy_for(POL.GRADING, session)
        assert (built.phd_ec_grades, built.phd_ec_pass_grades) == expected, \
            f"PhD grade sets differ for {session}"


def test_the_stored_ruleset_neutralises_the_hardcoded_amendment(policy):
    """Why the rules can move onto the store without editing
    compute_cgpa_sgpa_ec: it may keep calling apply_phd_amendment per
    course, and get back the version's own sets for every session."""
    _load_amendment(policy)

    for session in ALL_SESSIONS_IN_WINDOW:
        built = policy.policy_for(POL.GRADING, session)
        assert POL.apply_phd_amendment(built, session) == \
            (built.phd_ec_grades, built.phd_ec_pass_grades)


def test_2021_phd_amendment_needs_no_branch_at_the_call_site(policy):
    """Resolution takes the session and nothing else -- no year, no
    semester list, no 'if year > 2021'."""
    _load_amendment(policy)
    resolved = policy.resolve(POL.GRADING, "2021-I")
    assert (resolved.effective_from, resolved.effective_to) == \
        ("2021-I", "2021-II")
    assert resolved.covers("2021-I")
    assert not resolved.covers("2021-II")
    assert not resolved.covers("2021-T4")


def test_the_2021_amendment_is_not_chronologically_monotonic(policy):
    """A finding, pinned as a test rather than left in a comment.

    Under this codebase's own session chronology (T1..T4 precede I, II,
    S within a year -- domain/transcript.py's `suffixes` list), the 2021
    rule does not read as an amendment taking effect once. The
    earned-credit set widens at 2021-T1, reverts at 2021-T3, widens again
    at 2021-I; and the CGPA set takes a value at 2021-I that it holds for
    that one session only. That is because the code's semester list
    ["II", "S", "T1", "T2"] mixes the two halves of the year.

    The storage design handles it -- that is what the test above shows --
    but a rule that zig-zags is far more likely to be a bug than an
    institution's intent. Worth resolving with the registrar BEFORE the
    live rules are moved onto the store, because each of these becomes a
    row someone has to defend.
    """
    _load_amendment(policy)
    phd_ec = [policy.policy_for(POL.GRADING, f"2021-{s}").phd_ec_grades
              for s in AS.SUFFIXES]

    # T1, T2 widened -> T3, T4 back to narrow -> I, II, S widened again.
    assert phd_ec == [A_EC, A_EC, D_EC, D_EC, A_EC, A_EC, A_EC]

    phd_pass = [policy.policy_for(POL.GRADING, f"2021-{s}").phd_ec_pass_grades
                for s in AS.SUFFIXES]
    # 2021-I is the only session in the whole window with this value.
    assert phd_pass[AS.SUFFIXES.index("I")] == A_PASS
    assert phd_pass.count(A_PASS) == 1


def test_sealed_amendment_still_resolves_after_later_changes(policy):
    """Once 2021 is closed, a later grading change must not disturb it --
    the transcript case the whole design exists for."""
    _load_amendment(policy)
    before = {s: policy.policy_for(POL.GRADING, s)
              for s in ALL_SESSIONS_IN_WINDOW if s.startswith("2021")}

    policy.close_session("2021-S")

    tightened = POL.grading_payload_from(DEFAULT)
    tightened["grade_points"]["A"] = 4
    policy.supersede(POL.GRADING, "2024-I", tightened,
                     note="New grade point scale")

    for session, ruleset in before.items():
        assert policy.policy_for(POL.GRADING, session) == ruleset
    assert policy.policy_for(POL.GRADING, "2024-I").grade_points["A"] == 4
