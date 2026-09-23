"""Academic policy, as data that domain functions receive.

The shape is: **frozen dataclasses of plain values, built by a ``load_*``
function at the edge and passed in as an argument.** Domain functions take
``policy=None`` and fall back to the loader, which keeps call sites short
while leaving every one of them injectable::

    compute_cgpa_sgpa_ec(courses, "PHD", policy=GradingPolicy(...))

The ``load_*`` functions are the only place in ``domain/`` allowed to read
ambient configuration (the policy store, the settings store, app config).
Everything below them takes values.

Grade rules are versioned, not configured
-----------------------------------------
Grading policy is effective-dated: a 2019 transcript must keep computing
under the 2019 rules forever. So the grade->point map, the earned-credit
and CGPA grade sets, the credit-bearing enrolment types, the LTP format
and the degree classification all live in ``policy_store`` as complete
rulesets keyed on the session they take effect from.
:func:`load_grading_policy` resolves the one in force for a session.

Nothing here branches on a year. The "PhD passing grades introduced in
2021" rule used to be an ``if year > 2021 / elif year < 2021 / else`` on
the academic session inside the computation loop; it is now
:data:`BASELINE_GRADING_VERSIONS`, an ordinary effective-dated table.

Programme classes, not a UG/PG/PhD enum
---------------------------------------
The computation used to ask ``if degree == "BTE"`` for the UG rules and
``elif degree == "PHD"`` for the PhD rules, with every other degree code
falling through to PG. Institutions use different codes, and a programme
can need its own rules for reasons that have nothing to do with degree
level, so a ruleset maps **degree code -> programme class** and then
holds one rule block per class. Class names are arbitrary; unmapped
degrees take :attr:`GradingPolicy.default_degree_class`.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

import logging
from dataclasses import dataclass, field
from typing import Mapping, Optional, Sequence

import acad_session as AS
import policy_store as PS
import settings_store as ST

# ---------------------------------------------------------------- grading


@dataclass(frozen=True)
class ProgrammeRules:
    """The grade rules for one programme class (e.g. UG, PG, PHD).

    ``grade_points`` is complete here even when the stored ruleset left it
    to the institution-wide default: the builder resolves the override so
    the computation never has to ask which of two maps applies.
    """

    #: grade letter -> grade points.
    grade_points: Mapping[str, float]

    #: Grades that earn credit.
    earned_credit_grades: frozenset

    #: Grades whose points count towards CGPA. Narrower than
    #: ``earned_credit_grades``: a grade can earn credit without counting
    #: (e.g. "S", which carries no points and is netted out).
    cgpa_grades: frozenset


@dataclass(frozen=True)
class LtpFormat:
    """How a course's L-T-P-S-C string is read.

    Split out because the count of fields, and which one holds the credit
    value, are an institution's convention rather than a fact.
    """

    separator: str = "-"
    field_count: int = 5
    credits_index: int = 4

    #: Positions that must be present and non-empty for the data to be
    #: usable at all. Checked BEFORE ``field_count``, which is why a
    #: two-field string raises IndexError rather than a domain error --
    #: see the note in compute_cgpa_sgpa_ec.
    required_indices: Sequence[int] = (0, 2)

    #: Named in the error message when the field count is wrong.
    format_label: str = "L-T-P-S-C"


@dataclass(frozen=True)
class GradingPolicy:
    """One complete, effective-dated grading ruleset."""

    #: Institution-wide grade letter -> points. A programme class may
    #: override it wholesale; :meth:`rules_for` returns the effective one.
    grade_points: Mapping[str, float]

    #: degree code -> programme class name.
    degree_classes: Mapping[str, str]

    #: Class applied to any degree code not listed above.
    default_degree_class: str

    #: programme class name -> :class:`ProgrammeRules`.
    programme_rules: Mapping[str, ProgrammeRules]

    #: Enrolment types that count as credit (as opposed to audit).
    credit_enrol_types: Sequence[str] = ("C", "CM", "CC")

    #: How an enrolment type is matched against the set above.
    #:
    #: ``"exact"`` is correct. ``"substring"`` reproduces a long-standing
    #: quirk: the rule used to be ``enrol_type in "C,CM,CC"``, i.e. a
    #: substring test on a joined string, so a stray one-character code
    #: like "M" counted as a credit enrolment because "M" appears inside
    #: "CM". Of the real enrolment types (A, C, CM, CC) none is affected,
    #: so the two modes agree on all valid data --
    #: ``tests/test_gpa_computation.py`` characterises the quirk on
    #: invalid data, which is why the default preserves it.
    #:
    #: Because this field is versioned, an institution can switch to
    #: ``"exact"`` effective from an open session without altering a
    #: single historical transcript.
    credit_enrol_type_match: str = "substring"

    #: Only enrolments in this status are counted.
    counted_enrol_status: str = "ENRO"

    #: Satisfactory grade: earns credit, carries no points, and is netted
    #: out of both GPA denominators.
    satisfactory_grade: str = "S"

    #: Grades removed from the SGPA denominator entirely, as though the
    #: course had not been registered for.
    excluded_grades: frozenset = frozenset(("U", "I", "W"))

    #: Grades that make a course "passed" for the passed-courses listing
    #: (prerequisite checking).
    #:
    #: Deliberately NOT derived from ``cgpa_grades``, though it currently
    #: equals the UG set plus "S". Two reasons: "S" is a pass but cannot
    #: be a CGPA grade (no points, netted out of the denominator), and
    #: ``cgpa_grades`` is per programme class while this listing is not --
    #: deriving it would silently stop a PhD student's "D" counting as a
    #: pass, since the PhD class excludes "D" from CGPA.
    passed_course_grades: frozenset = frozenset(
        ("A", "A-", "B", "B-", "C", "C-", "D", "S"))

    #: How a course's credit value is read out of its LTP string.
    ltp: LtpFormat = field(default_factory=LtpFormat)

    #: Decimal places SGPA and CGPA are rounded to.
    gpa_decimal_places: int = 2

    def class_for(self, degree: str) -> str:
        """The programme class a degree code belongs to."""
        return self.degree_classes.get(degree, self.default_degree_class)

    def rules_for(self, degree: str) -> ProgrammeRules:
        """The grade rules for a student's degree.

        Raises:
            KeyError: if the degree maps to a class the ruleset does not
                define. That is a broken ruleset, not bad input, and it is
                rejected at write time by
                :func:`validate_grading_payload`.
        """
        return self.programme_rules[self.class_for(degree)]

    def is_credit_enrol_type(self, enrol_type: str) -> bool:
        """Whether this enrolment type earns credit (see
        :attr:`credit_enrol_type_match`)."""
        if self.credit_enrol_type_match == "exact":
            return enrol_type in self.credit_enrol_types
        return enrol_type in ",".join(self.credit_enrol_types)

    def round_gpa(self, value: float) -> float:
        return round(value, self.gpa_decimal_places)


# ------------------------------------------------- the shipped baseline

#: The grade point scale.
_GRADE_POINTS = {"A": 10, "A-": 9, "B": 8, "B-": 7, "C": 6, "C-": 5,
                 "D": 4, "E": 2, "F": 0}

#: Which degree codes classify as what. BMD (B.Tech-M.Tech Dual) is
#: deliberately NOT listed: it classified as PG while the computation
#: hardcoded ``degree == "BTE"`` for the UG case, and it still does.
_DEGREE_CLASSES = {"BTE": "UG", "PHD": "PHD"}

_UG_EC = frozenset(("A", "A-", "B", "B-", "C", "C-", "D", "S", "NP"))
_PG_EC = frozenset(("A", "A-", "B", "B-", "C", "C-", "D", "S"))
_UG_PG_CGPA = frozenset(("A", "A-", "B", "B-", "C", "C-", "D"))

# PhD grade sets. Narrower than UG/PG: "D" earns neither credit nor CGPA
# points for a research student.
_PHD_EC = frozenset(("A", "A-", "B", "B-", "C", "C-"))
_PHD_CGPA = frozenset(("A", "A-", "B", "B-", "C", "C-"))


#: The session the seeded baseline takes effect from. Early enough to
#: precede any enrolment, so every transcript resolves to it.
BASELINE_EFFECTIVE_FROM = "2000-T1"

#: The ruleset the product ships with, and the one
#: :func:`default_seed_data.seed_grading_policy` stores at install.
#:
#: There is exactly one, and it is not session-dependent. An earlier
#: revision of this module carried the PhD grade sets as a table keyed per
#: academic calendar, to reproduce a rule that switched on the session
#: suffix ("PhD passing grades introduced in 2021"). That rule was
#: incoherent -- read as one institution-wide series it demanded different
#: rulesets for sessions beginning in the same month -- and it described a
#: transition in a deployment that no longer needs preserving. So the
#: shipped rules are simply the rules, and any future amendment is a new
#: stored version rather than a branch or a table.
DEFAULT_GRADING_POLICY = GradingPolicy(
    grade_points=_GRADE_POINTS,
    degree_classes=_DEGREE_CLASSES,
    default_degree_class="PG",
    programme_rules={
        "UG": ProgrammeRules(_GRADE_POINTS, _UG_EC, _UG_PG_CGPA),
        "PG": ProgrammeRules(_GRADE_POINTS, _PG_EC, _UG_PG_CGPA),
        "PHD": ProgrammeRules(_GRADE_POINTS, _PHD_EC, _PHD_CGPA),
    },
)


def baseline_grading_policy() -> GradingPolicy:
    """The shipped in-code ruleset.

    Used when nothing is stored, which keeps the computation testable with
    no database. Takes no session: the shipped rules do not vary by one.
    """
    return DEFAULT_GRADING_POLICY


def load_grading_policy(acad_session: Optional[str] = None) -> GradingPolicy:
    """The grading ruleset in force for an academic session.

    Prefers the stored, versioned ruleset and falls back to the shipped
    baseline when none is recorded -- which is the state of a fresh
    install, and lets the computation be tested with no database at all.

    A stored ruleset that cannot be resolved for an otherwise valid reason
    (nothing recorded yet, a session before the earliest version) falls
    back rather than failing: refusing to produce a transcript because an
    admin has not seeded policy would be worse than computing under the
    rules the code ships with. A stored ruleset that exists but is corrupt
    still raises, because that is not a fallback situation.
    """
    if acad_session is not None:
        try:
            return PS.policy_for(GRADING, acad_session)
        except PS.PolicyNotFoundError:
            pass
        except AS.InvalidAcadSession:
            logging.warning(
                f"Unknown academic session: {acad_session!r}. Computing under "
                f"the ruleset the code ships with.")
    return baseline_grading_policy()


# ------------------------------------------- storage for the grading group

#: Name of the versioned grading policy group (see policy_store.py).
GRADING = "grading"

_SET_KEYS = ("excluded_grades", "passed_course_grades", "credit_enrol_types")
_RULE_SET_KEYS = ("earned_credit_grades", "cgpa_grades")

_REQUIRED = ("grade_points", "degree_classes", "default_degree_class",
             "programme_rules", "counted_enrol_status", "satisfactory_grade"
             ) + _SET_KEYS

_MATCH_MODES = ("exact", "substring")


def grading_payload_from(policy: GradingPolicy, **overrides) -> dict:
    """A storable payload for one version of the grading rules.

    ``overrides`` replaces top-level keys after the fact, which is how a
    caller states the one thing a new version changes without restating
    the ruleset (the stored row is still complete -- this is an authoring
    convenience, not a patch mechanism).
    """
    def items(value):
        return sorted(value) if isinstance(value, (set, frozenset)) \
            else list(value)

    payload = {
        "grade_points": dict(policy.grade_points),
        "degree_classes": dict(policy.degree_classes),
        "default_degree_class": policy.default_degree_class,
        "programme_rules": {
            name: {
                "earned_credit_grades": items(rules.earned_credit_grades),
                "cgpa_grades": items(rules.cgpa_grades),
                # Only stored when it differs from the institution-wide
                # map, so a reader can see at a glance which programmes
                # depart from the common scale.
                **({"grade_points": dict(rules.grade_points)}
                   if dict(rules.grade_points) != dict(policy.grade_points)
                   else {}),
            }
            for name, rules in policy.programme_rules.items()
        },
        "credit_enrol_types": items(policy.credit_enrol_types),
        "credit_enrol_type_match": policy.credit_enrol_type_match,
        "counted_enrol_status": policy.counted_enrol_status,
        "satisfactory_grade": policy.satisfactory_grade,
        "excluded_grades": items(policy.excluded_grades),
        "passed_course_grades": items(policy.passed_course_grades),
        "ltp": {
            "separator": policy.ltp.separator,
            "field_count": policy.ltp.field_count,
            "credits_index": policy.ltp.credits_index,
            "required_indices": list(policy.ltp.required_indices),
            "format_label": policy.ltp.format_label,
        },
        "gpa_decimal_places": policy.gpa_decimal_places,
    }
    payload.update(overrides)
    return payload


def build_grading_policy(payload) -> GradingPolicy:
    """Stored payload -> :class:`GradingPolicy`.

    Grade sets become real frozensets here. Storage has always used JSON
    arrays; the computation used to join them into comma-separated strings
    and match with ``in``, i.e. substring matching. That was checked
    against the whole grade vocabulary before the change: for every one of
    the 16 recognised grades, substring and membership agree, so the
    conversion is behaviour-preserving. The one place it was not is
    enrolment types, which keeps an explicit match mode (see
    :attr:`GradingPolicy.credit_enrol_type_match`).
    """
    missing = [k for k in _REQUIRED if k not in payload]
    if missing:
        raise ValueError(f"missing key(s): {', '.join(sorted(missing))}")

    grade_points = {str(k): v for k, v in payload["grade_points"].items()}

    rules = {}
    for name, block in payload["programme_rules"].items():
        block_missing = [k for k in _RULE_SET_KEYS if k not in block]
        if block_missing:
            raise ValueError(
                f"programme_rules[{name!r}] is missing "
                f"{', '.join(sorted(block_missing))}")
        own_points = block.get("grade_points")
        rules[str(name)] = ProgrammeRules(
            grade_points=({str(k): v for k, v in own_points.items()}
                          if own_points else grade_points),
            earned_credit_grades=frozenset(block["earned_credit_grades"]),
            cgpa_grades=frozenset(block["cgpa_grades"]))

    ltp = payload.get("ltp") or {}
    return GradingPolicy(
        grade_points=grade_points,
        degree_classes={str(k): str(v)
                        for k, v in payload["degree_classes"].items()},
        default_degree_class=str(payload["default_degree_class"]),
        programme_rules=rules,
        credit_enrol_types=tuple(payload["credit_enrol_types"]),
        credit_enrol_type_match=str(
            payload.get("credit_enrol_type_match", "substring")),
        counted_enrol_status=str(payload["counted_enrol_status"]),
        satisfactory_grade=str(payload["satisfactory_grade"]),
        excluded_grades=frozenset(payload["excluded_grades"]),
        passed_course_grades=frozenset(payload["passed_course_grades"]),
        ltp=LtpFormat(
            separator=str(ltp.get("separator", "-")),
            field_count=int(ltp.get("field_count", 5)),
            credits_index=int(ltp.get("credits_index", 4)),
            required_indices=tuple(ltp.get("required_indices", (0, 2))),
            format_label=str(ltp.get("format_label", "L-T-P-S-C"))),
        gpa_decimal_places=int(payload.get("gpa_decimal_places", 2)),
    )


def validate_grading_payload(payload):
    """Structural checks beyond what the builder enforces. Deliberately
    does not police WHICH grades an institution recognises: that is
    exactly the kind of rule that legitimately changes between
    versions."""
    errors = []

    # Reported here as well as by the builder, which raises on the first
    # missing key and so never reaches the rest. The store's contract is
    # that one rejection lists every problem, so an admin fixing a ruleset
    # is not made to discover them one at a time.
    for key in _REQUIRED:
        if key not in payload:
            errors.append(f"{key} is required")

    points = payload.get("grade_points")
    if points is None:
        pass  # already reported as missing above
    elif not isinstance(points, Mapping) or not points:
        errors.append("grade_points must be a non-empty object")
    else:
        for grade, value in points.items():
            if not isinstance(grade, str) or not grade.strip():
                errors.append(f"grade_points has a blank grade key: {grade!r}")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                errors.append(f"grade_points[{grade!r}] must be a number, "
                              f"got {value!r}")

    def check_set(key, items, where=""):
        if isinstance(items, str) or not isinstance(items, (list, tuple)):
            errors.append(f"{where}{key} must be an array of codes, not a "
                          f"{type(items).__name__} -- the comma-separated "
                          f"strings used in code are not accepted here")
            return
        if any(not isinstance(i, str) or not i.strip() for i in items):
            errors.append(f"{where}{key} must contain only non-empty strings")
        if len(set(items)) != len(items):
            errors.append(f"{where}{key} contains duplicate entries")

    for key in _SET_KEYS:
        if payload.get(key) is not None:
            check_set(key, payload[key])

    rules = payload.get("programme_rules")
    if not isinstance(rules, Mapping) or not rules:
        errors.append("programme_rules must be a non-empty object mapping a "
                      "programme class to its grade rules")
        rules = {}
    for name, block in rules.items():
        where = f"programme_rules[{name!r}]."
        if not isinstance(block, Mapping):
            errors.append(f"programme_rules[{name!r}] must be an object")
            continue
        for key in _RULE_SET_KEYS:
            if key not in block:
                errors.append(f"{where}{key} is required")
            elif block[key] is not None:
                check_set(key, block[key], where)

    # Every class a degree maps to, and the default, must actually exist --
    # otherwise a student of that degree gets a KeyError at transcript time
    # rather than an error when the ruleset was stored.
    classes = payload.get("degree_classes")
    default = payload.get("default_degree_class")
    if not isinstance(classes, Mapping):
        errors.append("degree_classes must be an object mapping a degree "
                      "code to a programme class name")
    else:
        for degree, cls in classes.items():
            if cls not in rules:
                errors.append(
                    f"degree_classes[{degree!r}] is {cls!r}, which has no "
                    f"entry in programme_rules (have: "
                    f"{', '.join(sorted(map(str, rules))) or 'none'})")
    if default is not None and default not in rules:
        errors.append(f"default_degree_class {default!r} has no entry in "
                      f"programme_rules -- every degree code not listed in "
                      f"degree_classes would fail")

    mode = payload.get("credit_enrol_type_match")
    if mode is not None and mode not in _MATCH_MODES:
        errors.append(f"credit_enrol_type_match must be one of "
                      f"{', '.join(_MATCH_MODES)}, got {mode!r}")

    for key in ("counted_enrol_status", "satisfactory_grade",
                "default_degree_class"):
        value = payload.get(key)
        if value is not None and (not isinstance(value, str)
                                  or not value.strip()):
            errors.append(f"{key} must be a non-empty string")

    ltp = payload.get("ltp")
    if ltp is not None:
        if not isinstance(ltp, Mapping):
            errors.append("ltp must be an object")
        else:
            count = ltp.get("field_count")
            index = ltp.get("credits_index")
            if isinstance(count, int) and isinstance(index, int) \
                    and not (-count <= index < count):
                errors.append(f"ltp.credits_index {index} is outside a "
                              f"{count}-field LTP string")
            for i in ltp.get("required_indices") or ():
                if isinstance(count, int) and isinstance(i, int) \
                        and not (-count <= i < count):
                    errors.append(f"ltp.required_indices contains {i}, which "
                                  f"is outside a {count}-field LTP string")

    places = payload.get("gpa_decimal_places")
    if places is not None and (isinstance(places, bool)
                               or not isinstance(places, int)
                               or places < 0):
        errors.append(f"gpa_decimal_places must be a non-negative integer, "
                      f"got {places!r}")

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
    """The STORED grading ruleset in force for ``acad_session``.

    Unlike :func:`load_grading_policy` this does not fall back to the
    shipped baseline, so it is the call to use when you need to know what
    is actually recorded.

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
