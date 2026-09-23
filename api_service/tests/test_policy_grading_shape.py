"""Does the versioned policy schema actually fit the rules it is for?

The risk this file exists to catch is a storage shape that turns out not to
hold the real thing. It checks that against the live domain objects -- not
against copied literals -- so it fails if either side moves:

1. the shipped ruleset round-trips through the store and comes back equal;
2. a version is complete, not a patch, and an incomplete or wrongly-shaped
   one is refused at write time rather than at transcript time;
3. an amendment -- one instant, one version -- resolves correctly across
   both academic calendars, including the mid-session case; and
4. sealed history survives later changes.

It also records a finding rather than a property: the actual 2021 PhD rule
cannot be stored as ONE institution-wide series, because it assigns
different rulesets to sessions that begin at the same time. That is why
``domain.policy.BASELINE_GRADING_VERSIONS`` is keyed per calendar. See
test_the_2021_rule_assigns_different_rulesets_to_concurrent_sessions.
"""
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

#: The two PhD grade sets the 2021 revision moves between, from the live
#: module rather than retyped.
NARROW = POL._PHD_NARROW
WIDE = POL._PHD_WIDE

ALL_SESSIONS_IN_WINDOW = [f"{y}-{s}"
                          for y in range(2019, 2024)
                          for s in AS.SUFFIXES]


def _phd_payload(ec, cgpa):
    """A complete payload differing only in the PhD programme rules."""
    payload = POL.grading_payload_from(DEFAULT)
    payload["programme_rules"]["PHD"]["earned_credit_grades"] = sorted(ec)
    payload["programme_rules"]["PHD"]["cgpa_grades"] = sorted(cgpa)
    return payload


# ===================== Round-trip =====================

def test_todays_rules_round_trip_through_the_store(policy):
    """The exact ruleset the computation ships with, stored and resolved
    back, field for field."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT),
                     note="Rules as at the time of the policy-store work")

    built = policy.policy_for(POL.GRADING, "2024-I")

    assert isinstance(built, POL.GradingPolicy)
    assert built == DEFAULT


def test_grade_sets_survive_as_real_collections(policy):
    """Storage uses JSON arrays and the computation uses frozensets, so
    nothing along the way reintroduces the comma-joined strings that used
    to be matched by substring."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    built = policy.policy_for(POL.GRADING, "2024-I")

    ug = built.rules_for("BTE")
    assert isinstance(ug.earned_credit_grades, frozenset)
    assert ug.earned_credit_grades == DEFAULT.rules_for("BTE") \
        .earned_credit_grades
    assert isinstance(built.excluded_grades, frozenset)

    # The stored form really is an array.
    stored = policy.resolve(POL.GRADING, "2024-I").payload
    assert stored["programme_rules"]["UG"]["earned_credit_grades"] == \
        tuple(sorted(ug.earned_credit_grades))


def test_grade_sets_must_be_arrays_not_comma_separated_strings(policy):
    """The pre-refactor rules held grade sets as comma-separated strings
    and matched them with `in`. Storage refuses that shape outright so the
    quirk cannot creep back in through a payload."""
    bad = POL.grading_payload_from(DEFAULT)
    bad["programme_rules"]["UG"]["earned_credit_grades"] = "A,A-,B"
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", bad)
    assert "must be an array" in str(ei.value)


def test_incomplete_ruleset_is_refused(policy):
    partial = POL.grading_payload_from(DEFAULT)
    del partial["grade_points"]
    del partial["programme_rules"]["PHD"]["cgpa_grades"]
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", partial)
    assert "grade_points" in str(ei.value)
    assert "cgpa_grades" in str(ei.value)


def test_a_degree_mapped_to_an_undefined_class_is_refused_at_write_time(
        policy):
    """Caught when the ruleset is stored, not when a student of that degree
    asks for a transcript years later."""
    bad = POL.grading_payload_from(DEFAULT)
    bad["degree_classes"]["MTE"] = "POSTGRAD_TYPO"
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", bad)
    assert "POSTGRAD_TYPO" in str(ei.value)
    assert "programme_rules" in str(ei.value)


def test_a_default_class_with_no_rules_is_refused(policy):
    """Every degree code not listed would otherwise fail, which is most of
    them."""
    bad = POL.grading_payload_from(DEFAULT)
    bad["default_degree_class"] = "NOPE"
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", bad)
    assert "default_degree_class" in str(ei.value)


