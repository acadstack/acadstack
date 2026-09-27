"""Defines all the models used in this application.

__author__ = "Balwinder Sodhi"
__copyright__ = "Copyright 2025"
__license__ = "MIT"
__version__ = "0.1"
__status__ = "Development"
"""

import logging
from datetime import datetime as DT

import peewee as ORM
from playhouse.postgres_ext import JSONField
from playhouse.pool import PooledPostgresqlExtDatabase

# Deferred initialization
# db = ORM.PostgresqlDatabase(None)
db = PooledPostgresqlExtDatabase(None)

# List of degree programs
DEGREES = [
    ("BTE", "B.Tech"),
    ("MTE", "M.Tech"),
    ("MSR", "M.S (Research)"),
    ("MSC", "M.Sc"),
    ("BMD", "B.Tech-M.Tech Dual"),
    ("PHD", "PhD"),
    ("MCS_AI", "M.Tech(AI)"),
    ("MEE_SIGNAL", "M.Tech(Signal Processing)"),
    ("MEE_MICRO", "M.Tech(Micro. & VLSI)"),
    ("MEE_POWER", "M.Tech(Power Engg.)"),
    ("MME_THERM", "M.Tech(Thermal Engg.)"),
    ("MME_MANUF", "M.Tech(Manufacturing)"),
    ("MCE_MECHA", "M.Tech(Mechanics And Design)")
]


def create_schema():
    logging.info("Creating DB tables")
    with db:
        db.create_tables([User, KnownFace, Person, Course,
                          PasswordResetKey, CourseOffering,
                          CourseCategory, UserDoc,
                          CourseEnrollment, StudentAttendance,
                          CourseInstructor, WorkflowNote,
                          BatchAdvisors, AcademicCalendar,
                          FeedbackForm, FeedbackQuestion,
                          CourseInstructorFeedback,
                          StudentFeedbackStatus,
                          StudentSupervisor, CourseSlotTiming,
                          FeesTransaction, StudentCredits, DcForStudent,
                          DcMember, PhDProgressReport, AcademicMilestone,
                          AttendancePhoto, SystemSetting])
        logging.info("DB tables created.")


class BaseModel(ORM.Model):
    id = ORM.BigAutoField()
    is_deleted = ORM.BooleanField(default=False)
    txn_no = ORM.IntegerField(default=1, index=True)
    ins_ts = ORM.DateTimeField(default=DT.now)
    upd_ts = ORM.DateTimeField(default=DT.now)
    txn_login_id = ORM.CharField(max_length=40, null=True)

    class Meta:
        database = db
        only_save_dirty = True


class PasswordResetKey(BaseModel):
    login_id = ORM.CharField(max_length=40)
    prk = ORM.CharField(max_length=40)


class WorkflowNote(BaseModel):
    entity_key = ORM.IntegerField()
    entity_name = ORM.CharField(max_length=50)
    note = ORM.TextField(null=True)


class Person(BaseModel):
    """Can represent a student or employee of the institute.
    It is meant to hold the general profile information of
    the user.

    Args:
        BaseModel (BaseModel): Extends the base model
    """
    # Roll No. for the student, employee ID for others
    org_id = ORM.CharField(max_length=40, unique=True)
    gender = ORM.FixedCharField(max_length=1, null=True)

    # Dept. code defined in static_data.json
    dept_name = ORM.CharField(max_length=10)
    year_of_entry = ORM.CharField(max_length=4, null=True)  # yyyy
    degree = ORM.CharField(max_length=20, choices=DEGREES, null=True)
    category = ORM.CharField(max_length=10, null=True) # SC, ST, OBC, EWS, GEN, PWD
    deg_type = ORM.CharField(max_length=10, null=True) # REG, DWM, DWC
    deg_type_spec = ORM.CharField(max_length=10, null=True)
    current_status = ORM.CharField(max_length=10, null=True) # REG, WTH, MDL

    def get_degree_label(self):
        return dict(self.DEGREES)[self.degree]


