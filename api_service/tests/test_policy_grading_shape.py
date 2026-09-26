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

The 2021 PhD rule that motivated much of this design is gone: it assigned
different rulesets to sessions beginning at the same instant, so it could
not be stored as one series, and with no deployment to preserve it was
retired rather than reproduced. What remains of it here is the property it
taught us -- one instant, one ruleset -- in
test_the_store_cannot_hold_two_rulesets_for_one_instant.
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

#: The shipped PhD grade sets, and a narrower variant to amend towards, so
#: the amendment tests observe a real change without retyping a ruleset.
SHIPPED = POL._PHD_EC
NARROWER = frozenset(("A", "A-", "B"))

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


def test_the_payload_holds_only_rules_a_senate_could_amend():
    """Fixed codes, the rounding and the LTP format are not versioned."""
    payload = POL.grading_payload_from(DEFAULT)
    assert set(payload) == {
        "grade_points", "degree_classes", "default_degree_class",
        "programme_rules", "credit_enrol_types", "excluded_grades",
        "passed_course_grades"}


RETIRED = {"ltp": {"separator": "-", "field_count": 5},
           "credit_enrol_type_match": "substring",
           "counted_enrol_status": "ENRO", "satisfactory_grade": "S",
           "gpa_decimal_places": 2}


def test_retired_fields_are_refused_on_write(policy):
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1",
                         POL.grading_payload_from(DEFAULT, **RETIRED))
    for key in RETIRED:
        assert f"grading: {key} is not a grading policy field" \
            in ei.value.errors


def test_a_version_stored_with_retired_fields_still_builds():
    """A row written before the fields were retired is still readable."""
    built = POL.build_grading_policy(
        POL.grading_payload_from(DEFAULT, **RETIRED))
    assert built == DEFAULT


def test_every_problem_is_reported_in_one_rejection(policy):
    """The admin UI lists them together."""
    bad = POL.grading_payload_from(DEFAULT)
    del bad["excluded_grades"]
    bad["grade_points"]["A"] = "ten"
    bad["passed_course_grades"] = ["A", "A"]
    bad["programme_rules"]["PG"]["cgpa_grades"] = "A,B"
    with pytest.raises(PS.PolicyValidationError) as ei:
        policy.supersede(POL.GRADING, "2000-T1", bad)
    assert ei.value.errors == [
        "grading: grade_points['A'] must be a number, got 'ten'",
        "grading: excluded_grades is required",
        "grading: passed_course_grades contains duplicate entries",
        "grading: programme_rules['PG'].cgpa_grades must be an array of "
        "codes, not a str -- a comma-separated string is not accepted here",
    ]


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
    policy.supersede(POL.GRADING, "2021-I", _phd_payload(NARROWER, NARROWER))

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

def test_the_store_cannot_hold_two_rulesets_for_one_instant(policy):
    """The mechanical consequence: refused, not silently resolved, because
    the unique index is on the instant."""
    policy.supersede(POL.GRADING, "2021-I", _phd_payload(NARROWER, NARROWER))
    with pytest.raises(PS.PolicyImmutableError, match="already exists"):
        policy.supersede(POL.GRADING, "2021-T1", _phd_payload(NARROWER, NARROWER))


def test_an_unknown_session_still_computes_under_the_shipped_rules(policy):
    """The original logged 'Unknown academic semester' and carried on. A
    session that cannot be placed on the timeline still resolves, to the
    ruleset the code ships with, with a warning."""
    assert POL.load_grading_policy("2021-XYZ") is POL.DEFAULT_GRADING_POLICY
    assert POL.load_grading_policy(None) is POL.DEFAULT_GRADING_POLICY


def test_a_seeded_ruleset_is_what_the_computation_resolves(policy):
    """The seeder is what makes the store the runtime source of truth --
    without it load_grading_policy() only ever returns the in-code
    baseline, and the whole versioned store is inert."""
    import default_seed_data as SEED

    assert SEED.seed_grading_policy() == 1
    resolved = POL.load_grading_policy("2024-I")
    assert resolved == DEFAULT           # same rules...
    assert resolved is not DEFAULT       # ...but come off the store

    # Idempotent, and it never supersedes an institution's own amendment.
    assert SEED.seed_grading_policy() == 0
    policy.supersede(POL.GRADING, "2025-I",
                     _phd_payload(NARROWER, NARROWER),
                     note="Local amendment")
    assert SEED.seed_grading_policy() == 0
    assert POL.load_grading_policy("2025-I").rules_for("PHD") \
        .earned_credit_grades == NARROWER


def test_seeding_is_skipped_rather_than_failing_inside_sealed_history(
        policy):
    """The baseline is effective from 2000, so on an install that has
    closed a session it would land in sealed history. A refused seed must
    not stop the app booting."""
    import default_seed_data as SEED

    policy.close_session("2020-I")
    assert SEED.seed_grading_policy() == 0
    # ...and the in-code baseline still answers.
    assert POL.load_grading_policy("2021-I") is POL.DEFAULT_GRADING_POLICY


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
    policy.supersede(POL.GRADING, "2021-II", _phd_payload(NARROWER, NARROWER),
                     note="PhD grade definitions revised")

    def ec(session):
        return policy.policy_for(POL.GRADING, session) \
            .rules_for("PHD").earned_credit_grades

    for session in ("2021-I", "2021-T1", "2021-T2"):
        assert ec(session) == SHIPPED, \
            f"{session} began before the change and must keep its rules"
    for session in ("2021-II", "2021-T3", "2021-T4", "2021-S"):
        assert ec(session) == NARROWER, \
            f"{session} begins at or after the change"


def test_resolution_takes_the_session_and_nothing_else(policy):
    """No year, no semester list, no 'if year > 2021' at the call site."""
    policy.supersede(POL.GRADING, "2000-T1",
                     POL.grading_payload_from(DEFAULT))
    policy.supersede(POL.GRADING, "2021-II", _phd_payload(NARROWER, NARROWER))

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
    policy.supersede(POL.GRADING, "2021-II", _phd_payload(NARROWER, NARROWER))
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
