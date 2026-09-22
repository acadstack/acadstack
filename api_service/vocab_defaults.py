"""Canonical bootstrap values for every controlled vocabulary in AcadStack
(degrees, roles, course/offering/enrolment statuses, enrolment types,
grades, attendance codes, DC roles/statuses, departments, course types,
course slots, and the smaller lookup lists that used to live only in
static_data.json).

This module is the SINGLE SOURCE these values are typed into. Everything
else derives from it instead of restating the list by hand:

- models.py builds its ``choices=`` tuples from here (needed at class
  definition / import time, before any DB connection exists -- see
  create_schema()/demo_data.py -- so it cannot query the DB-backed
  values below).
- settings_store.py registers one Spec per vocabulary under the "vocab"
  group, using the matching list here as the Spec's ``default``.
- default_seed_data.py seeds a SystemSetting row per vocabulary from the
  same lists, so a fresh or upgraded install has them in the DB without
  an institution's own customizations ever being overwritten (the seeder
  only inserts rows that are missing).
- demo_data.py and api_common.py's static_data_dict() both read the
  EFFECTIVE (DB-overridden) values via settings_store.vocab(), which
  falls back to these defaults when nothing is stored yet.

Deliberately excluded (out of scope for this consolidation): course-slot
DAY/TIME mappings (CourseSlotTiming, an already-genuine DB table, not a
static list), and status/code vocabularies that are pure workflow
plumbing not exposed anywhere as a pick-list (see docs/refactor-plan.md
Phase 9 for turning those into real transition tables).

Each vocabulary is a list of ``{"code": ..., "label": ...}`` dicts (plus
extra keys where a vocabulary needs more than a label -- see GRADES'
``audit_ok``). Order is display order only; it has no semantic meaning.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

DEGREES = [
    {"code": "BTE", "label": "B.Tech"},
    {"code": "MTE", "label": "M.Tech"},
    {"code": "MSR", "label": "M.S (Research)"},
    {"code": "MSC", "label": "M.Sc"},
    {"code": "BMD", "label": "B.Tech-M.Tech Dual"},
    {"code": "PHD", "label": "PhD"},
    {"code": "MCS_AI", "label": "M.Tech(AI)"},
    {"code": "MEE_SIGNAL", "label": "M.Tech(Signal Processing)"},
    {"code": "MEE_MICRO", "label": "M.Tech(Micro. & VLSI)"},
    {"code": "MEE_POWER", "label": "M.Tech(Power Engg.)"},
    {"code": "MME_THERM", "label": "M.Tech(Thermal Engg.)"},
    {"code": "MME_MANUF", "label": "M.Tech(Manufacturing)"},
    {"code": "MCE_MECHA", "label": "M.Tech(Mechanics And Design)"},
    # The following used to exist ONLY in static_data.json (never in
    # models.py's DEGREES, never used by demo_data.py, never referenced
    # anywhere else in the repo): BTE_MC, MCE_WATER, MCE_STRUC, MME_MCPMC,
    # JEE_PREP, ADD_INTRN. Confirmed unused and dropped as stale entries
    # rather than promoted to canonical -- reintroduce them here (with a
    # matching demo_data.py update) if an institution actually needs them.
]

ROLES = [
    {"code": "STU", "label": "Student"},
    {"code": "ACA", "label": "Academic Section"},
    {"code": "FAC", "label": "Faculty"},
    {"code": "HOD", "label": "Head of Dept."},
    {"code": "DEA", "label": "Dean of Academics"},
    {"code": "SUP", "label": "Superuser"},
    {"code": "GUE", "label": "Guest"},
    {"code": "PLA", "label": "Placement Cell"},
    {"code": "ADV", "label": "Advisor"},
    {"code": "RES", "label": "Research Section"},
]

COURSE_STATUSES = [
    {"code": "DRA", "label": "Draft"},
    {"code": "APP", "label": "Approved"},
    {"code": "HAP", "label": "HoD Approval Pending"},
    {"code": "HAR", "label": "HoD Rejected"},
    {"code": "CAP", "label": "Council Approval Pending"},
    {"code": "CAR", "label": "Council Rejected"},
    {"code": "RET", "label": "Retired"},
]

OFFERING_STATUSES = [
    {"code": "E", "label": "Enrolling"},
    {"code": "R", "label": "Running"},
    {"code": "F", "label": "Finished"},
    {"code": "P", "label": "Proposed"},
    {"code": "D", "label": "Declined"},
    {"code": "C", "label": "Canceled"},
]

ENROLMENT_STATUSES = [
    {"code": "IPEN", "label": "Pending Instructor Approval"},
    {"code": "IREJ", "label": "Instructor Rejected"},
    {"code": "APEN", "label": "Pending Advisor Approval"},
    {"code": "AREJ", "label": "Advisor Rejected"},
    {"code": "ENRO", "label": "Enrolled"},
    {"code": "DROP", "label": "Dropped by Student"},
    {"code": "ASREJ", "label": "Acadmic section Rejected"},
    {"code": "WDRAW", "label": "Withdrawn by Student"},
]

ENROLMENT_TYPES = [
    {"code": "A", "label": "Audit"},
    {"code": "C", "label": "Credit"},
    {"code": "CM", "label": "Credit for Minor"},
    {"code": "CC", "label": "Credit for Concent."},
]

# audit_ok: whether the grade is a valid grade for an audited ('A')
# enrolment (replaces the separate VALID_AUDIT_GRADES list that used to
# live in common.py -- see settings_store.valid_audit_grade_codes()).
GRADES = [
    {"code": "NA", "label": "NA", "audit_ok": True},
    {"code": "A", "label": "A", "audit_ok": False},
    {"code": "A-", "label": "A-", "audit_ok": False},
    {"code": "B", "label": "B", "audit_ok": False},
    {"code": "B-", "label": "B-", "audit_ok": False},
    {"code": "C", "label": "C", "audit_ok": False},
    {"code": "C-", "label": "C-", "audit_ok": False},
    {"code": "D", "label": "D", "audit_ok": False},
    {"code": "E", "label": "E", "audit_ok": False},
    {"code": "F", "label": "F", "audit_ok": False},
    {"code": "NP", "label": "NP", "audit_ok": True},
    {"code": "NF", "label": "NF", "audit_ok": True},
    {"code": "I", "label": "I", "audit_ok": True},
    {"code": "W", "label": "W", "audit_ok": True},
    {"code": "S", "label": "S", "audit_ok": False},
    {"code": "U", "label": "U", "audit_ok": False},
]

ATTENDANCE_CODES = [
    {"code": "A", "label": "Absent"},
    {"code": "P", "label": "Present"},
    {"code": "L", "label": "On Leave"},
]

DC_ROLES = [
    {"code": "ME", "label": "Member"},
    {"code": "SU", "label": "Supervisor"},
    {"code": "CO", "label": "Co-Supervisor"},
    {"code": "CP", "label": "Chairperson"},
]

DC_STATUSES = [
    {"code": "DRA", "label": "Draft"},
    {"code": "SUB", "label": "Submitted to HoD"},
    {"code": "FTD", "label": "Forwarded to Dean"},
    {"code": "RTS", "label": "Returned to Supervisor"},
    {"code": "APP", "label": "Approved"},
    {"code": "RTH", "label": "Returned to HoD"},
    {"code": "DEL", "label": "Deleted"},
]

DEPARTMENTS = [
    {"code": "ACA", "label": "Academic Section"},
    {"code": "EST", "label": "Establishment Section"},
    {"code": "CSE", "label": "Computer Science and Engineering"},
    {"code": "AIL", "label": "Artificial Intelligence"},
    {"code": "CEE", "label": "Center for Engineering Education"},
    {"code": "CIV", "label": "Civil Engineering"},
    {"code": "CHE", "label": "Chemical Engineering"},
    {"code": "ELE", "label": "Electrical Engineering"},
    {"code": "MEC", "label": "Mechanical Engineering"},
    {"code": "BIO", "label": "Biomedical Engineering"},
    {"code": "MET", "label": "Metallurgical and Materials Engineering"},
    {"code": "MTH", "label": "Mathematics"},
    {"code": "PHY", "label": "Physics"},
    {"code": "CHY", "label": "Chemistry"},
    {"code": "HSS", "label": "Humanities and Social Sciences"},
    {"code": "CARD", "label": "Centre for Applied Research in Data Science"},
    {"code": "PREP", "label": "Preparatory Dept."},
    {"code": "ALL", "label": "All Departments"},
]

COURSE_TYPES = [
    {"code": "SC", "label": "Science Requirement Core"},
    {"code": "SE", "label": "Science Electives"},
    {"code": "GR", "label": "General Engineering Requirement"},
    {"code": "PC", "label": "Programme Core"},
    {"code": "PE", "label": "Programme Elective"},
    {"code": "HC", "label": "Humanities and Social Sciences core"},
    {"code": "HE", "label": "Humanities and Social Sciences Electives"},
    {"code": "CP", "label": "Capstone Projects"},
    {"code": "CT", "label": "Industrial Internship and Comprehensive Viva"},
    {"code": "NN", "label": "Extra-curricular"},
    {"code": "OC", "label": "Open Electives"},
]

COURSE_SLOTS = [
    {"code": "S", "label": "Seminars or a core course (one hour per week)"},
    {"code": "PC1", "label": "PC1: Core of 1-2 year B.Tech"},
    {"code": "PC2", "label": "PC2: Core of 1-2 year B.Tech"},
    {"code": "PC3", "label": "PC3: Core of 1-2 year B.Tech"},
    {"code": "PC4", "label": "PC4: Core of 1-2 year B.Tech"},
    {"code": "PCE1", "label": "PCE1: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech"},
    {"code": "PCE2", "label": "PCE2: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech"},
    {"code": "PCE3", "label": "PCE3: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech"},
    {"code": "PCPE", "label": "Program core/elec for 3-4 year B.Tech"},
    {"code": "HSPE", "label": "HSS elec or Program core/elec for 3-4 year B.Tech"},
    {"code": "PCDE", "label": "HSS elec or dept core/elec for 3-4 year B.Tech"},
    {"code": "PEOE", "label": "Program elec or open elec for 3-4 year B.Tech"},
    {"code": "HSME", "label": "HSS or Science or Math elec 3rd and/or 4th year B.Tech"},
    {"code": "LC", "label": "Lab Courses"},
    {"code": "PHSME", "label": "Buffer slot"},
]

COURSE_FREQS = [
    {"code": "E", "label": "Even Semester"},
    {"code": "O", "label": "Odd Semester"},
    {"code": "S", "label": "Summer break"},
    {"code": "A", "label": "Any Semester"},
]

FORM_TYPES = [
    {"code": "END_SEM_FB", "label": "End-semester feedback"},
    {"code": "MID_SEM_FB", "label": "Mid-semester feedback"},
]

PERSON_CATEGORIES = [
    {"code": "GEN", "label": "General"},
    {"code": "SC", "label": "Scheduled Caste"},
    {"code": "ST", "label": "Scheduled Tribe"},
    {"code": "OBC", "label": "OBC"},
    {"code": "EWS", "label": "Economically Weaker Section"},
    {"code": "PWD", "label": "PWD"},
    {"code": "OTH", "label": "Others"},
]

DEGREE_TYPES = [
    {"code": "REG", "label": "Regular"},
    {"code": "HON", "label": "Honors"},
    {"code": "DWM", "label": "Degree With Minor"},
    {"code": "DWC", "label": "Degree Wtih Concentration"},
]

PPR_STATUSES = [
    {"code": "DRA", "label": "Draft"},
    {"code": "RET", "label": "Returned to DC Member"},
    {"code": "SUB", "label": "Submitted to DC Chair"},
    {"code": "APP", "label": "Approved"},
]

STUDENT_STATUSES = [
    {"code": "REG", "label": "Registered"},
    {"code": "WTH", "label": "Withdrawan"},
    {"code": "MDL", "label": "Medical/Semster Break"},
]

# static_data.json's MinorConcSpecialization had MECE defined TWICE with
# different labels ("...Electronics & Communication Engineering" and
# "...English and Creative Expression") and CTCS defined twice with the
# same label. Resolved per product decision: MECE keeps the Electronics &
# Communication Engineering meaning; the English/Creative Expression minor
# is recoded to MENG (a new, previously-unused code) rather than dropped;
# the CTCS duplicate is just removed.
MINOR_CONC_SPECIALIZATIONS = [
    {"code": "MCBME", "label": "Minor in Biomedical Engineering"},
    {"code": "MCHY", "label": "Minor in Chemistry"},
    {"code": "MCSE", "label": "Minor in Computer Science and Engineering"},
    {"code": "MELE", "label": "Minor in Electrical Engineering"},
    {"code": "MECE", "label": "Minor in Electronics & Communication Engineering"},
    {"code": "MMEC", "label": "Minor in Mechanical Engineering"},
    {"code": "MMTH", "label": "Minor in Mathematics"},
    {"code": "MPHY", "label": "Minor in Physics"},
    {"code": "MQUE", "label": "Minor in Quantum Engineering"},
    {"code": "MCGS", "label": "Minor in Cognitive Science"},
    {"code": "MENG", "label": "Minor in English and Creative Expression"},
    {"code": "MCME", "label": "Minor in in Computational Mechanics"},
    {"code": "CSTR", "label": "Concentration in Structures"},
    {"code": "CMVL", "label": "Concentration in Micro-electronics and VLSI Design"},
    {"code": "CTHF", "label": "Concentration in Thermal and Fluids"},
    {"code": "CMNF", "label": "Concentration in Manufacturing"},
    {"code": "CMED", "label": "Concentration in Mechanics and Design"},
    {"code": "CAIL", "label": "Concentration in Artificial Intelligence"},
    {"code": "CVIP", "label": "Concentration in Computer Vision and Image Processing"},
    {"code": "CAES", "label": "Concentration in Architecture and Embedded Systems"},
    {"code": "CTCS", "label": "Concentration in Theoretical Computer Science"},
    {"code": "CMAM", "label": "Concentration in Mathematical Modelling"},
    {"code": "CAMT", "label": "Concentration in Advanced Mathematics"},
    {"code": "CCME", "label": "Concentration in Computational Mechanics"},
]

# ===================== Registry =====================

# Every vocabulary, keyed by the name used in "vocab.<name>" setting keys.
ALL = {
    "degrees": DEGREES,
    "roles": ROLES,
    "course_statuses": COURSE_STATUSES,
    "offering_statuses": OFFERING_STATUSES,
    "enrolment_statuses": ENROLMENT_STATUSES,
    "enrolment_types": ENROLMENT_TYPES,
    "grades": GRADES,
    "attendance_codes": ATTENDANCE_CODES,
    "dc_roles": DC_ROLES,
    "dc_statuses": DC_STATUSES,
    "departments": DEPARTMENTS,
    "course_types": COURSE_TYPES,
    "course_slots": COURSE_SLOTS,
    "course_freqs": COURSE_FREQS,
    "form_types": FORM_TYPES,
    "person_categories": PERSON_CATEGORIES,
    "degree_types": DEGREE_TYPES,
    "ppr_statuses": PPR_STATUSES,
    "student_statuses": STUDENT_STATUSES,
    "minor_conc_specializations": MINOR_CONC_SPECIALIZATIONS,
}

# Maps each vocabulary to the key it used to have in the hand-maintained
# static_data.json, and whether that group used to carry a leading
# {"id": "", "value": "-Select-"} placeholder entry for dropdowns. Both
# are preserved exactly so api_common.static_data_dict() keeps returning
# byte-for-byte the same shape the frontend (webapp/src/main.js's `SD`
# mixin) already expects -- this refactor changes where the data comes
# from, not what it looks like on the wire.
STATIC_DATA_KEYS = {
    "course_statuses": ("CourseStatuses", True),
    "course_types": ("CourseTypes", True),
    "course_freqs": ("CourseFreqs", True),
    "offering_statuses": ("OfferingStatuses", True),
    "grades": ("CourseGrades", True),
    "enrolment_types": ("EnrolTypes", True),
    "enrolment_statuses": ("EnrolStatuses", True),
    "attendance_codes": ("AttendCodes", True),
    "departments": ("Departments", True),
    "roles": ("UserRoles", True),
    "degrees": ("Degrees", True),
    "course_slots": ("CourseSlots", True),
    "form_types": ("FormTypes", False),
    "person_categories": ("PersonCategories", False),
    "degree_types": ("DegreeType", False),
    "dc_roles": ("DcRoles", False),
    "dc_statuses": ("DcStatuses", False),
    "ppr_statuses": ("PPRStatuses", False),
    "minor_conc_specializations": ("MinorConcSpecialization", True),
    "student_statuses": ("StudentStatus", False),
}


def codes(name: str) -> list:
    """Just the codes for one vocabulary, in declared order."""
    return [item["code"] for item in ALL[name]]


def choices(name: str) -> list:
    """(code, label) tuples for one vocabulary, ready for a peewee
    ``choices=`` field argument."""
    return [(item["code"], item["label"]) for item in ALL[name]]