class User(BaseModel):
    login_id = ORM.CharField(max_length=40, unique=True)
    password_hashed = ORM.TextField()
    email = ORM.CharField(max_length=150, unique=True)
    first_name = ORM.CharField(max_length=100, null=True)
    last_name = ORM.CharField(max_length=100, null=True)
    is_locked = ORM.BooleanField(default=False)
    person = ORM.ForeignKeyField(Person, backref='users', unique=True, null=True)
    ROLES = [
        ("STU", 'Student'),
        ("ACA", 'Academic Section'),
        ("FAC", 'Faculty'),
        ("HOD", 'Head of Dept.'),
        ("DEA", 'Dean of Academics'),
        ("SUP", 'Superuser'),
        ("GUE", 'Guest'),
        ("PLA", 'Placement Cell'),
        ("ADV", 'Advisor'),
        ("RES", 'Research Section')
    ]
    role = ORM.CharField(max_length=4, choices=ROLES, default="GUE")

    def get_role_label(self):
        return dict(self.ROLES)[self.role]

    def get_full_name(self):
        return "{0} {1}".format(self.first_name, self.last_name)


class BatchAdvisors(BaseModel):
    user = ORM.ForeignKeyField(User, backref='batch_advisors')
    year_of_entry = ORM.CharField(max_length=4)  # yyyy
    for_degree = ORM.CharField(max_length=20)

    class Meta:
        indexes = (
            # Unique index
            (('user', 'year_of_entry', 'for_degree'), True),
        )


class AcademicCalendar(BaseModel):
    # In the format YYYY-S where S is: 'M' for Monsoon semester,
    # 'S' for Summer, 'W' for Winter semesters.
    acad_session = ORM.CharField(max_length=10)

    # Descriptions and codes defined in static_data.json
    # E.g., session start date, mid-sem exam start/end dates etc.
    event_code = ORM.CharField(max_length=100)
    event_value = ORM.TextField()

    # DATE, INT, TEXT, FLOAT
    # event_value_type = ORM.CharField(max_length=10)
    class Meta:
        indexes = (
            # Unique index
            (('acad_session', 'event_code'), True),
        )

    """
    acad_session | event_code | event_value_type | event_value
    2020-W      | SESS_START_DT | DATE | 2020-12-30
    2020-W      | SESS_END_DT | DATE | 2021-03-30
    2020-W      | MID_SEM_START_DT | DATE | 2021-01-24
    2020-W      | MIN_ATTEND_REQD | INT | 60
    """


class KnownFace(BaseModel):
    user = ORM.ForeignKeyField(User, backref='known_faces', null=True)

    # Face encoding (a vector) for the photo
    face_enc = ORM.TextField()

    # Photo file (a UUID string)
    photo = ORM.TextField()


class UserDoc(BaseModel):
    DOC_CATS = [
        ("STU", "Student documents"),
        ("ACA", "Academic information"),
        ("GEN", "General documents"),
        ("FEETXN", "Registration fees transaction")
    ]
    user = ORM.ForeignKeyField(User, backref='user_docs', null=True)
    category = ORM.CharField(max_length=20, default="GEN",
                         choices=DOC_CATS)
    description = ORM.TextField()
    file_name = ORM.TextField()
    # File name (a UUID string)
    doc = ORM.TextField()


# ====== Courses related models =========

class Course(BaseModel):
    COURSE_STATUSES = [
        ("DRA", "Draft"),
        ("APP", "Approved"),
        ("HAP", "HoD Approval Pending"),
        ("HAR", "HoD Rejected"),
        ("CAP", "Council Approval Pending"),
        ("CAR", "Council Rejected"),
        ("RET", "Retired")
    ]
    code = ORM.CharField(max_length=20, unique=True)
    title = ORM.CharField(max_length=200)
    ltp = ORM.CharField(max_length=40, null=True)

    status = ORM.CharField(max_length=4, default="DRA",
                       choices=COURSE_STATUSES)

    author = ORM.ForeignKeyField(User, null=True,
                             backref='authored_courses',
                             on_delete='SET NULL')

    # E: Even, O: Odd, S: Summer, A: Any
    freq = ORM.CharField(max_length=1, default="A")
    has_lab = ORM.BooleanField(default=False)

    # Can be course numbers or arbitrary text
    prereqs = ORM.CharField(max_length=200, null=True)

    objectives = ORM.TextField(null=True)
    req_visiting_fac = ORM.BooleanField(default=False)

    # Course numbers
    course_supersedes = ORM.CharField(max_length=100, null=True)
    course_overlaps = ORM.CharField(max_length=100, null=True)

    # JSON array true/false
    tkp = JSONField(default=[])
    # JSON array true/false
    tgap = JSONField(default=[])

    # JSON fields
    modules = JSONField(default=[])
    teaching = JSONField(default=[])
    learning = JSONField(default={})
    evaluation = JSONField(default={})
    ref_material = JSONField(default=[])

    def get_status_label(self):
        return dict(self.COURSE_STATUSES)[self.status]


