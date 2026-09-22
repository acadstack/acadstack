"""Academic policy, as data that domain functions receive.

Phase 2 gave us ``settings_store.setting(key, default)``. If domain
functions called it ad hoc they would be untestable with policy other
than whatever happens to be in the database, and every call site would
have to be found again when Phase 6 introduces effective-dated policy.

So the shape is: **frozen dataclasses of plain values, built by a
``load_*`` function at the edge and passed in as an argument.** Domain
functions take ``policy=None`` and fall back to the loader, which keeps
call sites short while leaving every one of them injectable::

    compute_cgpa_sgpa_ec(courses, "PHD", policy=GradingPolicy(
        grade_points={"A": 10, "B": 5}, ...))

The ``load_*`` functions are the only place in ``domain/`` allowed to
read ambient configuration (the settings store, app config). Everything
below them takes values.

When Phase 6 lands, ``load_grading_policy()`` grows an ``acad_session``
argument and resolves the ruleset in force for that session; the domain
functions that already take a ``GradingPolicy`` do not change at all.
That is the point of doing this now.
"""

import logging
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

import policy_store as PS
import settings_store as ST

# ---------------------------------------------------------------- grading


@dataclass(frozen=True)
class GradingPolicy:
    """Grade vocabulary and credit rules used by transcript computation.

    Several fields are comma-separated *strings* rather than collections
    because the computation tests membership with ``in``, i.e. substring
    matching, and that quirk is load-bearing: ``tests/test_gpa_computation.py``
    characterises it (a one-character enrol_type matches "C,CM,CC"). Do
    not "fix" these into tuples without changing those tests, which is
    explicitly out of scope until the rules move into the versioned
    policy store.
    """

    #: grade letter -> grade points
    grade_points: Mapping[str, int]

    #: Grades earning credit, per degree class (comma-separated).
    ug_ec_grades: str
    pg_ec_grades: str

    #: Grades counted in CGPA for UG and PG.
    pass_grades: str

    #: PhD defaults, before the session-dependent amendment below.
    phd_ec_grades: str
    phd_ec_pass_grades: str

    #: The values the amendment swaps in. The amendment widens the
    #: earned-credit set and narrows the CGPA set; which of the two it
    #: applies depends on the session (see apply_phd_amendment).
    phd_ec_grades_amended: str
    phd_ec_pass_grades_amended: str

    #: Academic year in which the PhD amendment took effect, and the
    #: semester suffixes that split that year.
    phd_amendment_year: int = 2021
    phd_amendment_first_sem: str = "I"
    phd_amendment_later_sems: Sequence[str] = ("II", "S", "T1", "T2")

    #: Degree codes that select a degree's credit rules.
    ug_degree_code: str = "BTE"
    phd_degree_code: str = "PHD"

    #: Enrolment types that count as credit (substring-matched, see above).
    credit_enrol_types: str = "C,CM,CC"

    #: Only enrolments in this status are counted.
    counted_enrol_status: str = "ENRO"

    #: Satisfactory grade (counted separately, then netted out), and the
    #: grades removed from the SGPA denominator entirely.
    satisfactory_grade: str = "S"
    excluded_grades: Sequence[str] = ("U", "I", "W")

    #: Grades that make a course "passed" for the passed-courses listing.
    passed_course_grades: str = "A,A-,B,B-,C,C-,D,S"

    def ec_grades_for(self, degree: str, phd_ec_grades: str) -> str:
        """Earned-credit grade set for a degree. ``phd_ec_grades`` is the
        session-adjusted PhD set from :func:`apply_phd_amendment`."""
        if degree == self.ug_degree_code:
            return self.ug_ec_grades
        if degree == self.phd_degree_code:
            return phd_ec_grades
        return self.pg_ec_grades


DEFAULT_GRADING_POLICY = GradingPolicy(
    grade_points={"A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6, "C-": 5,
                  "D": 4, "E": 2, "F": 0},
    ug_ec_grades="A,A-,B,B-,C,C-,D,S,NP",
    pg_ec_grades="A,A-,B,B-,C,C-,D,S",
    pass_grades="A,A-,B,B-,C,C-,D",
    phd_ec_grades="A,A-,B,B-,C",
    phd_ec_pass_grades="A,A-,B,B-,C,C-",
    phd_ec_grades_amended="A,A-,B,B-,C,C-",
    phd_ec_pass_grades_amended="A,A-,B,B-,C",
)