def test_a_version_is_complete_not_a_patch(policy):
    """Each version states the whole ruleset, so resolving a 2019
    transcript never has to replay the versions before it."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-I", _phd_payload(WIDE, NARROW))

    old = policy.policy_for(POL.GRADING, "2019-I")
    new = policy.policy_for(POL.GRADING, "2021-I")
    assert old.grade_points == new.grade_points  # carried, not inherited
    assert old.rules_for("PHD") != new.rules_for("PHD")


def test_a_programme_can_carry_its_own_grade_point_scale(policy):
    """'The grade definitions changed for the PhD programme' as one
    complete version, which is what the 2021 revision actually was."""
    payload = POL.grading_payload_from(DEFAULT)
    payload["programme_rules"]["PHD"]["grade_points"] = {
        "A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6}
    policy.supersede(POL.GRADING, "2000-T1", payload)

    built = policy.policy_for(POL.GRADING, "2024-I")
    assert built.rules_for("PHD").grade_points == {
        "A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6}
    # Everyone else stays on the institution-wide scale.
    assert built.rules_for("BTE").grade_points == DEFAULT.grade_points
    assert built.rules_for("MTE").grade_points == DEFAULT.grade_points


# ===================== The 2021 PhD revision =====================

def test_the_2021_rule_assigns_different_rulesets_to_concurrent_sessions(
        policy):
    """The finding that decides how this revision can be stored at all.

    A policy version is in force for an *instant*: every session beginning
    in that month resolves to it. The original rule branched on the session
    SUFFIX, and two suffixes from different academic calendars can name the
    same instant -- at which point the rule demands two different answers
    for one point in time.

    So it was never an amendment that took effect on a date; it was
    per-calendar improvisation during the pandemic years, when semester-
    and quarter-based programmes ran side by side. That is why the shipped
    baseline is keyed by session type, and why the live rules must not be
    seeded until the registrar has ruled on them.
    """
    by_instant = {}
    for session_type in POL.BASELINE_GRADING_VERSIONS:
        for suffix in AS.suffixes_for(session_type):
            session = f"2021-{suffix}"
            rules = POL.baseline_grading_policy(session).rules_for("PHD")
            # Compared on the grade sets: ProgrammeRules carries a mapping
            # of grade points and so is not hashable.
            by_instant.setdefault(AS.ordinal(session), {})[session] = (
                rules.earned_credit_grades, rules.cgpa_grades)

    disagreeing = {instant: group for instant, group in by_instant.items()
                   if len(set(group.values())) > 1}

    assert sorted(sorted(group) for group in disagreeing.values()) == [
        ["2021-I", "2021-T1"],
        ["2021-II", "2021-T3"],
    ], ("The 2021 rule no longer disagrees across concurrent sessions. If "
        "that is deliberate, the finding is resolved and the rule can be "
        "stored as one series.")


def test_the_store_cannot_hold_two_rulesets_for_one_instant(policy):
    """The mechanical consequence: refused, not silently resolved, because
    the unique index is on the instant."""
    policy.supersede(POL.GRADING, "2021-I", _phd_payload(WIDE, NARROW))
    with pytest.raises(PS.PolicyImmutableError, match="already exists"):
        policy.supersede(POL.GRADING, "2021-T1", _phd_payload(WIDE, WIDE))


def test_the_baseline_reproduces_the_original_rule_per_calendar(policy):
    """Read per calendar the rule IS coherent, and the shipped baseline
    reproduces it. Pinned here as the table someone has to defend.

    The quarter series widens at T1, reverts at T3 and widens again the
    next year -- faithful, not a transcription slip: T3 and T4 fell into
    the branch that logged "Unknown academic semester", i.e. they were
    never handled.
    """
    def ec(session):
        return POL.baseline_grading_policy(session) \
            .rules_for("PHD").earned_credit_grades

    assert [ec(f"2021-{s}") for s in AS.suffixes_for("semester")] == \
        [WIDE, WIDE, WIDE]
    assert [ec(f"2021-{s}") for s in AS.suffixes_for("quarter")] == \
        [WIDE, WIDE, NARROW, NARROW]
    assert ec("2020-I") == NARROW and ec("2020-T1") == NARROW
    assert ec("2022-T1") == WIDE


def test_an_unknown_session_falls_back_to_the_base_ruleset(policy):
    """The original logged 'Unknown academic semester' and carried on with
    its per-iteration defaults. A session that cannot be placed on the
    timeline still computes, under the base ruleset, with a warning."""
    fallback = POL.baseline_grading_policy("2021-XYZ").rules_for("PHD")
    assert fallback == DEFAULT.rules_for("PHD")
    assert fallback.earned_credit_grades == NARROW
    assert fallback.cgpa_grades == WIDE


# ===================== A well-formed amendment =====================

def test_a_single_instant_amendment_resolves_across_both_calendars(policy):
    """What a well-formed revision looks like: one version, one instant,
    and each calendar picks it up when its own next session begins.

    Effective from 2021-II (January) it governs 2021-T3 too -- both begin
    that month -- while 2021-T2, which began in October and is already
    under way, keeps the rules it started under. That is the mid-session
    case, and it is the reason resolution is on the session's start.
    """
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-II", _phd_payload(WIDE, WIDE),
                     note="PhD grade definitions revised")

    def ec(session):
        return policy.policy_for(POL.GRADING, session) \
            .rules_for("PHD").earned_credit_grades

    for session in ("2021-I", "2021-T1", "2021-T2"):
        assert ec(session) == NARROW, \
            f"{session} began before the change and must keep its rules"
    for session in ("2021-II", "2021-T3", "2021-T4", "2021-S"):
        assert ec(session) == WIDE, \
            f"{session} begins at or after the change"


def test_resolution_takes_the_session_and_nothing_else(policy):
    """No year, no semester list, no 'if year > 2021' at the call site."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-II", _phd_payload(WIDE, WIDE))

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
    policy.supersede(POL.GRADING, "2021-II", _phd_payload(WIDE, WIDE))
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