class CourseOffering(BaseModel):
    CO_STATUSES = [
        ("E", "Enrolling"),
        ("R", "Running"),
        ("F", "Finished"),
        ("P", "Proposed"),
        ("D", "Declined"),
        ("C", "Canceled")
    ]
    # Academic session start date in which course is floated
    acad_session = ORM.CharField(max_length=10)
    course = ORM.ForeignKeyField(Course, backref='offerings',
                             null=True, on_delete='SET NULL')
    status = ORM.CharField(max_length=2, choices=CO_STATUSES,
                       default="E")
    slot = ORM.CharField(max_length=10, null=True)
    section = ORM.CharField(max_length=2, default="A")
    # Dept. code defined in static_data.json
    dept_name = ORM.CharField(max_length=10, null=True)

    def get_status_label(self):
        return dict(self.CO_STATUSES)[self.status]

    class Meta:
        indexes = (
            # Unique index
            (('course', 'acad_session', 'status', 'section', 'dept_name'), True),
        )


class CourseCategory(BaseModel):
    offering = ORM.ForeignKeyField(CourseOffering, null=True,
                               backref='course_categories',
                               on_delete='SET NULL')
    degree = ORM.CharField(max_length=20, choices=DEGREES, default="ALL")
    dept = ORM.CharField(max_length=4, null=True)
    category = ORM.CharField(max_length=4, null=True)
    for_entry_years = ORM.CharField(max_length=100, null=True)

    class Meta:
        indexes = (
            # Unique index
            (('offering', 'degree', 'dept', 'category'), True),
        )


class CourseInstructor(BaseModel):
    offering = ORM.ForeignKeyField(CourseOffering, null=True,
                               backref='instructors',
                               on_delete='SET NULL')
    instructor = ORM.ForeignKeyField(User, null=True,
                                 backref='course_instructors',
                                 on_delete='SET NULL')
    is_coordinator = ORM.BooleanField(default=False)

    class Meta:
        indexes = (
            # Unique index
            (('offering', 'instructor'), True),
        )


class CourseEnrollment(BaseModel):
    ENROL_STATUSES = [
        ("IPEN", 'Pending Instructor Approval'),
        ("IREJ", 'Instructor Rejected'),
        ("APEN", 'Pending Advisor Approval'),
        ("AREJ", 'Advisor Rejected'),
        ("ENRO", 'Enrolled'),
        ("DROP", 'Dropped by Student'),
        ("ASREJ", 'Acadmic section Rejected'),
        ("WDRAW", 'Withdrawn by Student')
    ]
    course_offering = ORM.ForeignKeyField(CourseOffering,
                                      backref='enrollments',
                                      on_delete='CASCADE')
    student = ORM.ForeignKeyField(User, backref='enrollments',
                              on_delete='CASCADE')
    # (C)redit, (A)udit, 
    # Credit for minor (CM), Credit for concentration (CC)
    enrol_type = ORM.CharField(max_length=20)
    enrol_status = ORM.CharField(max_length=10, choices=ENROL_STATUSES,
                             default="IPEN")
    grade = ORM.CharField(max_length=2, default="NA")
    current_score = ORM.FloatField(null=True)
    remarks = ORM.TextField(null=True)

    def get_status_label(self):
        return dict(self.ENROL_STATUSES)[self.enrol_status]

    class Meta:
        indexes = (
            # Unique index
            (('student', 'course_offering'), True),
        )


