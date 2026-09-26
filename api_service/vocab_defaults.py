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
plumbing not exposed anywhere as a pick-list -- those want real workflow
transition tables rather than a vocabulary list, which is its own piece
of work.

Each vocabulary is a list of ``{"code": ..., "label": ...}`` dicts (plus
extra keys where a vocabulary needs more than a label -- see GRADES'
``audit_ok``). Order is display order only; it has no semantic meaning.

``"reserved": True`` marks a code that Python, SQL or Vue code names
directly (branches on, filters by, or uses as a default). An institution
may relabel a reserved code but not delete or recode it: settings_store's
vocab validator refuses any list that drops one. This module is the
authority for which codes are reserved; the flag on a stored item must
match it. When code starts depending on a new code literal, mark it here.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__status__ = "Development"
"""

DEGREES = [
    {"code": "BTE", "label": "B.Tech", "reserved": True},
    {"code": "MTE", "label": "M.Tech"},
    {"code": "MSR", "label": "M.S (Research)"},
    {"code": "MSC", "label": "M.Sc"},
    {"code": "BMD", "label": "B.Tech-M.Tech Dual"},
    {"code": "PHD", "label": "PhD", "reserved": True},
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
    {"code": "STU", "label": "Student", "reserved": True},
    {"code": "ACA", "label": "Academic Section", "reserved": True},
    {"code": "FAC", "label": "Faculty", "reserved": True},
    {"code": "HOD", "label": "Head of Dept.", "reserved": True},
    {"code": "DEA", "label": "Dean of Academics", "reserved": True},
    {"code": "SUP", "label": "Superuser", "reserved": True},
    {"code": "GUE", "label": "Guest", "reserved": True},
    {"code": "PLA", "label": "Placement Cell", "reserved": True},
    {"code": "ADV", "label": "Advisor"},
    {"code": "RES", "label": "Research Section", "reserved": True},
]

COURSE_STATUSES = [
    {"code": "DRA", "label": "Draft", "reserved": True},
    {"code": "APP", "label": "Approved", "reserved": True},
    {"code": "HAP", "label": "HoD Approval Pending", "reserved": True},
    {"code": "HAR", "label": "HoD Rejected", "reserved": True},
    {"code": "CAP", "label": "Council Approval Pending", "reserved": True},
    {"code": "CAR", "label": "Council Rejected", "reserved": True},
    {"code": "RET", "label": "Retired"},
]

OFFERING_STATUSES = [
    {"code": "E", "label": "Enrolling", "reserved": True},
    {"code": "R", "label": "Running", "reserved": True},
    {"code": "F", "label": "Finished", "reserved": True},
    {"code": "P", "label": "Proposed", "reserved": True},
    {"code": "D", "label": "Declined", "reserved": True},
    {"code": "C", "label": "Canceled", "reserved": True},
]

ENROLMENT_STATUSES = [
    {"code": "IPEN", "label": "Pending Instructor Approval", "reserved": True},
    {"code": "IREJ", "label": "Instructor Rejected"},
    {"code": "APEN", "label": "Pending Advisor Approval", "reserved": True},
    {"code": "AREJ", "label": "Advisor Rejected"},
    {"code": "ENRO", "label": "Enrolled", "reserved": True},
    {"code": "DROP", "label": "Dropped by Student", "reserved": True},
    {"code": "ASREJ", "label": "Acadmic section Rejected", "reserved": True},
    {"code": "WDRAW", "label": "Withdrawn by Student", "reserved": True},
]

ENROLMENT_TYPES = [
    {"code": "A", "label": "Audit", "reserved": True},
    {"code": "C", "label": "Credit", "reserved": True},
    {"code": "CM", "label": "Credit for Minor", "reserved": True},
    {"code": "CC", "label": "Credit for Concent.", "reserved": True},
]

# audit_ok: whether the grade is a valid grade for an audited ('A')
# enrolment (replaces the separate VALID_AUDIT_GRADES list that used to
# live in common.py -- see settings_store.valid_audit_grade_codes()).
GRADES = [
    {"code": "NA", "label": "NA", "audit_ok": True, "reserved": True},
    {"code": "A", "label": "A", "audit_ok": False, "reserved": True},
    {"code": "A-", "label": "A-", "audit_ok": False, "reserved": True},
    {"code": "B", "label": "B", "audit_ok": False, "reserved": True},
    {"code": "B-", "label": "B-", "audit_ok": False, "reserved": True},
    {"code": "C", "label": "C", "audit_ok": False, "reserved": True},
    {"code": "C-", "label": "C-", "audit_ok": False, "reserved": True},
    {"code": "D", "label": "D", "audit_ok": False, "reserved": True},
    {"code": "E", "label": "E", "audit_ok": False, "reserved": True},
    {"code": "F", "label": "F", "audit_ok": False, "reserved": True},
    {"code": "NP", "label": "NP", "audit_ok": True, "reserved": True},
    {"code": "NF", "label": "NF", "audit_ok": True, "reserved": True},
    {"code": "I", "label": "I", "audit_ok": True, "reserved": True},
    {"code": "W", "label": "W", "audit_ok": True, "reserved": True},
    {"code": "S", "label": "S", "audit_ok": False, "reserved": True},
    {"code": "U", "label": "U", "audit_ok": False, "reserved": True},
]

ATTENDANCE_CODES = [
    {"code": "A", "label": "Absent", "reserved": True},
    {"code": "P", "label": "Present", "reserved": True},
    {"code": "L", "label": "On Leave"},
]

DC_ROLES = [
    {"code": "ME", "label": "Member", "reserved": True},
    {"code": "SU", "label": "Supervisor", "reserved": True},
    {"code": "CO", "label": "Co-Supervisor"},
    {"code": "CP", "label": "Chairperson", "reserved": True},
]

DC_STATUSES = [
    {"code": "DRA", "label": "Draft", "reserved": True},
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
    {"code": "ALL", "label": "All Departments", "reserved": True},
]

# Core vs elective (used by sql_statements.toml's dept_wise_course_load/
# core_courses_taught/electives_taught): SC/PC/GR/HC are core, SE/PE/HE/OC
# are elective; CP/CT/NN are neither. Not modeled as a field on each item
# below since only that hand-written SQL currently needs the grouping.
COURSE_TYPES = [
    {"code": "SC", "label": "Science Requirement Core", "reserved": True},
    {"code": "SE", "label": "Science Electives", "reserved": True},
    {"code": "GR", "label": "General Engineering Requirement", "reserved": True},
    {"code": "PC", "label": "Programme Core", "reserved": True},
    {"code": "PE", "label": "Programme Elective", "reserved": True},
    {"code": "HC", "label": "Humanities and Social Sciences core", "reserved": True},
    {"code": "HE", "label": "Humanities and Social Sciences Electives", "reserved": True},
    {"code": "CP", "label": "Capstone Projects"},
    {"code": "CT", "label": "Industrial Internship and Comprehensive Viva"},
    {"code": "NN", "label": "Extra-curricular"},
    {"code": "OC", "label": "Open Electives", "reserved": True},
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
    {"code": "A", "label": "Any Semester", "reserved": True},
]

FORM_TYPES = [
    {"code": "END_SEM_FB", "label": "End-semester feedback", "reserved": True},
    {"code": "MID_SEM_FB", "label": "Mid-semester feedback", "reserved": True},
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
    {"code": "DRA", "label": "Draft", "reserved": True},
    {"code": "RET", "label": "Returned to DC Member", "reserved": True},
    {"code": "SUB", "label": "Submitted to DC Chair", "reserved": True},
    {"code": "APP", "label": "Approved", "reserved": True},
]

STUDENT_STATUSES = [
    {"code": "REG", "label": "Registered", "reserved": True},
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

# Academic-calendar event codes: the keys AcademicCalendar.event_code
# takes (see models.py), matched against by domain.academic_calendar's
# is_today_between_events()/event_date(). AddAcademicDates.vue still has
# one fixed row per event rather than looping over this list, so the
# labels below aren't rendered anywhere yet -- declaring it as a
# vocabulary mainly makes the codes admin-visible/exportable like every
# other controlled list, and lets dates_save (api_wflow.py) reject an
# unknown code instead of silently storing it.
ACAD_EVENT_CODES = [
    {"code": "SESSION_S", "label": "Academic Session Start", "reserved": True},
    {"code": "SESSION_E", "label": "Academic Session End", "reserved": True},
    {"code": "COURSE_REG_S", "label": "Course Registration Start", "reserved": True},
    {"code": "COURSE_REG_E", "label": "Course Registration End", "reserved": True},
    {"code": "CLASSES_S", "label": "Classes Start", "reserved": True},
    {"code": "CLASSES_E", "label": "Classes End", "reserved": True},
    {"code": "ADD_DROP_S", "label": "Add/Drop Start", "reserved": True},
    {"code": "ADD_DROP_E", "label": "Add/Drop End", "reserved": True},
    {"code": "FEEDBACK_MID_S", "label": "Mid-Semester Feedback Start", "reserved": True},
    {"code": "FEEDBACK_MID_E", "label": "Mid-Semester Feedback End", "reserved": True},
    {"code": "MINOR_EXAM_S", "label": "Minor Exam Start", "reserved": True},
    {"code": "MINOR_EXAM_E", "label": "Minor Exam End", "reserved": True},
    {"code": "WITHDRAW_S", "label": "Withdraw Start", "reserved": True},
    {"code": "WITHDRAW_E", "label": "Withdraw End", "reserved": True},
    {"code": "MAJOR_EXAM_S", "label": "Major Exam Start", "reserved": True},
    {"code": "MAJOR_EXAM_E", "label": "Major Exam End", "reserved": True},
    {"code": "FEEDBACK_S", "label": "End-Semester Feedback Start", "reserved": True},
    {"code": "FEEDBACK_E", "label": "End-Semester Feedback End", "reserved": True},
    {"code": "GRADE_SUB_S", "label": "Grade Submission Start", "reserved": True},
    {"code": "GRADE_SUB_E", "label": "Grade Submission End", "reserved": True},
    {"code": "SHOW_MIDSEM_FB_S", "label": "Show Mid-Semester Feedback From", "reserved": True},
    {"code": "SHOW_ENDSEM_FB_S", "label": "Show End-Semester Feedback From", "reserved": True},
    {"code": "RESULT_DECLARATION", "label": "Result Declaration", "reserved": True},
]

# PhD (and other programme) milestone sequence: the codes an
# AcademicMilestone row records (domain/milestones.py). ``sequence`` orders
# them; ``applies_to`` is a degree code. DC_PROPOSED/DC_APPROVED are
# recorded by the doctoral-committee workflow's effects.
MILESTONES = [
    {"code": "JOINING", "label": "Joining", "sequence": 10, "applies_to": "PHD"},
    {"code": "DC_PROPOSED", "label": "DC Proposed", "sequence": 20, "applies_to": "PHD",
     "reserved": True},
    {"code": "DC_APPROVED", "label": "DC Approved", "sequence": 30, "applies_to": "PHD",
     "reserved": True},
    {"code": "COMPRE", "label": "Comprehensive Exam", "sequence": 40, "applies_to": "PHD"},
    {"code": "TP", "label": "TP", "sequence": 50, "applies_to": "PHD"},
    {"code": "OPEN_SEMINAR_1", "label": "Open Seminar 1", "sequence": 60, "applies_to": "PHD"},
    {"code": "OPEN_SEMINAR_2", "label": "Open Seminar 2", "sequence": 70, "applies_to": "PHD"},
    {"code": "SYNOPSIS", "label": "Synopsis", "sequence": 80, "applies_to": "PHD"},
    {"code": "THESIS_SUBMITTED", "label": "Thesis Submitted", "sequence": 90, "applies_to": "PHD"},
    {"code": "DEFENCE", "label": "Defence", "sequence": 100, "applies_to": "PHD"},
    {"code": "AWARDED", "label": "Degree Awarded", "sequence": 110, "applies_to": "PHD"},
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
    "acad_event_codes": ACAD_EVENT_CODES,
    "milestones": MILESTONES,
}

# Maps each vocabulary to the key it had in the old hand-maintained
# static_data.json, and whether that group carries a leading
# {"id": "", "value": "-Select-"} placeholder entry for dropdowns. Both
# are preserved exactly so api_common.static_data_dict() returns
# byte-for-byte the same shape the frontend (webapp/src/main.js's `SD`
# mixin) expects -- only where the data comes from changed, not what it
# looks like on the wire.
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
    "acad_event_codes": ("AcadEventCodes", False),
    "milestones": ("Milestones", False),
}


def codes(name: str) -> list:
    """Just the codes for one vocabulary, in declared order."""
    return [item["code"] for item in ALL[name]]


def choices(name: str) -> list:
    """(code, label) tuples for one vocabulary, ready for a peewee
    ``choices=`` field argument."""
    return [(item["code"], item["label"]) for item in ALL[name]]


def reserved_codes(name: str) -> set:
    """Codes of one vocabulary that code depends on (see module doc)."""
    return {item["code"] for item in ALL.get(name, []) if item.get("reserved")}