def apply_phd_amendment(policy: GradingPolicy, acad_session: str) -> tuple:
    """Returns ``(phd_ec_grades, phd_ec_pass_grades)`` in force for
    ``acad_session``.

    This is the "PhD passing grades introduced in 2021" rule, lifted out
    of the computation loop verbatim -- including the branch that leaves
    the defaults in place for an unrecognised semester suffix, which
    yields the *opposite* combination from the pre-2021 case.
    ``tests/test_gpa_computation.py`` pins all eight cases.

    Phase 6/7 deletes this function: the amendment becomes two ordinary
    effective-dated versions of the PhD ruleset, and the caller simply
    asks for the ruleset in force for the session.
    """
    ec_grades = policy.phd_ec_grades
    ec_pass_grades = policy.phd_ec_pass_grades

    year = int(acad_session[:4])
    sem = acad_session[5:]  # I, II, S, T1, T2, etc.

    if year > policy.phd_amendment_year:
        ec_grades = policy.phd_ec_grades_amended
    elif year < policy.phd_amendment_year:
        ec_pass_grades = policy.phd_ec_pass_grades_amended
    else:  # The amendment year itself
        if sem == policy.phd_amendment_first_sem:
            ec_pass_grades = policy.phd_ec_pass_grades_amended
            ec_grades = policy.phd_ec_grades_amended
        elif sem in policy.phd_amendment_later_sems:
            ec_grades = policy.phd_ec_grades_amended
        else:
            logging.warning(f"Unknown academic semester: '{sem}'")

    return ec_grades, ec_pass_grades


def load_grading_policy(acad_session: Optional[str] = None) -> GradingPolicy:
    """The grading policy in force.

    ``acad_session`` is accepted but unused today: the values still come
    from code. It is in the signature so that call sites written now pass
    the session, and Phase 6 can make the resolution effective-dated
    without touching them.
    """
    return DEFAULT_GRADING_POLICY


# ------------------------------------------- grading, effective-dated

#: Name of the versioned grading policy group (see policy_store.py).
GRADING = "grading"

#: Payload keys holding a set of codes, stored as JSON arrays.
_GRADING_SET_KEYS = ("ug_ec_grades", "pg_ec_grades", "pass_grades",
                     "phd_ec_grades", "phd_ec_pass_grades",
                     "excluded_grades", "passed_course_grades",
                     "credit_enrol_types")

_GRADING_REQUIRED = ("grade_points",) + _GRADING_SET_KEYS + (
    "counted_enrol_status", "satisfactory_grade")


def grading_payload_from(policy: GradingPolicy, phd_ec_grades=None,
                         phd_ec_pass_grades=None) -> dict:
    """A storable payload for one version of the grading rules.

    Takes the PhD grade sets explicitly because that is precisely what
    the 2021 amendment varies: one call per effective range, with the
    sets already resolved for that range. Everything else is carried
    across from ``policy``.

    Note what is NOT stored: ``ug_degree_code``/``phd_degree_code`` (which
    degree codes map to which rules is institution configuration, not
    academic policy) and the ``phd_amendment_*`` fields (the amendment
    becomes the sequence of versions itself).
    """
    def items(value):
        return list(value) if not isinstance(value, str) else value.split(",")

    return {
        "grade_points": dict(policy.grade_points),
        "ug_ec_grades": items(policy.ug_ec_grades),
        "pg_ec_grades": items(policy.pg_ec_grades),
        "pass_grades": items(policy.pass_grades),
        "phd_ec_grades": items(phd_ec_grades or policy.phd_ec_grades),
        "phd_ec_pass_grades": items(
            phd_ec_pass_grades or policy.phd_ec_pass_grades),
        "excluded_grades": items(policy.excluded_grades),
        "passed_course_grades": items(policy.passed_course_grades),
        "credit_enrol_types": items(policy.credit_enrol_types),
        "counted_enrol_status": policy.counted_enrol_status,
        "satisfactory_grade": policy.satisfactory_grade,
    }


