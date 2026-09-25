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
and CGPA grade sets, the credit-bearing enrolment types, the excluded and
passing grades and the degree classification all live in ``policy_store``
as complete rulesets keyed on the session they take effect from.
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
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

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
class GradingPolicy:
    """One complete, effective-dated grading ruleset.

    Only rules an institution's Senate could actually amend belong here.
    Fixed codes the computation relies on (the "ENRO" status, the "S"
    grade) and the rounding are constants in ``domain/transcript.py``, and
    a course's credit value is ``Course.credits``, computed when the
    course is saved.
    """

    #: Institution-wide grade letter -> points. A programme class may
    #: override it wholesale; :meth:`rules_for` returns the effective one.
    grade_points: Mapping[str, float]

    #: degree code -> programme class name.
    degree_classes: Mapping[str, str]

    #: Class applied to any degree code not listed above.
    default_degree_class: str

    #: programme class name -> :class:`ProgrammeRules`.
    programme_rules: Mapping[str, ProgrammeRules]

    #: Enrolment types that count as credit (as opposed to audit),
    #: matched by exact membership.
    credit_enrol_types: frozenset = frozenset(("C", "CM", "CC"))

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


@dataclass(frozen=True)
class _Kind:
    """How one kind of payload value is checked, built and stored.

    ``check(value, where)`` returns a list of problems (empty when fine),
    each prefixed with ``where``, the value's path in the payload.
    """

    check: Callable[[Any, str], list]
    build: Callable[[Any], Any]
    dump: Callable[[Any], Any]


def _check_codes(value, where):
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        return [f"{where} must be an array of codes, not a "
                f"{type(value).__name__} -- a comma-separated string is not "
                f"accepted here"]
    if any(not isinstance(i, str) or not i.strip() for i in value):
        return [f"{where} must contain only non-empty strings"]
    if len(set(value)) != len(value):
        return [f"{where} contains duplicate entries"]
    return []


def _check_points(value, where):
    if not isinstance(value, Mapping) or not value:
        return [f"{where} must be a non-empty object"]
    errors = []
    for grade, points in value.items():
        if not isinstance(grade, str) or not grade.strip():
            errors.append(f"{where} has a blank grade key: {grade!r}")
        if isinstance(points, bool) or not isinstance(points, (int, float)):
            errors.append(f"{where}[{grade!r}] must be a number, got "
                          f"{points!r}")
    return errors


def _check_name(value, where):
    if not isinstance(value, str) or not value.strip():
        return [f"{where} must be a non-empty string"]
    return []


def _check_name_map(value, where):
    if not isinstance(value, Mapping):
        return [f"{where} must be an object mapping a degree code to a "
                f"programme class name"]
    return [e for k, v in value.items()
            for e in _check_name(v, f"{where}[{k!r}]")]


_CODES = _Kind(_check_codes, frozenset, sorted)
_POINTS = _Kind(_check_points,
                lambda v: {str(k): n for k, n in v.items()}, dict)
_NAME = _Kind(_check_name, str, str)
_NAME_MAP = _Kind(_check_name_map,
                  lambda v: {str(k): str(n) for k, n in v.items()}, dict)

#: The payload's flat top-level keys, each named as its GradingPolicy
#: field. ``programme_rules`` is nested and handled with
#: :data:`_RULE_FIELDS`.
_FIELDS = {
    "grade_points": _POINTS,
    "degree_classes": _NAME_MAP,
    "default_degree_class": _NAME,
    "credit_enrol_types": _CODES,
    "excluded_grades": _CODES,
    "passed_course_grades": _CODES,
}

#: The keys of one programme_rules block, each named as its
#: ProgrammeRules field. ``grade_points`` is optional there: a block
#: without one inherits the institution-wide map.
_RULE_FIELDS = {
    "earned_credit_grades": _CODES,
    "cgpa_grades": _CODES,
}


def _check_block(block, fields, where="", optional=None, nested=()):
    """Every problem with one payload object: missing, malformed and
    unrecognised keys. ``nested`` names keys the caller checks itself."""
    optional = optional or {}
    errors = []
    for key, kind in fields.items():
        if key not in block:
            errors.append(f"{where}{key} is required")
        else:
            errors.extend(kind.check(block[key], f"{where}{key}"))
    for key, kind in optional.items():
        if block.get(key) is not None:
            errors.extend(kind.check(block[key], f"{where}{key}"))
    known = set(fields) | set(optional) | set(nested)
    errors.extend(f"{where}{key} is not a grading policy field"
                  for key in sorted(map(str, block)) if key not in known)
    return errors


