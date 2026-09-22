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

import acad_session as AS
import vocab_defaults as VD

# Deferred initialization
# db = ORM.PostgresqlDatabase(None)
db = PooledPostgresqlExtDatabase(None)

# Every choices= list below is derived from vocab_defaults.py (the single
# source of truth for controlled vocabularies -- see that module's
# docstring) instead of being retyped here. These stay as plain class/
# module attributes -- not a live DB read -- because they must exist at
# import time, before any DB connection exists (create_schema() and
# demo_data.py both need them before the schema they live in has even
# been created). An institution's DB-side additions/edits to a vocabulary
# (via settings_store.vocab()) are reflected in api_common.static_data_dict()
# and at runtime, but not in these bootstrap choices= lists; peewee does
# not enforce `choices` at save time, so this does not restrict what can
# actually be stored.
DEGREES = VD.choices("degrees")


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
                          AttendancePhoto, SystemSetting,
                          PolicyVersion, ClosedAcademicSession,
                          SchemaMigration])
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

    dept_name = ORM.CharField(max_length=10, choices=VD.choices("departments"))
    year_of_entry = ORM.CharField(max_length=4, null=True)  # yyyy
    degree = ORM.CharField(max_length=20, choices=DEGREES, null=True)
    category = ORM.CharField(max_length=10, null=True,
                         choices=VD.choices("person_categories"))
    deg_type = ORM.CharField(max_length=10, null=True,
                         choices=VD.choices("degree_types"))
    deg_type_spec = ORM.CharField(max_length=10, null=True,
                              choices=VD.choices("minor_conc_specializations"))
    current_status = ORM.CharField(max_length=10, null=True,
                               choices=VD.choices("student_statuses"))

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
    ROLES = VD.choices("roles")
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
    COURSE_STATUSES = VD.choices("course_statuses")
    code = ORM.CharField(max_length=20, unique=True)
    title = ORM.CharField(max_length=200)
    ltp = ORM.CharField(max_length=40, null=True)

    # S (session/teaching hours) and C (credits), computed ONCE from ltp's
    # L/T/P components server-side (see common.compute_course_ltp) and
    # stored here so no query has to re-derive them by re-running the
    # formula or by parsing ltp's string positions. The formula used to be
    # implemented twice, once in Python and again in SQL; storing the
    # result is what removed the second copy.
    s_hours = ORM.FloatField(null=True)
    credits = ORM.FloatField(null=True)

    status = ORM.CharField(max_length=4, default="DRA",
                       choices=COURSE_STATUSES)

    author = ORM.ForeignKeyField(User, null=True,
                             backref='authored_courses',
                             on_delete='SET NULL')

    freq = ORM.CharField(max_length=1, default="A",
                     choices=VD.choices("course_freqs"))
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
    CO_STATUSES = VD.choices("offering_statuses")
    # Academic session start date in which course is floated
    acad_session = ORM.CharField(max_length=10)
    course = ORM.ForeignKeyField(Course, backref='offerings',
                             null=True, on_delete='SET NULL')
    status = ORM.CharField(max_length=2, choices=CO_STATUSES,
                       default="E")
    slot = ORM.CharField(max_length=10, null=True,
                     choices=VD.choices("course_slots"))
    section = ORM.CharField(max_length=2, default="A")
    dept_name = ORM.CharField(max_length=10, null=True,
                          choices=VD.choices("departments"))

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
    category = ORM.CharField(max_length=4, null=True,
                         choices=VD.choices("course_types"))
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
    ENROL_STATUSES = VD.choices("enrolment_statuses")
    course_offering = ORM.ForeignKeyField(CourseOffering,
                                      backref='enrollments',
                                      on_delete='CASCADE')
    student = ORM.ForeignKeyField(User, backref='enrollments',
                              on_delete='CASCADE')
    # (C)redit, (A)udit,
    # Credit for minor (CM), Credit for concentration (CC)
    enrol_type = ORM.CharField(max_length=20,
                           choices=VD.choices("enrolment_types"))
    enrol_status = ORM.CharField(max_length=10, choices=ENROL_STATUSES,
                             default="IPEN")
    grade = ORM.CharField(max_length=2, default="NA",
                      choices=VD.choices("grades"))
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
    ATT_STATUS = VD.choices("attendance_codes")
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
    form_type = ORM.CharField(max_length=45, choices=VD.choices("form_types"))

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
    slot = ORM.CharField(max_length=40, choices=VD.choices("course_slots"))
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
    status = ORM.CharField(max_length=40, choices=VD.choices("dc_statuses"))
    effective_from = ORM.DateField(default=DT.now)
    effective_to = ORM.DateField(null=True)
    remarks = ORM.TextField(null=True)
    
    class Meta:
        indexes = (
            # Unique index
            (('student', 'status', 'effective_from'), True),
        )


class DcMember(BaseModel):
    DC_ROLES = VD.choices("dc_roles")
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
    PPR_STATUSES = VD.choices("ppr_statuses")
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


# ====== Versioned, effective-dated academic policy =========
# See policy_store.py for the read/write API and docs/versioned-policy.md
# for why this is a separate concept from SystemSetting.


class ImmutablePolicyError(Exception):
    """Raised when a write would alter policy that a closed academic
    session has already been computed under.

    Deliberately not an ``AcadStackException``: ``common`` imports
    ``models``, so this module cannot import that exception type without
    a cycle. ``policy_store`` re-raises these as ``PolicyImmutableError``,
    which subclasses BOTH this and ``AcadStackException``, so a caller can
    catch either one.
    """


