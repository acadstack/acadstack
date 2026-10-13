"""Standard lists, slot timings and feedback forms common to IIT/NIT-type
institutes. A new installation has none of them; the superuser adds the ones
missing with /vocab_seed_defaults (Lists screen), and can then edit or hide them.
"""

# The lists, as (code, label) or (code, label, attrs) in display order.
DEFAULT_VOCAB = {
    "Departments": [
        ("ACA", "Academic Section"),
        ("CSE", "Computer Science and Engineering"),
        ("EE", "Electrical Engineering"),
        ("ECE", "Electronics and Communication Engineering"),
        ("ME", "Mechanical Engineering"),
        ("CE", "Civil Engineering"),
        ("CHE", "Chemical Engineering"),
        ("MME", "Metallurgical and Materials Engineering"),
        ("MA", "Mathematics"),
        ("PH", "Physics"),
        ("CY", "Chemistry"),
        ("HSS", "Humanities and Social Sciences"),
    ],
    "Degrees": [
        ("BTECH", "B.Tech", {"level": "UG", "printed_name": "Bachelor of Technology"}),
        ("BS", "B.S.", {"level": "UG", "printed_name": "Bachelor of Science"}),
        ("DD", "B.Tech-M.Tech Dual Degree", {"level": "UG", "printed_name": "Bachelor and Master of Technology (Dual Degree)"}),
        ("MTECH", "M.Tech", {"level": "PG", "printed_name": "Master of Technology"}),
        ("MSC", "M.Sc", {"level": "PG", "printed_name": "Master of Science"}),
        ("MS", "M.S. (Research)", {"level": "PG", "printed_name": "Master of Science (by Research)"}),
        ("MBA", "MBA", {"level": "PG", "printed_name": "Master of Business Administration"}),
        ("MCA", "MCA", {"level": "PG", "printed_name": "Master of Computer Applications"}),
        ("PHD", "PhD", {"level": "PHD", "printed_name": "Doctor of Philosophy"}),
    ],
    "CourseTypes": [
        ("BSC", "Basic Science Core", {"group": "CORE"}),
        ("ESC", "Engineering Science Core", {"group": "CORE"}),
        ("HSC", "Humanities and Social Sciences Core", {"group": "CORE"}),
        ("PC", "Programme Core", {"group": "CORE"}),
        ("PE", "Programme Elective", {"group": "ELECTIVE"}),
        ("OE", "Open Elective", {"group": "ELECTIVE"}),
        ("HSE", "Humanities and Social Sciences Elective", {"group": "ELECTIVE"}),
        ("PRJ", "Project"),
        ("INT", "Internship"),
        ("SEM", "Seminar"),
        ("NC", "Non-credit (NCC/NSS/NSO)"),
    ],
    "PersonCategories": [
        ("GEN", "General"),
        ("EWS", "Economically Weaker Section"),
        ("OBC", "OBC (Non-Creamy Layer)"),
        ("SC", "Scheduled Caste"),
        ("ST", "Scheduled Tribe"),
        ("PWD", "Person with Disability"),
    ],
    "DegreeType": [
        ("REG", "Regular"),
        ("HON", "Honours"),
        ("DWM", "Degree with Minor"),
    ],
    "CourseFreqs": [
        ("O", "Odd semester"),
        ("E", "Even semester"),
        ("S", "Summer term"),
        ("A", "Any semester"),
    ],
    "CourseSlots": [(s, f"Slot {s}") for s in "ABCDEFGH"]
                   + [(f"L{d}", f"Lab slot L{d}") for d in range(1, 6)],
    "CalendarEvents": [
        ("ORIENTATION", "Orientation programme"),
        ("INST_REG", "Semester registration and fee payment"),
        ("MIDSEM_BREAK", "Mid-semester break"),
    ],
}


def slot_timings():
    """(slot, week_day, start_time, end_time) of a weekly timetable without
    clashes: lecture slots A-H, three 50-minute hours each on different days
    between 8:00 and 12:50, and labs L1-L5 on Monday to Friday afternoons.
    week_day 0 is Monday."""
    lectures = "ABCDEFGH"
    rows = []
    for i in range(3 * len(lectures)):
        start = (8 + i % 5) * 100
        rows.append((lectures[i % len(lectures)], i // 5, start, start + 50))
    rows += [(f"L{d + 1}", d, 1400, 1650) for d in range(5)]
    return rows


LIKERT = ["Strongly agree", "Agree", "Neither agree nor disagree", "Disagree",
          "Strongly disagree"]

_QUESTIONS = [
    "The instructor explained the concepts clearly.",
    "The instructor came well prepared for the classes.",
    "The classes were held regularly and on time.",
    "The pace of the course was appropriate.",
    "The instructor addressed students' doubts and questions.",
    "The evaluation (quizzes, assignments, exams) was fair.",
    "The reference material and resources were useful.",
    "Overall, I am satisfied with the course.",
]

# form_type -> (form_name, [(question, ans_options, is_optional, is_text)])
FEEDBACK_FORMS = {
    "MID_SEM_FB": ("Mid-semester course feedback",
                   [(q, LIKERT, False, False) for q in _QUESTIONS]
                   + [("Any other comments or suggestions?", [], True, True)]),
    "END_SEM_FB": ("End-semester course feedback",
                   [(q, LIKERT, False, False) for q in _QUESTIONS]
                   + [("Any other comments or suggestions?", [], True, True)]),
}