class StudentAttendance(BaseModel):
    ATT_STATUS = [
        ("A", 'Absent'),
        ("L", 'On Leave'),
        ("P", 'Present'),
    ]
    attend = ORM.CharField(max_length=2, choices=ATT_STATUS,
                       default="A")
    enrollment = ORM.ForeignKeyField(CourseEnrollment,
                                 backref="attendance",
                                 on_delete="CASCADE")
    attend_dt = ORM.DateField(default=DT.now)
    remarks = ORM.CharField(max_length=500, null=True)

    class Meta:
        indexes = (
            # Unique index
            (('enrollment', 'attend_dt'), True),
        )


class FeedbackForm(BaseModel):
    form_name = ORM.CharField(max_length=50)
    is_active = ORM.BooleanField(default=True)
    # END_SEM_FB or MID_SEM_FB
    form_type = ORM.CharField(max_length=45)

    class Meta:
        indexes = (
            # Unique index
            (('form_name', 'form_type', 'is_active'), True),
        )


class FeedbackQuestion(BaseModel):
    form = ORM.ForeignKeyField(FeedbackForm,
                           backref='form_questions',
                           on_delete='CASCADE')
    question = ORM.CharField(max_length=500)
    ans_options = JSONField(default=[], null=True)
    is_optional = ORM.BooleanField(default=False)
    is_multianswer = ORM.BooleanField(default=False)
    is_text = ORM.BooleanField(default=False)

    class Meta:
        indexes = (
            # Unique index
            (('form', 'question'), True),
        )


class CourseInstructorFeedback(BaseModel):
    instructor = ORM.ForeignKeyField(CourseInstructor,
                                 backref='instructor_feedbacks',
                                 on_delete='CASCADE')
    question = ORM.ForeignKeyField(FeedbackQuestion,
                               backref='instructor_feedbacks',
                               on_delete='CASCADE')
    feedback = ORM.TextField()
    # It will be a uuid string
    submission_id = ORM.CharField(max_length=40)

    # YYYY-S
    acad_session = ORM.CharField(max_length=10)
    # class Meta:
    #     indexes = (
    #         # Unique index
    #         (('instructor', 'submission_id', 'question'), True),
    #     )


class StudentFeedbackStatus(BaseModel):
    feedback_form = ORM.ForeignKeyField(FeedbackForm,
                                    backref='student_feedbacks',
                                    on_delete='CASCADE')
    course_instructor = ORM.ForeignKeyField(CourseInstructor,
                                        backref='student_feedbacks',
                                        on_delete='CASCADE')
    student = ORM.ForeignKeyField(CourseEnrollment,
                              backref='student_feedbacks',
                              on_delete='CASCADE')
    is_submitted = ORM.BooleanField()

    class Meta:
        indexes = (
            # Unique index
            (('course_instructor', 'student', 'feedback_form'), True),
        )


class StudentSupervisor(BaseModel):
    student = ORM.ForeignKeyField(User,
                              backref='user_students',
                              on_delete='CASCADE')
    supervisor = ORM.ForeignKeyField(User,
                                 backref='user_supervisors',
                                 on_delete='CASCADE')

    class Meta:
        indexes = (
            # Unique index
            (('student', 'supervisor'), True),
        )


class CourseSlotTiming(BaseModel):
    slot = ORM.CharField(max_length=40)
    week_day = ORM.SmallIntegerField()
    start_time = ORM.SmallIntegerField()
    end_time = ORM.SmallIntegerField()

    class Meta:
        indexes = (
            # Unique index
            (('slot', 'week_day', 'start_time'), True),
        )


class FeesTransaction(BaseModel):
    student = ORM.ForeignKeyField(User,
                              backref='student_fee_transactions',
                              on_delete='CASCADE')
    acad_session = ORM.CharField(max_length=10)
    fees_txn_amt = ORM.IntegerField()
    fees_txn_no = ORM.CharField(max_length=50)
    fees_txn_dt = ORM.DateField()
    fees_txn_bank = ORM.CharField(max_length=100)
    doc_file_name = ORM.CharField(max_length=100)

    class Meta:
        indexes = (
            # Unique index
            (
                ('student', 'acad_session', 'fees_txn_no',
                'fees_txn_bank', 'fees_txn_dt',
                'doc_file_name', 'is_deleted'), True),
        )