def grading_payload_from(policy: GradingPolicy, **overrides) -> dict:
    """A storable payload for one version of the grading rules.

    ``overrides`` replaces top-level keys after the fact, which is how a
    caller states the one thing a new version changes without restating
    the ruleset (the stored row is still complete -- this is an authoring
    convenience, not a patch mechanism).
    """
    payload = {key: kind.dump(getattr(policy, key))
               for key, kind in _FIELDS.items()}
    payload["programme_rules"] = {
        name: {
            **{key: kind.dump(getattr(rules, key))
               for key, kind in _RULE_FIELDS.items()},
            # Only stored when it differs from the institution-wide map,
            # so a reader can see at a glance which programmes depart
            # from the common scale.
            **({"grade_points": dict(rules.grade_points)}
               if dict(rules.grade_points) != dict(policy.grade_points)
               else {}),
        }
        for name, rules in policy.programme_rules.items()
    }
    payload.update(overrides)
    return payload


def build_grading_policy(payload) -> GradingPolicy:
    """Stored payload -> :class:`GradingPolicy`.

    Assumes a payload :func:`validate_grading_payload` accepted, which the
    store guarantees on write. Keys it does not know are ignored, so a
    version stored before a field was retired still builds.
    """
    top = {key: kind.build(payload[key]) for key, kind in _FIELDS.items()}
    rules = {
        str(name): ProgrammeRules(
            grade_points=(_POINTS.build(block["grade_points"])
                          if block.get("grade_points") is not None
                          else top["grade_points"]),
            **{key: kind.build(block[key])
               for key, kind in _RULE_FIELDS.items()})
        for name, block in payload["programme_rules"].items()
    }
    return GradingPolicy(programme_rules=rules, **top)


def validate_grading_payload(payload):
    """Every problem with a proposed ruleset, in one list -- the admin UI
    shows them together, so an admin fixing a ruleset is not made to
    discover them one at a time.

    Deliberately does not police WHICH grades an institution recognises:
    that is exactly the kind of rule that legitimately changes between
    versions.
    """
    errors = _check_block(payload, _FIELDS, nested=("programme_rules",))
    rules = payload.get("programme_rules")
    if not isinstance(rules, Mapping) or not rules:
        errors.append("programme_rules must be a non-empty object mapping a "
                      "programme class to its grade rules")
        rules = {}
    for name, block in rules.items():
        where = f"programme_rules[{name!r}]"
        if not isinstance(block, Mapping):
            errors.append(f"{where} must be an object")
        else:
            errors.extend(_check_block(block, _RULE_FIELDS, f"{where}.",
                                       optional={"grade_points": _POINTS}))

    # Every class a degree maps to, and the default, must actually exist --
    # otherwise a student of that degree gets a KeyError at transcript time
    # rather than an error when the ruleset was stored.
    classes = payload.get("degree_classes")
    if isinstance(classes, Mapping):
        for degree, cls in classes.items():
            if cls not in rules:
                errors.append(
                    f"degree_classes[{degree!r}] is {cls!r}, which has no "
                    f"entry in programme_rules (have: "
                    f"{', '.join(sorted(map(str, rules))) or 'none'})")
    default = payload.get("default_degree_class")
    if isinstance(default, str) and default not in rules:
        errors.append(f"default_degree_class {default!r} has no entry in "
                      f"programme_rules -- every degree code not listed in "
                      f"degree_classes would fail")
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
    """The one enrolment rule an institution configures. The status and
    type codes enrolment writes are fixed vocabulary codes, used inline in
    ``domain/enrolment.py``."""

    #: Skips the "semester fees paid" precondition for students.
    disable_fees_check: bool = False


def load_enrolment_policy() -> EnrolmentPolicy:
    """Reads the effective enrolment policy from the settings store.

    This is the only place in the enrolment domain that touches ambient
    configuration; everything downstream receives the resulting
    :class:`EnrolmentPolicy` as an argument.
    """
    return EnrolmentPolicy(
        disable_fees_check=ST.setting("enrolment.disable_fees_check"))