def build_grading_policy(payload) -> GradingPolicy:
    """Stored payload -> :class:`GradingPolicy`.

    Two translations happen here, and both are deliberate.

    **Arrays back to comma-separated strings.** The computation tests
    membership with ``in`` -- substring matching, not set membership --
    and that quirk is load-bearing (``tests/test_gpa_computation.py``
    characterises it). Storage uses JSON arrays because that is the right
    shape; this joins them so the computation is bit-for-bit unchanged.
    Fixing the quirk is a separate change that touches this function and
    the membership tests together.

    **The 2021 amendment is neutralised.** ``phd_ec_grades_amended`` is
    set equal to ``phd_ec_grades`` (and likewise for the pass set), so
    every branch of :func:`apply_phd_amendment` returns the same pair for
    any session. The store has already answered the question the branch
    was asking, so leaving the branch in place changes nothing --
    which is what lets the rules move onto the store without touching
    ``compute_cgpa_sgpa_ec`` in the same change.
    """
    missing = [k for k in _GRADING_REQUIRED if k not in payload]
    if missing:
        raise ValueError(f"missing key(s): {', '.join(sorted(missing))}")

    def joined(key):
        return ",".join(payload[key])

    phd_ec = joined("phd_ec_grades")
    phd_pass = joined("phd_ec_pass_grades")

    return GradingPolicy(
        grade_points={str(k): v for k, v in payload["grade_points"].items()},
        ug_ec_grades=joined("ug_ec_grades"),
        pg_ec_grades=joined("pg_ec_grades"),
        pass_grades=joined("pass_grades"),
        phd_ec_grades=phd_ec,
        phd_ec_pass_grades=phd_pass,
        phd_ec_grades_amended=phd_ec,
        phd_ec_pass_grades_amended=phd_pass,
        credit_enrol_types=joined("credit_enrol_types"),
        counted_enrol_status=str(payload["counted_enrol_status"]),
        satisfactory_grade=str(payload["satisfactory_grade"]),
        excluded_grades=tuple(payload["excluded_grades"]),
        passed_course_grades=joined("passed_course_grades"),
    )


def validate_grading_payload(payload):
    """Structural checks beyond what the builder enforces. Deliberately
    does not police WHICH grades an institution recognises: that is
    exactly the kind of rule that legitimately changes between
    versions."""
    errors = []

    points = payload.get("grade_points")
    if not isinstance(points, Mapping) or not points:
        errors.append("grade_points must be a non-empty object")
    else:
        for grade, value in points.items():
            if not isinstance(grade, str) or not grade.strip():
                errors.append(f"grade_points has a blank grade key: {grade!r}")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"grade_points[{grade!r}] must be a number, "
                              f"got {value!r}")

    for key in _GRADING_SET_KEYS:
        items = payload.get(key)
        if items is None:
            continue  # the builder already reports it as missing
        if isinstance(items, str) or not isinstance(items, (list, tuple)):
            errors.append(f"{key} must be an array of codes, not a "
                          f"{type(items).__name__} -- the comma-separated "
                          f"strings used in code are not accepted here")
            continue
        if any(not isinstance(i, str) or not i.strip() for i in items):
            errors.append(f"{key} must contain only non-empty strings")
        if len(set(items)) != len(items):
            errors.append(f"{key} contains duplicate entries")

    for key in ("counted_enrol_status", "satisfactory_grade"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str)
                                  or not value.strip()):
            errors.append(f"{key} must be a non-empty string")

    return errors


GRADING_GROUP = PS.declare_policy_group(
    GRADING,
    doc="Grade vocabulary, grade points and earned-credit rules used to "
        "compute SGPA, CGPA and earned credits. Versioned per academic "
        "session: a transcript is always computed under the ruleset in "
        "force for the session being reported.",
    builder=build_grading_policy,
    validator=validate_grading_payload,
)


def resolve_grading_policy(acad_session: str) -> GradingPolicy:
    """The stored grading ruleset in force for ``acad_session``.

    This is the effective-dated replacement for :func:`load_grading_policy`.
    It is NOT yet what computation calls: no ruleset has been seeded, so
    it would raise. Switching over means seeding a baseline version and
    changing load_grading_policy() below to delegate here -- a change that
    alters how transcripts compute and needs its own verification against
    real grade data. See docs/versioned-policy.md section 8.

    Raises:
        PolicyNotFoundError: if no version covers the session.
    """
    return PS.policy_for(GRADING, acad_session)


# -------------------------------------------------------------- enrolment


@dataclass(frozen=True)
class EnrolmentPolicy:
    """Rules governing enrolment requests and approvals."""

    #: Skips the "semester fees paid" precondition for students.
    disable_fees_check: bool = False

    #: Enrolment statuses that occupy a timetable slot, and therefore
    #: participate in slot-conflict detection.
    slot_conflict_statuses: Sequence[str] = ("IPEN", "APEN", "ENRO")

    #: Enrolment type code meaning "audit only".
    audit_enrol_type: str = "A"

    #: Status an enrolment request enters, and the status/type a bulk
    #: enrolment by the academic section is created with.
    requested_status: str = "IPEN"
    bulk_enrol_status: str = "ENRO"
    bulk_enrol_type: str = "C"

    #: Status applied instead when ACA/DEA perform a drop/withdraw.
    academic_section_drop_status: str = "ASREJ"


def load_enrolment_policy() -> EnrolmentPolicy:
    """Reads the effective enrolment policy from the settings store.

    This is the only place in the enrolment domain that touches ambient
    configuration; everything downstream receives the resulting
    :class:`EnrolmentPolicy` as an argument.
    """
    return EnrolmentPolicy(
        disable_fees_check=ST.setting("enrolment.disable_fees_check"))