class StudentCredits(BaseModel):
    student = ORM.ForeignKeyField(User, backref='student_credits')
    acad_session = ORM.CharField(max_length=10)
    cgpa = ORM.FloatField()
    sgpa = ORM.FloatField()
    cred_earned = ORM.FloatField()
    cred_registered = ORM.FloatField()
    cred_earned_total = ORM.FloatField()
    
    class Meta:
        indexes = (
            # Unique index
            (('student', 'acad_session'), True),
        )


class DcForStudent(BaseModel):
 
    student = ORM.ForeignKeyField(User,
                              backref='student_dcs',
                              on_delete='CASCADE')
    # Status can be: Proposed, Returned, Approved
    status = ORM.CharField(max_length=40)
    effective_from = ORM.DateField(default=DT.now)
    effective_to = ORM.DateField(null=True)
    remarks = ORM.TextField(null=True)
    
    class Meta:
        indexes = (
            # Unique index
            (('student', 'status', 'effective_from'), True),
        )


class DcMember(BaseModel):
    DC_ROLES = [
        ("ME", 'Member'),
        ("SU", 'Supervisor'),
        ("CO", 'Co-Supervisor'),
        ("CP", 'Chairperson'),
    ]
    role = ORM.CharField(max_length=2, choices=DC_ROLES,
                       default="ME")
    member = ORM.ForeignKeyField(User, null=True,
                                 backref='dc_memberships',
                                 on_delete='CASCADE')
    dc = ORM.ForeignKeyField(DcForStudent,
                                 backref='dc_members',
                                 on_delete='CASCADE')
    is_external = ORM.BooleanField(default=False)
    ext_name = ORM.CharField(max_length=100, null=True)
    ext_contact = ORM.TextField(null=True)
    expertise = ORM.TextField(null=True)
    class Meta:
        indexes = (
            # Unique index
            (('role', 'member', 'dc', 'is_external', 'ext_name'), True),
        )


class PhDProgressReport(BaseModel):
    PPR_STATUSES = [
        ("DRA", 'Draft'),
        ("RET", 'Returned'),
        ("SUB", 'Submitted'),
        ("APP", 'Approved'),
    ]
    status = ORM.CharField(max_length=10, choices=PPR_STATUSES,
                       default="DRA")
    student = ORM.ForeignKeyField(User,
                              backref='phd_progress_reports',
                              on_delete='CASCADE')
    dc_member = ORM.ForeignKeyField(DcMember,
                                 backref='phd_progress_reports',
                                 on_delete='CASCADE')
    acad_session = ORM.CharField(max_length=10)
    is_satisfactory = ORM.BooleanField(default=False)
    note = ORM.TextField()

    class Meta:
        indexes = (
            # Unique index
            (('student', 'dc_member', 'acad_session'), True),
        )

class AcademicMilestone(BaseModel):
    student = ORM.ForeignKeyField(User,
                              backref='acad_milestones',
                              on_delete='CASCADE')
    dc = ORM.ForeignKeyField(DcForStudent,
                                 backref='acad_milestones',
                                 on_delete='CASCADE')
    # Joining -> DC formation -> Compre -> TP ->
    # Open Seminar 1 -> Open Seminar 2 -> Synop -> 
    # Thesis submit -> Defence -> Awarded
    milestone = ORM.CharField(max_length=40)
    status_dt = ORM.DateField(default=DT.now)
    remarks = ORM.TextField(null=True)

    class Meta:
        indexes = (
            # Unique index
            (('dc', 'student', 'milestone'), True),
        )

class AttendancePhoto(BaseModel):
    offering = ORM.ForeignKeyField(CourseOffering,
                                 backref="attendance_photos",
                                 on_delete="CASCADE")
    attend_dt = ORM.DateField(default=DT.now)
    file_name = ORM.CharField(max_length=200)
    # DONE, PENDING, ERROR
    status = ORM.CharField(max_length=15, default="PENDING")

    class Meta:
        indexes = (
            # Unique index
            (('offering', 'attend_dt', 'file_name'), True),
        )

class SystemSetting(BaseModel):
    group = ORM.CharField(max_length=60, index=True)
    name = ORM.CharField(max_length=200, index=True)
    is_json = ORM.BooleanField(index=True)
    value_text = ORM.TextField(null=True)
    value_json = JSONField(default={}, null=True)

    class Meta:
        indexes = (
            # Unique index
            (('group', 'name', 'is_json'), True),
        )
