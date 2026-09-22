"""Does the versioned policy schema actually fit the rules it is for?

The risk this file exists to catch is designing a shape that turns out not
to hold the real thing. It answers that against the live domain objects --
not against copied literals -- so it fails if either side moves:

1. ``DEFAULT_GRADING_POLICY`` round-trips through the store and comes
   back as an equal ``GradingPolicy``;
2. a stored ruleset NEUTRALISES ``apply_phd_amendment``, which is what
   lets the rules move onto the store without touching
   ``compute_cgpa_sgpa_ec`` in the same change; and
3. a well-formed amendment -- one instant, one version -- resolves
   correctly across both academic calendars.

The uncomfortable part is point 4, which is a finding rather than a
property: the actual 2021 PhD rule CANNOT be stored as one series,
because it assigns different rulesets to sessions that begin at the same
time. See test_the_2021_rule_assigns_different_rulesets_to_concurrent_sessions.
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

#: Every session across the years the 2021 rule spans, both calendars.
ALL_SESSIONS_IN_WINDOW = [f"{y}-{s}"
                          for y in range(2019, 2024)
                          for s in AS.SUFFIXES]


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
#
# The earlier phase modelled this amendment as a hand-authored table of
# effective-dated versions and checked that resolution reproduced
# apply_phd_amendment session for session. It did -- under the pre-0004
# ordinal scheme, which ranked every suffix on one arbitrary within-year
# order and so gave 2021-T1 and 2021-I different positions.
#
# Migration 0004 replaced that with a real timeline, on which those two
# sessions BEGIN TOGETHER. The tests below record what that exposes.


def _phd_sets(session):
    """The (earned-credit, cgpa) PhD grade sets the in-code rule yields."""
    return POL.apply_phd_amendment(DEFAULT, session)


def test_the_2021_rule_assigns_different_rulesets_to_concurrent_sessions(
        policy):
    """The finding that decides how this amendment can be stored at all.

    A policy version is in force for an *instant*: every session beginning
    in that month resolves to it. The 2021 rule does not respect that. It
    branches on the session SUFFIX, and two suffixes from different
    academic calendars can name the same instant -- at which point the rule
    demands two different answers for one point in time.

    So this rule is not an amendment that took effect on a date. It is
    per-calendar improvisation (the pandemic years, when semester- and
    quarter-based programmes ran side by side), and no single
    effective-dated series can reproduce it. Resolving it with the
    registrar is a prerequisite to seeding the live rules, not a tidy-up
    afterwards.
    """
    conflicts = {}
    for suffix in AS.SUFFIXES:
        session = f"2021-{suffix}"
        conflicts.setdefault(AS.ordinal(session), {})[session] = \
            _phd_sets(session)

    disagreeing = {ordinal: group
                   for ordinal, group in conflicts.items()
                   if len(set(group.values())) > 1}

    assert disagreeing, (
        "The 2021 rule no longer disagrees across concurrent sessions. If "
        "that is deliberate, this finding is resolved and the amendment can "
        "be stored as one series -- delete this test and seed it.")

    # Exactly the two instants where the two calendars start together.
    assert sorted(
        sorted(group) for group in disagreeing.values()) == [
        ["2021-I", "2021-T1"],
        ["2021-II", "2021-T3"],
    ]


def test_the_store_cannot_hold_two_rulesets_for_one_instant(policy):
    """The mechanical consequence: the attempt is refused rather than
    silently resolved, because the unique index is on the instant."""
    policy.supersede(POL.GRADING, "2021-I",
                     POL.grading_payload_from(DEFAULT, phd_ec_grades=A_EC,
                                              phd_ec_pass_grades=A_PASS))
    with pytest.raises(PS.PolicyImmutableError, match="already exists"):
        policy.supersede(POL.GRADING, "2021-T1",
                         POL.grading_payload_from(DEFAULT, phd_ec_grades=A_EC,
                                                  phd_ec_pass_grades=D_PASS))


def test_the_rule_is_coherent_within_one_calendar_except_for_one_session(
        policy):
    """What the rule looks like once the two calendars are separated --
    which is how it should be read before anyone signs off on rows.

    The quarter track widens the earned-credit set for T1/T2 and then
    reverts for T3/T4, but only because T3/T4 fall through to the branch
    that logs 'Unknown academic semester' -- they were never handled. The
    semester track is monotonic in the earned-credit set, but its CGPA set
    takes the widened value at 2021-I and at no other session, ever.
    """
    semester = [_phd_sets(f"2021-{s}") for s in AS.suffixes_for("semester")]
    quarter = [_phd_sets(f"2021-{s}") for s in AS.suffixes_for("quarter")]

    # Earned-credit set: semester widens once and stays; quarter reverts.
    assert [ec for ec, _ in semester] == [A_EC, A_EC, A_EC]
    assert [ec for ec, _ in quarter] == [A_EC, A_EC, D_EC, D_EC]

    # CGPA set: 2021-I is the only session in either calendar that ever
    # sees the amended value.
    assert [pa for _, pa in semester] == [A_PASS, D_PASS, D_PASS]
    assert [pa for _, pa in quarter] == [D_PASS] * 4


def test_a_single_instant_amendment_resolves_across_both_calendars(policy):
    """What a well-formed amendment looks like: one version, one instant,
    and every calendar picks it up when its own next session begins.

    Effective from 2021-II (January), it governs 2021-T3 too -- both begin
    that month -- while 2021-T2, which started in October and is already
    under way, keeps the rules it began under.
    """
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-II",
                     POL.grading_payload_from(DEFAULT, phd_ec_grades=A_EC),
                     note="PhD grade definitions revised")

    before = [s for s in ("2021-I", "2021-T1", "2021-T2")]
    after = [s for s in ("2021-II", "2021-T3", "2021-T4", "2021-S")]

    for session in before:
        assert policy.policy_for(POL.GRADING, session).phd_ec_grades == D_EC, \
            f"{session} began before the change and must keep its rules"
    for session in after:
        assert policy.policy_for(POL.GRADING, session).phd_ec_grades == A_EC, \
            f"{session} begins at or after the change"


def test_the_stored_ruleset_neutralises_the_hardcoded_amendment(policy):
    """Why the rules can move onto the store without editing
    compute_cgpa_sgpa_ec: a stored version collapses the two *_amended
    fields onto its own sets, so apply_phd_amendment returns that
    version's sets for every session and its branch stops mattering."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))

    for session in ALL_SESSIONS_IN_WINDOW:
        built = policy.policy_for(POL.GRADING, session)
        assert POL.apply_phd_amendment(built, session) == \
            (built.phd_ec_grades, built.phd_ec_pass_grades)


def test_resolution_takes_the_session_and_nothing_else(policy):
    """No year, no semester list, no 'if year > 2021' at the call site."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-II",
                     POL.grading_payload_from(DEFAULT, phd_ec_grades=A_EC))

    resolved = policy.resolve(POL.GRADING, "2021-II")
    assert (resolved.effective_from, resolved.effective_to) == \
        ("2021-II", None)
    assert resolved.covers("2021-II")
    assert resolved.covers("2021-T3")      # concurrent with 2021-II
    assert resolved.covers("2021-S")
    assert not resolved.covers("2021-T2")  # started before it


def test_sealed_rules_still_resolve_after_later_changes(policy):
    """Once 2021 is closed, a later grading change must not disturb it --
    the transcript case the whole design exists for."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-II",
                     POL.grading_payload_from(DEFAULT, phd_ec_grades=A_EC))
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
