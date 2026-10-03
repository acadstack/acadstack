"""Adds demo data for the application.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import argparse
import itertools
import json
import random
import secrets
import psycopg2 as pg
from psycopg2 import sql

from datetime import timedelta

import common as C
import migrate
import models as M
import settings as ST
import api_reports as R

static_data = C.static_data_json()


ENROL_TYPES = [entry.get('id') for entry in static_data.get('EnrolTypes', []) if entry.get('id')][1:]
ENROL_STATUSES = [entry.get('id') for entry in static_data.get('EnrolStatuses', []) if entry.get('id')][1:]
CO_STATUSES = [entry.get('id') for entry in static_data.get('OfferingStatuses', []) if entry.get('id')][1:]

# Filled from the VocabItem table once the schema exists.
DEPTS, DEGREES, DEG_SPL, COURSE_CAT, DEG_TYPES, PERSON_CAT, SLOTS = [], [], [], [], [], [], []

# The university's lists, as (code, label) or (code, label, attrs) in display
# order.
VOCAB_SEED = {
    "Departments": [
        ("ACA", "Academic Section"),
        ("EST", "Establishment Section"),
        ("CSE", "Computer Science and Engineering"),
        ("AIL", "Artificial Intelligence"),
        ("CEE", "Center for Engineering Education"),
        ("CIV", "Civil Engineering"),
        ("CHE", "Chemical Engineering"),
        ("ELE", "Electrical Engineering"),
        ("MEC", "Mechanical Engineering"),
        ("BIO", "Biomedical Engineering"),
        ("MET", "Metallurgical and Materials Engineering"),
        ("MTH", "Mathematics"),
        ("PHY", "Physics"),
        ("CHY", "Chemistry"),
        ("HSS", "Humanities and Social Sciences"),
        ("CARD", "Centre for Applied Research in Data Science"),
        ("PREP", "Preparatory Dept."),
    ],
    "Degrees": [
        ("BTE", "B.Tech", {"level": "UG", "printed_name": "Bachelor of Technology"}),
        ("BTE_MC", "B.Tech(M&C)", {"level": "UG", "printed_name": "Bachelor of Technology"}),
        ("MTE", "M.Tech", {"level": "PG", "printed_name": "Master of Technology"}),
        ("MCS_AI", "M.Tech(AI)", {"level": "PG", "printed_name": "Master of Technology"}),
        ("MCE_WATER", "M.Tech(Water Reso. & Envirn.)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Water Resources and Environment"}),
        ("MCE_STRUC", "M.Tech(Struc. and Geomech.)", {"level": "PG", "printed_name": "Master of Technology"}),
        ("MEE_SIGNAL", "M.Tech(Signal Processing)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Communication & Signal Processing"}),
        ("MEE_MICRO", "M.Tech(Micro. & VLSI)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Microelectronics & VLSI Design"}),
        ("MEE_POWER", "M.Tech(Power Engg.)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Power Engineering"}),
        ("MME_THERM", "M.Tech(Thermal Engg.)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Thermal & Fluids Engineering"}),
        ("MME_MANUF", "M.Tech(Manufacturing)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Manufacturing Engineering"}),
        ("MCE_MECHA", "M.Tech(Mechanics And Design)", {"level": "PG", "printed_name": "Master of Technology", "specialisation": "Specialization in Mechanics & Design"}),
        ("MME_MCPMC", "M.Tech(Computational Mechanics)", {"level": "PG", "printed_name": "Master of Technology"}),
        ("MSR", "M.S (Research)", {"level": "PG", "printed_name": "Master of Science"}),
        ("MSC", "M.Sc", {"level": "PG", "printed_name": "Master of Science"}),
        ("BMD", "B.Tech-M.Tech Dual", {"level": "UG", "printed_name": "Master of Technology"}),
        ("JEE_PREP", "JEE Preparatory", {"level": "UG"}),
        ("ADD_INTRN", "Additional Internship", {"level": "UG", "printed_name": "Bachelor of Technology", "specialisation": "Additional Internship"}),
        ("PHD", "PhD", {"level": "PHD", "printed_name": "Doctor of Philosophy"}),
    ],
    "CourseSlots": [
        ("S", "Seminars or a core course (one hour per week)"),
        ("PC1", "PC1: Core of 1-2 year B.Tech"),
        ("PC2", "PC2: Core of 1-2 year B.Tech"),
        ("PC3", "PC3: Core of 1-2 year B.Tech"),
        ("PC4", "PC4: Core of 1-2 year B.Tech"),
        ("PCE1", "PCE1: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech"),
        ("PCE2", "PCE2: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech"),
        ("PCE3", "PCE3: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech"),
        ("PCPE", "Program core/elec for 3-4 year B.Tech"),
        ("HSPE", "HSS elec or Program core/elec for 3-4 year B.Tech"),
        ("PCDE", "HSS elec or dept core/elec for 3-4 year B.Tech"),
        ("PEOE", "Program elec or open elec for 3-4 year B.Tech"),
        ("HSME", "HSS or Science or Math elec 3rd and/or 4th year B.Tech"),
        ("LC", "Lab Courses"),
        ("PHSME", "Buffer slot"),
    ],
    "CourseTypes": [
        ("SC", "Science Requirement Core", {"group": "CORE"}),
        ("SE", "Science Electives", {"group": "ELECTIVE"}),
        ("GR", "General Engineering Requirement", {"group": "CORE"}),
        ("PC", "Programme Core", {"group": "CORE"}),
        ("PE", "Programme Elective", {"group": "ELECTIVE"}),
        ("HC", "Humanities and Social Sciences core", {"group": "CORE"}),
        ("HE", "Humanities and Social Sciences Electives", {"group": "ELECTIVE"}),
        ("CP", "Capstone Projects"),
        ("CT", "Industrial Internship and Comprehensive Viva"),
        ("NN", "Extra-curricular"),
        ("OC", "Open Electives", {"group": "ELECTIVE"}),
    ],
    "MinorConcSpecialization": [
        ("MCBME", "Minor in Biomedical Engineering"),
        ("MCHY", "Minor in Chemistry"),
        ("MCSE", "Minor in Computer Science and Engineering"),
        ("MELE", "Minor in Electrical Engineering"),
        ("MECE", "Minor in Electronics & Communication Engineering"),
        ("MMEC", "Minor in Mechanical Engineering"),
        ("MMTH", "Minor in Mathematics"),
        ("MPHY", "Minor in Physics"),
        ("MQUE", "Minor in Quantum Engineering"),
        ("MCGS", "Minor in Cognitive Science"),
        ("MENG", "Minor in English and Creative Expression"),
        ("MCME", "Minor in in Computational Mechanics"),
        ("CSTR", "Concentration in Structures"),
        ("CMVL", "Concentration in Micro-electronics and VLSI Design"),
        ("CTHF", "Concentration in Thermal and Fluids"),
        ("CMNF", "Concentration in Manufacturing"),
        ("CMED", "Concentration in Mechanics and Design"),
        ("CAIL", "Concentration in Artificial Intelligence"),
        ("CVIP", "Concentration in Computer Vision and Image Processing"),
        ("CAES", "Concentration in Architecture and Embedded Systems"),
        ("CTCS", "Concentration in Theoretical Computer Science"),
        ("CMAM", "Concentration in Mathematical Modelling"),
        ("CAMT", "Concentration in Advanced Mathematics"),
        ("CCME", "Concentration in Computational Mechanics"),
    ],
    "PersonCategories": [
        ("GEN", "General"),
        ("SC", "Scheduled Caste"),
        ("ST", "Scheduled Tribe"),
        ("OBC", "OBC"),
        ("EWS", "Economically Weaker Section"),
        ("PWD", "PWD"),
        ("OTH", "Others"),
    ],
    "DegreeType": [
        ("REG", "Regular"),
        ("HON", "Honors"),
        ("DWM", "Degree With Minor"),
        ("DWC", "Degree Wtih Concentration"),
    ],
    "CourseFreqs": [
        ("E", "Even Semester"),
        ("O", "Odd Semester"),
        ("S", "Summer break"),
        ("A", "Any Semester"),
    ],
}

current_year = C.DT.now().year
ACAD_YEARS = [str(year) for year in range(current_year - 5, current_year + 1)]
ACAD_SESS = [f"{year}-{term}" for year in ACAD_YEARS for term in ("I", "II")]
ENTRY_YEARS = [str(year) for year in range(current_year - 7, current_year)]

def recreate_db(config):
    db_args = config["db_args"]
    db_name = config["db_name"]
    
    # Connect to PostgreSQL without specifying the database
    conn = pg.connect(dbname='postgres', **db_args)
    conn.autocommit = True
    cur = conn.cursor()
    
    print(f"Dropping the schema: {db_name}")
    sql1 = """SELECT pg_terminate_backend(pg_stat_activity.pid)
              FROM pg_stat_activity WHERE datname = %s
              AND pid <> pg_backend_pid();"""
    cur.execute(sql1, (db_name,))
    cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
    
    print(f"Creating the schema: {db_name}")
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
    
    cur.close()
    conn.close()

    C.db.init(db_name, **db_args)
    print(f"Database '{db_name}' initialized.")

    migrate.migrate()
    print("Created DB tables.")


GRADES = [g["grade"] for g in ST.ten_point_scheme("UG")["grades"]]


def _seed_vocab():
    for vocab, items in VOCAB_SEED.items():
        for idx, (code, label, *attrs) in enumerate(items):
            M.VocabItem.create(vocab=vocab, code=code, label=label, sort_order=idx + 1,
                               attrs=attrs[0] if attrs else {})


def _vocab_codes(vocab):
    rows = M.VocabItem.select().where(M.VocabItem.vocab == vocab) \
        .order_by(M.VocabItem.sort_order, M.VocabItem.id)
    return [r.code for r in rows]


def setup_db_with_demo_data(config):
    print("========== Setting up DEMO database ==========")
    recreate_db(config)
    _seed_vocab()
    ST.save("institute_name", "Indian Institute of Technology Ropar")
    ST.save("institute_place", "Rupnagar")
    global DEPTS, DEGREES, DEG_SPL, COURSE_CAT, DEG_TYPES, PERSON_CAT, SLOTS
    # ALL (from the baseline migration) is for course categories, not people.
    DEPTS = [d for d in _vocab_codes("Departments") if d != "ALL"]
    DEGREES = _vocab_codes("Degrees")
    DEG_SPL = _vocab_codes("MinorConcSpecialization")
    COURSE_CAT = _vocab_codes("CourseTypes")
    DEG_TYPES = _vocab_codes("DegreeType")
    PERSON_CAT = _vocab_codes("PersonCategories")
    SLOTS = _vocab_codes("CourseSlots")
    _create_acad_sessions()
    _create_users()
    _create_courses()
    # The latest session that has started is open; later ones get no offerings.
    open_sess = M.AcademicCalendar.select().where(
        (M.AcademicCalendar.event_code == "SESSION_S")
        & (M.AcademicCalendar.event_value <= C.DT.now().date().isoformat())) \
        .order_by(M.AcademicCalendar.event_value.desc()).first().acad_session
    for acs in ACAD_SESS[:ACAD_SESS.index(open_sess) + 1]:
        _create_offerings(acs, open_sess)
        # Generate grades data
        R.__process_credits_gen_request(acs)

    print("Done adding demo data.")


def setup_prod_db(config):
    print("========== Setting up PRODUCTION database ==========")
    # Never drops anything: applies pending migrations and, on an empty
    # database, creates the superuser and prints its credentials.
    C.db.init(config["db_name"], **config["db_args"])
    migrate.migrate()


def _create_users():
    print("Creating users...")
    f_names = ["Aman", "Bikram", "Ashish", "Suman", "Sanjay", "Krishna",
               "Murali", "Aditya", "Vikram", "Subodh", "Pranav", "Atul", "Gurjot",
               "Amartiya", "Suhasini", "Hema", "Kiran"]
    l_names = ["Singh", "Aggrawal", "Kumar", "Sharma", "Verma", "Gupta", "Goyal", "Garg",
               "Subramaniyam", "Gill", "Maan", "Paul", "Bragta", "Josaph", "Narayanan", "Aulakh", "Saini"]
    
    all_users = list(itertools.product(f_names, l_names))
    random.shuffle(all_users)
    all_users.append(("ACAD", "USER"))
    for idx, item in enumerate(all_users):
        dept = secrets.choice(DEPTS)
        num = str(idx + 1).zfill(4)
        if idx < 2:         # Two deans
            role = "DEA"
        elif idx < 4:       # Next 2 are academic staff
            role = "ACA"
        elif idx < 10:      # Next 6 are HODs
            role = "HOD"
        elif idx < 50:      # Next 40 are faculty
            role = "FAC"
        else:               # Rest are students
            role = "STU"

        if ".".join(item).lower() == "acad.user":
            role = "ACA"

        p = M.Person(org_id="{0}{1}".format(dept, num), dept_name=dept)
        p.year_of_entry = random.choice(ENTRY_YEARS)
        p.category = random.choice(PERSON_CAT)
        p.dept_name = random.choice(DEPTS)
        p.degree = random.choice(DEGREES)
        p.deg_type = random.choice(DEG_TYPES)
        p.deg_type_spec = random.choice(DEG_SPL)
        if role == "STU":
            # Student lookup and bulk enrolment find only Registered students.
            p.current_status = "REG"
        p.save()
        u = M.User()
        u.login_id = ".".join(item).lower()
        u.password_hashed = C.hash_password("abcd1234")
        u.first_name, u.last_name = item
        u.email = "{0}@{1}.com".format(item[0], item[1])
        u.person = p
        u.role = role
        u.save()

    print(f"Added {len(all_users)} users. Password for each user is: abcd1234")


def _create_courses():
    print("Creating courses...")
    # Code,Title,Type,LTP
    courses = ["GE103,Introduction to computing,GE,3-0-2-7-4",
               "GE104,INTRODUCTION TO ELECTRICAL ENGINEERING,GE,3-2-2-7-4",
               "GE105,ENGINEERING DRAWING,GE,3-0-4-7-4",
               "GE109,INTRODUCTIONTO ENGINEERING PRODUCTS,GE,3-0-2-7-4",
               "BM451,FUNDAMENTALS OF BIOLOGY FOR ENGINEERS,PC,3-0-2-7-4",
               "CH101,INTRODUCTION TO CHEMICAL ENGINEERING,PC,3-1-0-5-3",
               "CH201,CHEMICAL ENGINEERING THERMODYNAMICS,PC,3-1-0-5-3",
               "CH202,TRANSPORT PHENOMENA,PC,3-1-0-5-3",
               "CH203,HEAT AND MASS TRANSFER,PE,3-1-0-5-3",
               "CY101,CHEMISTRY FOR ENGINEERS,PE,3-1-2-6-4",
               "CY230,INTRODUCTION TO ORGANIC CHEMISTRY AND BIOCHEMISTRY,PC,3-1-0-5-3",
               "CE201,STRENGTH OF MATERIALS,PC,2-1-2-4-3",
               "CE202,FUNDAMENTALS OF FLUID MECHANICS,PE,2-3-0-3-2",
               "CS101,DISCRETE MATHEMATICAL STRUCTURES,PE,3-0-2-7-4",
               "CS201,DATA STRUCTURES,PC,3-1-2-6-4",
               "CS202,PROGRAMMING PARADIGMS AND PRAGMATICS,PC,3-1-2-6-4",
               "CS203,DIGITALLOGICDESIGN,PC,3-1-2-6-4",
               "CS204,COMPUTER ARCHITECTURE,PC,3-1-2-6-4",
               "EE201,SIGNALS AND SYSTEMS,PC,3-1-0-5-3",
               "EE301,ANALOG CIRCUITS,PC,3-1-0-5-3",
               "EE207,CONTROL ENGINEERING,PC,3-1-0-5-3",
               "HS102,ENGLISH LANGUAGE SKILLS,PC,2-3-2-3-6",
               "HS201,ECONOMICS,PC,3-1-0-5-3",
               "MA202,PROBABILITY AND STATISTICS,PC,3-1-0-5-3",
               "PH101,PHYSICS FOR ENGINEERS,PE,3-1-0-5-3",
               "ME101,ENGINEERING MECHANICS,PC,3-1-0-5-3",
               "ME102,THERMODYNAMICS,PC,3-1-0-5-3",
               "ME201,SOLID MECHANICS,PC,3-1-0-5-3",
               "CS503,MACHINE LEARNING,PE,3-0-2-7-4",
               "EE677,DIGITAL SIGNAL PROCESSING,PE,3-0-2-7-4",
               ]
    # Courses not meant for UG students only
    levels = {"CS503": "PG", "EE677": "PG", "HS102": "ALL"}
    n = len(courses)
    facs = list(M.User.select().where(M.User.role == "FAC"))
    for idx, c in enumerate(courses):
        cou = M.Course()
        cou.code, cou.title, cou.course_type, cou.ltp = c.split(",")
        cou.level = levels.get(cou.code, "UG")
        if idx % 10 == 0:
            cou.status = random.choice(["CAP", "HAP", "CAR", "HAR", "DRA"])
        else:
            cou.status = "APP"
        cou.author = random.choice(facs)
        cou.save()

    print("Added {} courses.".format(len(courses)))

def _save_acad_cal(sem, evt, yr, mmdd):
    acs = M.AcademicCalendar()
    acs.acad_session = f"{yr}-{sem}"
    acs.event_code = f"{evt}"
    # The second semester of an academic year runs in the next calendar year.
    acs.event_value = f"{int(yr) + 1 if sem == 'II' else yr}-{mmdd}"
    acs.save()

def _create_acad_sessions():
    print("Created academic sessions")
    ACAD_EVENTS = ['SESSION','COURSE_REG','CLASSES','ADD_DROP','WITHDRAW',
          'FEEDBACK_MID','MINOR_EXAM','SHOW_MIDSEM_FB','FEEDBACK','MAJOR_EXAM',
          'GRADE_SUB','RESULT_DECLARATION','SHOW_ENDSEM_FB']
    DATES_MMDD_I = [('07-24','12-25'), ('07-25', '08-01'), ('07-25', '11-20'),
                    ('08-16', '08-30'), ('09-01', '09-06'), ('09-24', '09-30'),
                    ('10-01', '10-10'), ('10-12', '10-12'), ('11-11', '11-16'),
                    ('11-17', '11-27'), ('11-18', '12-15'), ('12-20', '12-20'),
                    ('12-22', '12-22')]
    DATES_MMDD_II = [('01-24','06-25'), ('01-25', '02-01'), ('01-25', '05-20'),
                    ('02-16', '02-28'), ('03-01', '03-06'), ('03-24', '03-30'),
                    ('04-01', '04-10'), ('04-12', '04-12'), ('05-11', '05-16'),
                    ('05-17', '05-27'), ('05-18', '06-15'), ('06-20', '06-20'),
                    ('06-22', '06-22')]
    for yr in ACAD_YEARS:
        for sem in ("I", "II"):
            M.AcademicSession.create(code=f"{yr}-{sem}")
        for idx, ec in enumerate(ACAD_EVENTS):
            _save_acad_cal("I", f"{ec}_S", yr, DATES_MMDD_I[idx][0])
            _save_acad_cal("I", f"{ec}_E", yr, DATES_MMDD_I[idx][1])

            _save_acad_cal("II", f"{ec}_S", yr, DATES_MMDD_II[idx][0])
            _save_acad_cal("II", f"{ec}_E", yr, DATES_MMDD_II[idx][1])

def _create_offerings(acs, open_sess):
    print("Creating course offerings and enrolling students...")
    facs = list(M.User.select().where(M.User.role == "FAC"))
    stu = list(M.User.select().where(M.User.role == "STU"))
    stu_degrees = sorted({s.person.degree for s in stu})
    total = 60
    for idx, c in enumerate(M.Course.select().where(M.Course.status == "APP").limit(total)):
        coord = facs[idx]
        co = M.CourseOffering()
        co.course = c
        co.acad_session = acs
        co.dept_name = coord.person.dept_name  # offered by the coordinator's dept
        co.slot = random.choice(SLOTS)
        co.status = random.choice(CO_STATUSES)
        if acs != open_sess:
            co.status = "F" # Mark past courses as completed
        co.save()

        ci = M.CourseInstructor()
        ci.is_coordinator = True
        ci.offering = co
        ci.instructor = coord
        ci.save()

        # Enroll students
        if co.status in ["D", "P", "C"]:
            # Ignore registrations for declined, proposed and canceled COs
            continue
        sc = random.choice([25, 30, 40])
        lc = random.choice([5, 10])

        # Choose 4-5 course categorizations first, each covering all students
        # of one degree, and enrol only students they cover, so the lookup in
        # api_course_enrolment.py finds a category for every enrollment.
        degrees = random.sample(stu_degrees, random.choice([4, 5]))
        for degree in degrees:
            cc = M.CourseCategory()
            cc.category = random.choice(COURSE_CAT)
            cc.degree = degree
            cc.dept = "ALL"
            cc.for_entry_years = ",".join(ENTRY_YEARS)
            cc.offering = co
            cc.save()
        pool = [s for s in stu if s.person.degree in degrees]
        students_in_course = random.sample(pool, min(sc, len(pool)))

        for idx2, s in enumerate(students_in_course):
            ce = M.CourseEnrollment()
            ce.student = s
            ce.course_offering = co
            ce.enrol_type = "C"
            if idx2 % 10 == 0:
                ce.enrol_type = random.choice(ENROL_TYPES)
            ce.enrol_status = "ENRO"
            if idx2 % 8 == 0:
                ce.enrol_status = random.choice(ENROL_STATUSES)
            if acs != open_sess and ce.enrol_status == "ENRO":
                ce.grade = random.choice(GRADES)
            ce.save()
            if ce.enrol_status != "ENRO":
                # Ignore attendance for not enrolled students
                continue
            for i in range(lc):
                att = M.StudentAttendance()
                att.attend = "P"
                att.enrollment = ce
                att.attend_dt = C.DT.fromtimestamp(1500000000) + timedelta(days=i)
                att.save()

    print("Added {0} offerings, each with {1} students.".format(total, sc))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cfg_file_path", type=str,
                        help="Configuration file path.")
    args = parser.parse_args()
    with open(args.cfg_file_path, "r") as cfg_file:
        cfg = json.load(cfg_file)
        if "demo_data" in cfg and cfg["demo_data"]:
            setup_db_with_demo_data(cfg)
        else:
            setup_prod_db(cfg)
