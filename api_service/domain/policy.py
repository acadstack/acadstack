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