def max_closed_session_ord():
    """The highest ordinal among closed academic sessions, or None when
    no session has been closed yet.

    This is the "seal line": policy effective from at or before it has
    already been used to compute results that must never change.
    """
    return (ClosedAcademicSession
            .select(ORM.fn.MAX(ClosedAcademicSession.session_ord))
            .scalar())


class PolicyVersion(BaseModel):
    """One immutable version of one policy group's ruleset.

    A version is in force from ``effective_from_session`` until the next
    version of the same group begins -- a half-open interval whose end is
    DERIVED, never stored. That is the structural reason superseding is
    the only write: introducing a new version writes exactly one new row
    and touches no existing one, so no existing row's meaning changes.
    (Storing an ``effective_to`` would mean every supersede UPDATEd the
    previous row, which is precisely the mutation we are preventing.)

    ``effective_from_ord`` is the session's ordinal (see acad_session.py),
    denormalised so that resolution and the write guards are plain integer
    comparisons on an index. Migration 0003 adds a CHECK constraint tying
    it to ``effective_from_session``, so the two cannot disagree.
    """

    policy_group = ORM.CharField(max_length=60, index=True)
    effective_from_session = ORM.CharField(max_length=10)
    effective_from_ord = ORM.IntegerField(index=True)

    #: The whole ruleset as one JSON document. A ruleset is atomic: its
    #: parts (e.g. a grade->point map and the grade sets that go with it)
    #: are only meaningful together, so they version together.
    payload = JSONField(default={})

    #: Free text: the authority for the change (circular, minute number).
    note = ORM.TextField(null=True)

    class Meta:
        indexes = (
            # Unique index: one version per group per session boundary.
            (('policy_group', 'effective_from_ord'), True),
        )

    @property
    def is_sealed(self):
        """Whether a closed session sits at or after this version's start,
        making the row historical and therefore frozen.

        Conservative on purpose: a version superseded before any session
        it governed was closed is still treated as sealed, because it was
        in force and may have been referenced while it was.
        """
        seal = max_closed_session_ord()
        return seal is not None and seal >= self.effective_from_ord

    def _reject_if_sealed(self, verb):
        seal = max_closed_session_ord()
        if seal is None:
            return
        # For an UPDATE, the row is protected if EITHER its stored start
        # or the proposed new start is inside sealed territory -- so a
        # sealed version cannot be edited, and an unsealed one cannot be
        # moved back into history.
        ords = [self.effective_from_ord]
        if self._pk is not None:
            stored = (PolicyVersion
                      .select(PolicyVersion.effective_from_ord)
                      .where(PolicyVersion.id == self._pk)
                      .scalar())
            if stored is not None:
                ords.append(stored)
        if min(ords) <= seal:
            raise ImmutablePolicyError(
                f"Cannot {verb} policy version for group "
                f"{self.policy_group!r} effective {self.effective_from_session}"
                f": academic session {AS.from_ordinal(seal)} is closed, so "
                f"policy from that session or earlier is final. Supersede it "
                f"with a version effective from a later session instead.")

    def save(self, force_insert=False, **kwargs):
        """Blocks writes into sealed history.

        Covers both directions: inserting a version effective from an
        already-closed session (which would retroactively restate that
        session's rules) and updating/soft-deleting a sealed row. Rows
        that govern only open sessions stay writable.

        This is the ORM-level guard; migration 0003 installs equivalent
        triggers so that raw SQL -- which this codebase does use -- cannot
        go around it, and so that bulk ``.update()``/``.delete()`` queries,
        which never call this method, are caught too.
        """
        self._reject_if_sealed("insert" if self._pk is None else "modify")
        return super().save(force_insert=force_insert, **kwargs)

    def delete_instance(self, *args, **kwargs):
        self._reject_if_sealed("delete")
        return super().delete_instance(*args, **kwargs)


class ClosedAcademicSession(BaseModel):
    """Append-only record that an academic session's results are final.

    Closing is an explicit administrative act rather than a date going
    past, for two reasons: a date-derived rule would un-close a session
    the moment somebody corrected a calendar row, and the close event is
    the natural hook for freezing per-student records once results are
    out (see the StudentCredits recommendation in
    docs/versioned-policy.md).

    Rows are never updated or deleted -- the seal only ever advances.
    """

    acad_session = ORM.CharField(max_length=10, unique=True)
    session_ord = ORM.IntegerField(index=True)
    closed_ts = ORM.DateTimeField(default=DT.now)
    note = ORM.TextField(null=True)

    def save(self, force_insert=False, **kwargs):
        if self._pk is not None and not force_insert:
            raise ImmutablePolicyError(
                f"Academic session {self.acad_session} is already recorded as "
                f"closed; closure records are append-only and cannot be "
                f"edited or reopened.")
        return super().save(force_insert=force_insert, **kwargs)

    def delete_instance(self, *args, **kwargs):
        raise ImmutablePolicyError(
            f"Academic session {self.acad_session} cannot be reopened: "
            f"closure records are append-only.")


class SchemaMigration(ORM.Model):
    """Bookkeeping table recording which files under migrations/ have
    already been applied. Not a BaseModel: this is tooling state, not a
    business entity, so it skips is_deleted/txn_no/ins_ts/etc."""
    version = ORM.CharField(max_length=255, unique=True)
    applied_ts = ORM.DateTimeField(default=DT.now)

    class Meta:
        database = db
        table_name = "schema_migrations"
