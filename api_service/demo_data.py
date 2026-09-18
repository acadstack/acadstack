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
from passlib.handlers.pbkdf2 import pbkdf2_sha256

import common as C
import models as M
import api_reports as R
from default_seed_data import run_seed_defaults
from schema_migrations import run_pending_migrations

with open('static_data.json', 'r') as file:
    static_data = json.load(file)


DEPTS = [entry.get('id') for entry in static_data.get('Departments', []) if entry.get('id')][1:]
DEG_TYPES = [entry.get('id') for entry in static_data.get('DegreeType', []) if entry.get('id')][1:]
DEGREES = [entry.get('id') for entry in static_data.get('Degrees', []) if entry.get('id')][1:]
DEG_SPL = [entry.get('id') for entry in static_data.get('MinorConcSpecialization', []) if entry.get('id')][1:]
COURSE_CAT = [entry.get('id') for entry in static_data.get('CourseTypes', []) if entry.get('id')][1:]
PERSON_CAT = [entry.get('id') for entry in static_data.get('PersonCategories', []) if entry.get('id')][1:]
ENROL_TYPES = [entry.get('id') for entry in static_data.get('EnrolTypes', []) if entry.get('id')][1:]
ENROL_STATUSES = [entry.get('id') for entry in static_data.get('EnrolStatuses', []) if entry.get('id')][1:]
CO_STATUSES = [entry.get('id') for entry in static_data.get('OfferingStatuses', []) if entry.get('id')][1:]
GRADES = [entry.get('id') for entry in static_data.get('CourseGrades', []) if entry.get('id')][2:]

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
              FROM pg_stat_activity WHERE datname = 'acadstack_db'
              AND pid <> pg_backend_pid();"""
    cur.execute(sql.SQL(sql1))
    cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(db_name)))
    
    print(f"Creating the schema: {db_name}")
    cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
    
    cur.close()
    conn.close()

    C.db.init(db_name, **db_args)
    print(f"Database '{db_name}' initialized.")

    M.create_schema()
    print("Created DB tables.")

    run_pending_migrations()
    run_seed_defaults()
    print("Applied schema migrations and default seed data.")


def setup_db_with_demo_data(config):
    print("========== Setting up DEMO database ==========")
    recreate_db(config)    
    _create_acad_sessions()
    _create_users()
    _create_courses()
    for acs in ACAD_SESS:
        _create_offerings(acs)
        # Generate grades data
        R.__process_credits_gen_request(acs)

    print("Done adding demo data.")


def setup_prod_db(config):
    print("========== Setting up PRODUCTION database ==========")
    recreate_db(config)
    p = M.Person(org_id="acad.user", dept_name="ACA")
    p.save()
    u = M.User()
    u.login_id = "acad.user"
    u.role = "ACA"
    u.password_hashed = pbkdf2_sha256.hash("abcd1234")
    u.first_name, u.last_name = "Academic", "Section"
    u.email = "acad.user@iitrpr.ac.in"
    u.person = p
    u.save()
    print("!!!! Added the academic section user. Login: acad.user, password: abcd1234")

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
        p = M.Person(org_id="{0}{1}".format(dept, num), dept_name=dept)
        p.year_of_entry = random.choice(ENTRY_YEARS)
        p.category = random.choice(PERSON_CAT)
        p.dept_name = random.choice(DEPTS)
        p.degree = random.choice(DEGREES)
        p.deg_type = random.choice(DEG_TYPES)
        p.deg_type_spec = random.choice(DEG_SPL)
        p.save()
        u = M.User()
        u.login_id = ".".join(item).lower()
        u.password_hashed = pbkdf2_sha256.hash("abcd1234")
        u.first_name, u.last_name = item
        u.email = "{0}@{1}.com".format(item[0], item[1])
        u.person = p
        if idx < 2:         # Two deans
            u.role = "DEA"
        elif idx < 4:       # Next 2 are academic staff
            u.role = "ACA"
        elif idx < 10:      # Next 6 are HODs
            u.role = "HOD"
        elif idx < 50:      # Next 40 are faculty
            u.role = "FAC"
        else:               # Rest are students
            u.role = "STU"

        if u.login_id == "acad.user":
            u.role = "ACA"

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
               ]
    n = len(courses)
    facs = list(M.User.select().where(M.User.role == "FAC"))
    for idx, c in enumerate(courses):
        cou = M.Course()
        cou.code, cou.title, cou.course_type, cou.ltp = c.split(",")
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
    acs.event_value = f"{yr}-{mmdd}"
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
                    ('02-16', '02-30'), ('03-01', '03-06'), ('03-24', '03-30'),
                    ('04-01', '04-10'), ('04-12', '04-12'), ('05-11', '05-16'),
                    ('05-17', '05-27'), ('05-18', '06-15'), ('06-20', '06-20'),
                    ('06-22', '06-22')]
    for yr in ACAD_YEARS:
        for idx, ec in enumerate(ACAD_EVENTS):
            _save_acad_cal("I", f"{ec}_S", yr, DATES_MMDD_I[idx][0])
            _save_acad_cal("I", f"{ec}_E", yr, DATES_MMDD_I[idx][1])

            _save_acad_cal("II", f"{ec}_S", yr, DATES_MMDD_II[idx][0])
            _save_acad_cal("II", f"{ec}_E", yr, DATES_MMDD_II[idx][1])

def _create_offerings(acs):
    print("Creating course offerings and enrolling students...")
    facs = list(M.User.select().where(M.User.role == "FAC"))
    stu = list(M.User.select().where(M.User.role == "STU"))
    total = 60
    for idx, c in enumerate(M.Course.select().where(M.Course.status == "APP").limit(total)):
        co = M.CourseOffering()
        co.course = c
        co.acad_session = acs
        co.status = random.choice(CO_STATUSES)
        if acs != f"{current_year}-II":
            co.status = "F" # Mark past courses as completed
        co.save()

        cc = M.CourseCategory()
        cc.category = random.choice(COURSE_CAT)
        cc.degree = random.choice(DEGREES)
        cc.dept = random.choice(DEPTS)
        cc.for_entry_years = random.choice(ENTRY_YEARS)
        cc.offering = co
        cc.save()

        ci = M.CourseInstructor()
        ci.is_coordinator = True
        ci.offering = co
        ci.instructor = facs[idx]
        ci.save()

        # Enroll students
        if co.status in ["D", "P", "C"]:
            # Ignore registrations for declined, proposed and canceled COs
            continue
        sc = random.choice([25, 30, 40])
        lc = random.choice([5, 10])
        students_in_course = random.sample(stu, sc)
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
            if acs != f"{current_year}-II" and ce.enrol_status == "ENRO":
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
