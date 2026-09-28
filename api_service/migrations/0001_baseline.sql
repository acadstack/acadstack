-- Baseline schema for a new AcadStack database.
-- Later schema changes go in new numbered files next to this one; do not edit
-- this file once an installation has applied it.

CREATE TABLE public.academiccalendar (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    acad_session character varying(10) NOT NULL,
    event_code character varying(100) NOT NULL,
    event_value text NOT NULL
);

CREATE SEQUENCE public.academiccalendar_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.academiccalendar_id_seq OWNED BY public.academiccalendar.id;

CREATE TABLE public.academicmilestone (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    student_id bigint NOT NULL,
    dc_id bigint NOT NULL,
    milestone character varying(40) NOT NULL,
    status_dt date NOT NULL,
    remarks text
);

CREATE SEQUENCE public.academicmilestone_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.academicmilestone_id_seq OWNED BY public.academicmilestone.id;

CREATE TABLE public.attendancephoto (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    offering_id bigint NOT NULL,
    attend_dt date NOT NULL,
    file_name character varying(200) NOT NULL,
    status character varying(15) NOT NULL
);

CREATE SEQUENCE public.attendancephoto_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.attendancephoto_id_seq OWNED BY public.attendancephoto.id;

CREATE TABLE public.batchadvisors (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    user_id bigint NOT NULL,
    year_of_entry character varying(4) NOT NULL,
    for_degree character varying(20) NOT NULL
);

CREATE SEQUENCE public.batchadvisors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.batchadvisors_id_seq OWNED BY public.batchadvisors.id;

CREATE TABLE public.course (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    code character varying(20) NOT NULL,
    title character varying(200) NOT NULL,
    ltp character varying(40),
    status character varying(4) NOT NULL,
    author_id bigint,
    freq character varying(1) NOT NULL,
    has_lab boolean NOT NULL,
    prereqs character varying(200),
    objectives text,
    req_visiting_fac boolean NOT NULL,
    course_supersedes character varying(100),
    course_overlaps character varying(100),
    tkp json NOT NULL,
    tgap json NOT NULL,
    modules json NOT NULL,
    teaching json NOT NULL,
    learning json NOT NULL,
    evaluation json NOT NULL,
    ref_material json NOT NULL
);

CREATE SEQUENCE public.course_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.course_id_seq OWNED BY public.course.id;

CREATE TABLE public.coursecategory (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    offering_id bigint,
    degree character varying(20) NOT NULL,
    dept character varying(4),
    category character varying(4),
    for_entry_years character varying(100)
);

CREATE SEQUENCE public.coursecategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.coursecategory_id_seq OWNED BY public.coursecategory.id;

CREATE TABLE public.courseenrollment (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    course_offering_id bigint NOT NULL,
    student_id bigint NOT NULL,
    enrol_type character varying(20) NOT NULL,
    enrol_status character varying(10) NOT NULL,
    grade character varying(2) NOT NULL,
    current_score real,
    remarks text
);

CREATE SEQUENCE public.courseenrollment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.courseenrollment_id_seq OWNED BY public.courseenrollment.id;

CREATE TABLE public.courseinstructor (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    offering_id bigint,
    instructor_id bigint,
    is_coordinator boolean NOT NULL
);

CREATE SEQUENCE public.courseinstructor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.courseinstructor_id_seq OWNED BY public.courseinstructor.id;

CREATE TABLE public.courseinstructorfeedback (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    instructor_id bigint NOT NULL,
    question_id bigint NOT NULL,
    feedback text NOT NULL,
    submission_id character varying(40) NOT NULL,
    acad_session character varying(10) NOT NULL
);

CREATE SEQUENCE public.courseinstructorfeedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.courseinstructorfeedback_id_seq OWNED BY public.courseinstructorfeedback.id;

CREATE TABLE public.courseoffering (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    acad_session character varying(10) NOT NULL,
    course_id bigint,
    status character varying(2) NOT NULL,
    slot character varying(10),
    section character varying(2) NOT NULL,
    dept_name character varying(10)
);

CREATE SEQUENCE public.courseoffering_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.courseoffering_id_seq OWNED BY public.courseoffering.id;

CREATE TABLE public.courseslottiming (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    slot character varying(40) NOT NULL,
    week_day smallint NOT NULL,
    start_time smallint NOT NULL,
    end_time smallint NOT NULL
);

CREATE SEQUENCE public.courseslottiming_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.courseslottiming_id_seq OWNED BY public.courseslottiming.id;

CREATE TABLE public.dcforstudent (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    student_id bigint NOT NULL,
    status character varying(40) NOT NULL,
    effective_from date NOT NULL,
    effective_to date,
    remarks text
);

CREATE SEQUENCE public.dcforstudent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.dcforstudent_id_seq OWNED BY public.dcforstudent.id;

CREATE TABLE public.dcmember (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    role character varying(2) NOT NULL,
    member_id bigint,
    dc_id bigint NOT NULL,
    is_external boolean NOT NULL,
    ext_name character varying(100),
    ext_contact text,
    expertise text
);

CREATE SEQUENCE public.dcmember_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.dcmember_id_seq OWNED BY public.dcmember.id;

CREATE TABLE public.feedbackform (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    form_name character varying(50) NOT NULL,
    is_active boolean NOT NULL,
    form_type character varying(45) NOT NULL
);

CREATE SEQUENCE public.feedbackform_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.feedbackform_id_seq OWNED BY public.feedbackform.id;

CREATE TABLE public.feedbackquestion (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    form_id bigint NOT NULL,
    question character varying(500) NOT NULL,
    ans_options json,
    is_optional boolean NOT NULL,
    is_multianswer boolean NOT NULL,
    is_text boolean NOT NULL
);

CREATE SEQUENCE public.feedbackquestion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.feedbackquestion_id_seq OWNED BY public.feedbackquestion.id;

CREATE TABLE public.feestransaction (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    student_id bigint NOT NULL,
    acad_session character varying(10) NOT NULL,
    fees_txn_amt integer NOT NULL,
    fees_txn_no character varying(50) NOT NULL,
    fees_txn_dt date NOT NULL,
    fees_txn_bank character varying(100) NOT NULL,
    doc_file_name character varying(100) NOT NULL
);

CREATE SEQUENCE public.feestransaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.feestransaction_id_seq OWNED BY public.feestransaction.id;

CREATE TABLE public.knownface (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    user_id bigint,
    face_enc text NOT NULL,
    photo text NOT NULL
);

CREATE SEQUENCE public.knownface_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.knownface_id_seq OWNED BY public.knownface.id;

CREATE TABLE public.passwordresetkey (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    login_id character varying(40) NOT NULL,
    prk character varying(40) NOT NULL
);

CREATE SEQUENCE public.passwordresetkey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.passwordresetkey_id_seq OWNED BY public.passwordresetkey.id;

CREATE TABLE public.person (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    org_id character varying(40) NOT NULL,
    gender character(1),
    dept_name character varying(10) NOT NULL,
    year_of_entry character varying(4),
    degree character varying(20),
    category character varying(10),
    deg_type character varying(10),
    deg_type_spec character varying(10),
    current_status character varying(10)
);

CREATE SEQUENCE public.person_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.person_id_seq OWNED BY public.person.id;

CREATE TABLE public.phdprogressreport (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    status character varying(10) NOT NULL,
    student_id bigint NOT NULL,
    dc_member_id bigint NOT NULL,
    acad_session character varying(10) NOT NULL,
    is_satisfactory boolean NOT NULL,
    note text NOT NULL
);

CREATE SEQUENCE public.phdprogressreport_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.phdprogressreport_id_seq OWNED BY public.phdprogressreport.id;

CREATE TABLE public.setting (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    key character varying(60) NOT NULL,
    value json NOT NULL
);

CREATE SEQUENCE public.setting_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.setting_id_seq OWNED BY public.setting.id;

CREATE TABLE public.studentattendance (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    attend character varying(2) NOT NULL,
    enrollment_id bigint NOT NULL,
    attend_dt date NOT NULL,
    remarks character varying(500)
);

CREATE SEQUENCE public.studentattendance_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.studentattendance_id_seq OWNED BY public.studentattendance.id;

CREATE TABLE public.studentcredits (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    student_id bigint NOT NULL,
    acad_session character varying(10) NOT NULL,
    cgpa real NOT NULL,
    sgpa real NOT NULL,
    cred_earned real NOT NULL,
    cred_registered real NOT NULL,
    cred_earned_total real NOT NULL
);

CREATE SEQUENCE public.studentcredits_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.studentcredits_id_seq OWNED BY public.studentcredits.id;

CREATE TABLE public.studentfeedbackstatus (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    feedback_form_id bigint NOT NULL,
    course_instructor_id bigint NOT NULL,
    student_id bigint NOT NULL,
    is_submitted boolean NOT NULL
);

CREATE SEQUENCE public.studentfeedbackstatus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.studentfeedbackstatus_id_seq OWNED BY public.studentfeedbackstatus.id;

CREATE TABLE public.studentsupervisor (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    student_id bigint NOT NULL,
    supervisor_id bigint NOT NULL
);

CREATE SEQUENCE public.studentsupervisor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.studentsupervisor_id_seq OWNED BY public.studentsupervisor.id;

CREATE TABLE public."user" (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    login_id character varying(40) NOT NULL,
    password_hashed text NOT NULL,
    email character varying(150) NOT NULL,
    first_name character varying(100),
    last_name character varying(100),
    is_locked boolean NOT NULL,
    person_id bigint,
    role character varying(4) NOT NULL
);

CREATE SEQUENCE public.user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;

CREATE TABLE public.userdoc (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    user_id bigint,
    category character varying(20) NOT NULL,
    description text NOT NULL,
    file_name text NOT NULL,
    doc text NOT NULL
);

CREATE SEQUENCE public.userdoc_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.userdoc_id_seq OWNED BY public.userdoc.id;

CREATE TABLE public.vocabitem (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    vocab character varying(40) NOT NULL,
    code character varying(20) NOT NULL,
    label character varying(200) NOT NULL,
    sort_order integer NOT NULL
);

CREATE SEQUENCE public.vocabitem_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.vocabitem_id_seq OWNED BY public.vocabitem.id;

CREATE TABLE public.workflownote (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    entity_key integer NOT NULL,
    entity_name character varying(50) NOT NULL,
    note text
);

CREATE SEQUENCE public.workflownote_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.workflownote_id_seq OWNED BY public.workflownote.id;

ALTER TABLE ONLY public.academiccalendar ALTER COLUMN id SET DEFAULT nextval('public.academiccalendar_id_seq'::regclass);

ALTER TABLE ONLY public.academicmilestone ALTER COLUMN id SET DEFAULT nextval('public.academicmilestone_id_seq'::regclass);

ALTER TABLE ONLY public.attendancephoto ALTER COLUMN id SET DEFAULT nextval('public.attendancephoto_id_seq'::regclass);

ALTER TABLE ONLY public.batchadvisors ALTER COLUMN id SET DEFAULT nextval('public.batchadvisors_id_seq'::regclass);

ALTER TABLE ONLY public.course ALTER COLUMN id SET DEFAULT nextval('public.course_id_seq'::regclass);

ALTER TABLE ONLY public.coursecategory ALTER COLUMN id SET DEFAULT nextval('public.coursecategory_id_seq'::regclass);

ALTER TABLE ONLY public.courseenrollment ALTER COLUMN id SET DEFAULT nextval('public.courseenrollment_id_seq'::regclass);

ALTER TABLE ONLY public.courseinstructor ALTER COLUMN id SET DEFAULT nextval('public.courseinstructor_id_seq'::regclass);

ALTER TABLE ONLY public.courseinstructorfeedback ALTER COLUMN id SET DEFAULT nextval('public.courseinstructorfeedback_id_seq'::regclass);

ALTER TABLE ONLY public.courseoffering ALTER COLUMN id SET DEFAULT nextval('public.courseoffering_id_seq'::regclass);

ALTER TABLE ONLY public.courseslottiming ALTER COLUMN id SET DEFAULT nextval('public.courseslottiming_id_seq'::regclass);

ALTER TABLE ONLY public.dcforstudent ALTER COLUMN id SET DEFAULT nextval('public.dcforstudent_id_seq'::regclass);

ALTER TABLE ONLY public.dcmember ALTER COLUMN id SET DEFAULT nextval('public.dcmember_id_seq'::regclass);

ALTER TABLE ONLY public.feedbackform ALTER COLUMN id SET DEFAULT nextval('public.feedbackform_id_seq'::regclass);

ALTER TABLE ONLY public.feedbackquestion ALTER COLUMN id SET DEFAULT nextval('public.feedbackquestion_id_seq'::regclass);

ALTER TABLE ONLY public.feestransaction ALTER COLUMN id SET DEFAULT nextval('public.feestransaction_id_seq'::regclass);

ALTER TABLE ONLY public.knownface ALTER COLUMN id SET DEFAULT nextval('public.knownface_id_seq'::regclass);

ALTER TABLE ONLY public.passwordresetkey ALTER COLUMN id SET DEFAULT nextval('public.passwordresetkey_id_seq'::regclass);

ALTER TABLE ONLY public.person ALTER COLUMN id SET DEFAULT nextval('public.person_id_seq'::regclass);

ALTER TABLE ONLY public.phdprogressreport ALTER COLUMN id SET DEFAULT nextval('public.phdprogressreport_id_seq'::regclass);

ALTER TABLE ONLY public.setting ALTER COLUMN id SET DEFAULT nextval('public.setting_id_seq'::regclass);

ALTER TABLE ONLY public.studentattendance ALTER COLUMN id SET DEFAULT nextval('public.studentattendance_id_seq'::regclass);

ALTER TABLE ONLY public.studentcredits ALTER COLUMN id SET DEFAULT nextval('public.studentcredits_id_seq'::regclass);

ALTER TABLE ONLY public.studentfeedbackstatus ALTER COLUMN id SET DEFAULT nextval('public.studentfeedbackstatus_id_seq'::regclass);

ALTER TABLE ONLY public.studentsupervisor ALTER COLUMN id SET DEFAULT nextval('public.studentsupervisor_id_seq'::regclass);

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);

ALTER TABLE ONLY public.userdoc ALTER COLUMN id SET DEFAULT nextval('public.userdoc_id_seq'::regclass);

ALTER TABLE ONLY public.vocabitem ALTER COLUMN id SET DEFAULT nextval('public.vocabitem_id_seq'::regclass);

ALTER TABLE ONLY public.workflownote ALTER COLUMN id SET DEFAULT nextval('public.workflownote_id_seq'::regclass);

ALTER TABLE ONLY public.academiccalendar
    ADD CONSTRAINT academiccalendar_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.academicmilestone
    ADD CONSTRAINT academicmilestone_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.attendancephoto
    ADD CONSTRAINT attendancephoto_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.batchadvisors
    ADD CONSTRAINT batchadvisors_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.coursecategory
    ADD CONSTRAINT coursecategory_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.courseenrollment
    ADD CONSTRAINT courseenrollment_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.courseinstructor
    ADD CONSTRAINT courseinstructor_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.courseinstructorfeedback
    ADD CONSTRAINT courseinstructorfeedback_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.courseoffering
    ADD CONSTRAINT courseoffering_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.courseslottiming
    ADD CONSTRAINT courseslottiming_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dcforstudent
    ADD CONSTRAINT dcforstudent_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dcmember
    ADD CONSTRAINT dcmember_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.feedbackform
    ADD CONSTRAINT feedbackform_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.feedbackquestion
    ADD CONSTRAINT feedbackquestion_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.feestransaction
    ADD CONSTRAINT feestransaction_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.knownface
    ADD CONSTRAINT knownface_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.passwordresetkey
    ADD CONSTRAINT passwordresetkey_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.phdprogressreport
    ADD CONSTRAINT phdprogressreport_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.setting
    ADD CONSTRAINT setting_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.studentcredits
    ADD CONSTRAINT studentcredits_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.studentsupervisor
    ADD CONSTRAINT studentsupervisor_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.userdoc
    ADD CONSTRAINT userdoc_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.vocabitem
    ADD CONSTRAINT vocabitem_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.workflownote
    ADD CONSTRAINT workflownote_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX academiccalendar_acad_session_event_code ON public.academiccalendar USING btree (acad_session, event_code);

CREATE INDEX academiccalendar_txn_no ON public.academiccalendar USING btree (txn_no);

CREATE INDEX academicmilestone_dc_id ON public.academicmilestone USING btree (dc_id);

CREATE UNIQUE INDEX academicmilestone_dc_id_student_id_milestone ON public.academicmilestone USING btree (dc_id, student_id, milestone);

CREATE INDEX academicmilestone_student_id ON public.academicmilestone USING btree (student_id);

CREATE INDEX academicmilestone_txn_no ON public.academicmilestone USING btree (txn_no);

CREATE INDEX attendancephoto_offering_id ON public.attendancephoto USING btree (offering_id);

CREATE UNIQUE INDEX attendancephoto_offering_id_attend_dt_file_name ON public.attendancephoto USING btree (offering_id, attend_dt, file_name);

CREATE INDEX attendancephoto_txn_no ON public.attendancephoto USING btree (txn_no);

CREATE INDEX batchadvisors_txn_no ON public.batchadvisors USING btree (txn_no);

CREATE INDEX batchadvisors_user_id ON public.batchadvisors USING btree (user_id);

CREATE UNIQUE INDEX batchadvisors_user_id_year_of_entry_for_degree ON public.batchadvisors USING btree (user_id, year_of_entry, for_degree);

CREATE INDEX course_author_id ON public.course USING btree (author_id);

CREATE UNIQUE INDEX course_code ON public.course USING btree (code);

CREATE INDEX course_txn_no ON public.course USING btree (txn_no);

CREATE INDEX coursecategory_offering_id ON public.coursecategory USING btree (offering_id);

CREATE UNIQUE INDEX coursecategory_offering_id_degree_dept_category ON public.coursecategory USING btree (offering_id, degree, dept, category);

CREATE INDEX coursecategory_txn_no ON public.coursecategory USING btree (txn_no);

CREATE INDEX courseenrollment_course_offering_id ON public.courseenrollment USING btree (course_offering_id);

CREATE INDEX courseenrollment_student_id ON public.courseenrollment USING btree (student_id);

CREATE UNIQUE INDEX courseenrollment_student_id_course_offering_id ON public.courseenrollment USING btree (student_id, course_offering_id);

CREATE INDEX courseenrollment_txn_no ON public.courseenrollment USING btree (txn_no);

CREATE INDEX courseinstructor_instructor_id ON public.courseinstructor USING btree (instructor_id);

CREATE INDEX courseinstructor_offering_id ON public.courseinstructor USING btree (offering_id);

CREATE UNIQUE INDEX courseinstructor_offering_id_instructor_id ON public.courseinstructor USING btree (offering_id, instructor_id);

CREATE INDEX courseinstructor_txn_no ON public.courseinstructor USING btree (txn_no);

CREATE INDEX courseinstructorfeedback_instructor_id ON public.courseinstructorfeedback USING btree (instructor_id);

CREATE INDEX courseinstructorfeedback_question_id ON public.courseinstructorfeedback USING btree (question_id);

CREATE INDEX courseinstructorfeedback_txn_no ON public.courseinstructorfeedback USING btree (txn_no);

CREATE INDEX courseoffering_course_id ON public.courseoffering USING btree (course_id);

CREATE UNIQUE INDEX courseoffering_course_id_acad_session_status_section_dept_name ON public.courseoffering USING btree (course_id, acad_session, status, section, dept_name);

CREATE INDEX courseoffering_txn_no ON public.courseoffering USING btree (txn_no);

CREATE UNIQUE INDEX courseslottiming_slot_week_day_start_time ON public.courseslottiming USING btree (slot, week_day, start_time);

CREATE INDEX courseslottiming_txn_no ON public.courseslottiming USING btree (txn_no);

CREATE INDEX dcforstudent_student_id ON public.dcforstudent USING btree (student_id);

CREATE UNIQUE INDEX dcforstudent_student_id_status_effective_from ON public.dcforstudent USING btree (student_id, status, effective_from);

CREATE INDEX dcforstudent_txn_no ON public.dcforstudent USING btree (txn_no);

CREATE INDEX dcmember_dc_id ON public.dcmember USING btree (dc_id);

CREATE INDEX dcmember_member_id ON public.dcmember USING btree (member_id);

CREATE UNIQUE INDEX dcmember_role_member_id_dc_id_is_external_ext_name ON public.dcmember USING btree (role, member_id, dc_id, is_external, ext_name);

CREATE INDEX dcmember_txn_no ON public.dcmember USING btree (txn_no);

CREATE UNIQUE INDEX feedbackform_form_name_form_type_is_active ON public.feedbackform USING btree (form_name, form_type, is_active);

CREATE INDEX feedbackform_txn_no ON public.feedbackform USING btree (txn_no);

CREATE INDEX feedbackquestion_form_id ON public.feedbackquestion USING btree (form_id);

CREATE UNIQUE INDEX feedbackquestion_form_id_question ON public.feedbackquestion USING btree (form_id, question);

CREATE INDEX feedbackquestion_txn_no ON public.feedbackquestion USING btree (txn_no);

CREATE INDEX feestransaction_student_id ON public.feestransaction USING btree (student_id);

CREATE UNIQUE INDEX feestransaction_student_id_acad_session_fees_txn_no_fees_c1d64d ON public.feestransaction USING btree (student_id, acad_session, fees_txn_no, fees_txn_bank, fees_txn_dt, doc_file_name, is_deleted);

CREATE INDEX feestransaction_txn_no ON public.feestransaction USING btree (txn_no);

CREATE INDEX knownface_txn_no ON public.knownface USING btree (txn_no);

CREATE INDEX knownface_user_id ON public.knownface USING btree (user_id);

CREATE INDEX passwordresetkey_txn_no ON public.passwordresetkey USING btree (txn_no);

CREATE UNIQUE INDEX person_org_id ON public.person USING btree (org_id);

CREATE INDEX person_txn_no ON public.person USING btree (txn_no);

CREATE INDEX phdprogressreport_dc_member_id ON public.phdprogressreport USING btree (dc_member_id);

CREATE INDEX phdprogressreport_student_id ON public.phdprogressreport USING btree (student_id);

CREATE UNIQUE INDEX phdprogressreport_student_id_dc_member_id_acad_session ON public.phdprogressreport USING btree (student_id, dc_member_id, acad_session);

CREATE INDEX phdprogressreport_txn_no ON public.phdprogressreport USING btree (txn_no);

CREATE UNIQUE INDEX setting_key ON public.setting USING btree (key);

CREATE INDEX setting_txn_no ON public.setting USING btree (txn_no);

CREATE INDEX studentattendance_enrollment_id ON public.studentattendance USING btree (enrollment_id);

CREATE UNIQUE INDEX studentattendance_enrollment_id_attend_dt ON public.studentattendance USING btree (enrollment_id, attend_dt);

CREATE INDEX studentattendance_txn_no ON public.studentattendance USING btree (txn_no);

CREATE INDEX studentcredits_student_id ON public.studentcredits USING btree (student_id);

CREATE UNIQUE INDEX studentcredits_student_id_acad_session ON public.studentcredits USING btree (student_id, acad_session);

CREATE INDEX studentcredits_txn_no ON public.studentcredits USING btree (txn_no);

CREATE INDEX studentfeedbackstatus_course_instructor_id ON public.studentfeedbackstatus USING btree (course_instructor_id);

CREATE UNIQUE INDEX studentfeedbackstatus_course_instructor_id_student_id_fe_ce0120 ON public.studentfeedbackstatus USING btree (course_instructor_id, student_id, feedback_form_id);

CREATE INDEX studentfeedbackstatus_feedback_form_id ON public.studentfeedbackstatus USING btree (feedback_form_id);

CREATE INDEX studentfeedbackstatus_student_id ON public.studentfeedbackstatus USING btree (student_id);

CREATE INDEX studentfeedbackstatus_txn_no ON public.studentfeedbackstatus USING btree (txn_no);

CREATE INDEX studentsupervisor_student_id ON public.studentsupervisor USING btree (student_id);

CREATE UNIQUE INDEX studentsupervisor_student_id_supervisor_id ON public.studentsupervisor USING btree (student_id, supervisor_id);

CREATE INDEX studentsupervisor_supervisor_id ON public.studentsupervisor USING btree (supervisor_id);

CREATE INDEX studentsupervisor_txn_no ON public.studentsupervisor USING btree (txn_no);

CREATE UNIQUE INDEX user_email ON public."user" USING btree (email);

CREATE UNIQUE INDEX user_login_id ON public."user" USING btree (login_id);

CREATE UNIQUE INDEX user_person_id ON public."user" USING btree (person_id);

CREATE INDEX user_txn_no ON public."user" USING btree (txn_no);

CREATE INDEX userdoc_txn_no ON public.userdoc USING btree (txn_no);

CREATE INDEX userdoc_user_id ON public.userdoc USING btree (user_id);

CREATE INDEX vocabitem_txn_no ON public.vocabitem USING btree (txn_no);

CREATE UNIQUE INDEX vocabitem_vocab_code ON public.vocabitem USING btree (vocab, code);

CREATE INDEX workflownote_txn_no ON public.workflownote USING btree (txn_no);

ALTER TABLE ONLY public.academicmilestone
    ADD CONSTRAINT academicmilestone_dc_id_fkey FOREIGN KEY (dc_id) REFERENCES public.dcforstudent(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.academicmilestone
    ADD CONSTRAINT academicmilestone_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.attendancephoto
    ADD CONSTRAINT attendancephoto_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.courseoffering(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.batchadvisors
    ADD CONSTRAINT batchadvisors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_author_id_fkey FOREIGN KEY (author_id) REFERENCES public."user"(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.coursecategory
    ADD CONSTRAINT coursecategory_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.courseoffering(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.courseenrollment
    ADD CONSTRAINT courseenrollment_course_offering_id_fkey FOREIGN KEY (course_offering_id) REFERENCES public.courseoffering(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.courseenrollment
    ADD CONSTRAINT courseenrollment_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.courseinstructor
    ADD CONSTRAINT courseinstructor_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public."user"(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.courseinstructor
    ADD CONSTRAINT courseinstructor_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.courseoffering(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.courseinstructorfeedback
    ADD CONSTRAINT courseinstructorfeedback_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.courseinstructor(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.courseinstructorfeedback
    ADD CONSTRAINT courseinstructorfeedback_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.feedbackquestion(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.courseoffering
    ADD CONSTRAINT courseoffering_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.course(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.dcforstudent
    ADD CONSTRAINT dcforstudent_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dcmember
    ADD CONSTRAINT dcmember_dc_id_fkey FOREIGN KEY (dc_id) REFERENCES public.dcforstudent(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dcmember
    ADD CONSTRAINT dcmember_member_id_fkey FOREIGN KEY (member_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.feedbackquestion
    ADD CONSTRAINT feedbackquestion_form_id_fkey FOREIGN KEY (form_id) REFERENCES public.feedbackform(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.feestransaction
    ADD CONSTRAINT feestransaction_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.knownface
    ADD CONSTRAINT knownface_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);

ALTER TABLE ONLY public.phdprogressreport
    ADD CONSTRAINT phdprogressreport_dc_member_id_fkey FOREIGN KEY (dc_member_id) REFERENCES public.dcmember(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.phdprogressreport
    ADD CONSTRAINT phdprogressreport_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.courseenrollment(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studentcredits
    ADD CONSTRAINT studentcredits_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id);

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_course_instructor_id_fkey FOREIGN KEY (course_instructor_id) REFERENCES public.courseinstructor(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_feedback_form_id_fkey FOREIGN KEY (feedback_form_id) REFERENCES public.feedbackform(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studentsupervisor
    ADD CONSTRAINT studentsupervisor_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.studentsupervisor
    ADD CONSTRAINT studentsupervisor_supervisor_id_fkey FOREIGN KEY (supervisor_id) REFERENCES public."user"(id) ON DELETE CASCADE;

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.person(id);

ALTER TABLE ONLY public.userdoc
    ADD CONSTRAINT userdoc_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);

-- Default entries of the lists that differ between universities. Edit them
-- with SQL; set is_deleted = true to hide an entry.

INSERT INTO public.vocabitem (vocab, code, label, sort_order, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('Departments', 'ACA', 'Academic Section', 1, false, 1, now(), now()),
    ('Departments', 'EST', 'Establishment Section', 2, false, 1, now(), now()),
    ('Departments', 'CSE', 'Computer Science and Engineering', 3, false, 1, now(), now()),
    ('Departments', 'AIL', 'Artificial Intelligence', 4, false, 1, now(), now()),
    ('Departments', 'CEE', 'Center for Engineering Education', 5, false, 1, now(), now()),
    ('Departments', 'CIV', 'Civil Engineering', 6, false, 1, now(), now()),
    ('Departments', 'CHE', 'Chemical Engineering', 7, false, 1, now(), now()),
    ('Departments', 'ELE', 'Electrical Engineering', 8, false, 1, now(), now()),
    ('Departments', 'MEC', 'Mechanical Engineering', 9, false, 1, now(), now()),
    ('Departments', 'BIO', 'Biomedical Engineering', 10, false, 1, now(), now()),
    ('Departments', 'MET', 'Metallurgical and Materials Engineering', 11, false, 1, now(), now()),
    ('Departments', 'MTH', 'Mathematics', 12, false, 1, now(), now()),
    ('Departments', 'PHY', 'Physics', 13, false, 1, now(), now()),
    ('Departments', 'CHY', 'Chemistry', 14, false, 1, now(), now()),
    ('Departments', 'HSS', 'Humanities and Social Sciences', 15, false, 1, now(), now()),
    ('Departments', 'CARD', 'Centre for Applied Research in Data Science', 16, false, 1, now(), now()),
    ('Departments', 'PREP', 'Preparatory Dept.', 17, false, 1, now(), now()),
    ('Departments', 'ALL', 'All Departments', 18, false, 1, now(), now()),
    ('Degrees', 'BTE', 'B.Tech', 1, false, 1, now(), now()),
    ('Degrees', 'BTE_MC', 'B.Tech(M&C)', 2, false, 1, now(), now()),
    ('Degrees', 'MTE', 'M.Tech', 3, false, 1, now(), now()),
    ('Degrees', 'MCS_AI', 'M.Tech(AI)', 4, false, 1, now(), now()),
    ('Degrees', 'MCE_WATER', 'M.Tech(Water Reso. & Envirn.)', 5, false, 1, now(), now()),
    ('Degrees', 'MCE_STRUC', 'M.Tech(Struc. and Geomech.)', 6, false, 1, now(), now()),
    ('Degrees', 'MEE_SIGNAL', 'M.Tech(Signal Processing)', 7, false, 1, now(), now()),
    ('Degrees', 'MEE_MICRO', 'M.Tech(Micro. & VLSI)', 8, false, 1, now(), now()),
    ('Degrees', 'MEE_POWER', 'M.Tech(Power Engg.)', 9, false, 1, now(), now()),
    ('Degrees', 'MME_THERM', 'M.Tech(Thermal Engg.)', 10, false, 1, now(), now()),
    ('Degrees', 'MME_MANUF', 'M.Tech(Manufacturing)', 11, false, 1, now(), now()),
    ('Degrees', 'MCE_MECHA', 'M.Tech(Mechanics And Design)', 12, false, 1, now(), now()),
    ('Degrees', 'MME_MCPMC', 'M.Tech(Computational Mechanics)', 13, false, 1, now(), now()),
    ('Degrees', 'MSR', 'M.S (Research)', 14, false, 1, now(), now()),
    ('Degrees', 'MSC', 'M.Sc', 15, false, 1, now(), now()),
    ('Degrees', 'BMD', 'B.Tech-M.Tech Dual', 16, false, 1, now(), now()),
    ('Degrees', 'JEE_PREP', 'JEE Preparatory', 17, false, 1, now(), now()),
    ('Degrees', 'ADD_INTRN', 'Additional Internship', 18, false, 1, now(), now()),
    ('Degrees', 'PHD', 'PhD', 19, false, 1, now(), now()),
    ('CourseSlots', 'S', 'Seminars or a core course (one hour per week)', 1, false, 1, now(), now()),
    ('CourseSlots', 'PC1', 'PC1: Core of 1-2 year B.Tech', 2, false, 1, now(), now()),
    ('CourseSlots', 'PC2', 'PC2: Core of 1-2 year B.Tech', 3, false, 1, now(), now()),
    ('CourseSlots', 'PC3', 'PC3: Core of 1-2 year B.Tech', 4, false, 1, now(), now()),
    ('CourseSlots', 'PC4', 'PC4: Core of 1-2 year B.Tech', 5, false, 1, now(), now()),
    ('CourseSlots', 'PCE1', 'PCE1: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech', 6, false, 1, now(), now()),
    ('CourseSlots', 'PCE2', 'PCE2: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech', 7, false, 1, now(), now()),
    ('CourseSlots', 'PCE3', 'PCE3: Core of 1-2 year B.Tech, and/or core/elec of 3-4 year B.Tech', 8, false, 1, now(), now()),
    ('CourseSlots', 'PCPE', 'Program core/elec for 3-4 year B.Tech', 9, false, 1, now(), now()),
    ('CourseSlots', 'HSPE', 'HSS elec or Program core/elec for 3-4 year B.Tech', 10, false, 1, now(), now()),
    ('CourseSlots', 'PCDE', 'HSS elec or dept core/elec for 3-4 year B.Tech', 11, false, 1, now(), now()),
    ('CourseSlots', 'PEOE', 'Program elec or open elec for 3-4 year B.Tech', 12, false, 1, now(), now()),
    ('CourseSlots', 'HSME', 'HSS or Science or Math elec 3rd and/or 4th year B.Tech', 13, false, 1, now(), now()),
    ('CourseSlots', 'LC', 'Lab Courses', 14, false, 1, now(), now()),
    ('CourseSlots', 'PHSME', 'Buffer slot', 15, false, 1, now(), now()),
    ('CourseTypes', 'SC', 'Science Requirement Core', 1, false, 1, now(), now()),
    ('CourseTypes', 'SE', 'Science Electives', 2, false, 1, now(), now()),
    ('CourseTypes', 'GR', 'General Engineering Requirement', 3, false, 1, now(), now()),
    ('CourseTypes', 'PC', 'Programme Core', 4, false, 1, now(), now()),
    ('CourseTypes', 'PE', 'Programme Elective', 5, false, 1, now(), now()),
    ('CourseTypes', 'HC', 'Humanities and Social Sciences core', 6, false, 1, now(), now()),
    ('CourseTypes', 'HE', 'Humanities and Social Sciences Electives', 7, false, 1, now(), now()),
    ('CourseTypes', 'CP', 'Capstone Projects', 8, false, 1, now(), now()),
    ('CourseTypes', 'CT', 'Industrial Internship and Comprehensive Viva', 9, false, 1, now(), now()),
    ('CourseTypes', 'NN', 'Extra-curricular', 10, false, 1, now(), now()),
    ('CourseTypes', 'OC', 'Open Electives', 11, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MCBME', 'Minor in Biomedical Engineering', 1, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MCHY', 'Minor in Chemistry', 2, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MCSE', 'Minor in Computer Science and Engineering', 3, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MELE', 'Minor in Electrical Engineering', 4, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MECE', 'Minor in Electronics & Communication Engineering', 5, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MMEC', 'Minor in Mechanical Engineering', 6, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MMTH', 'Minor in Mathematics', 7, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MPHY', 'Minor in Physics', 8, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MQUE', 'Minor in Quantum Engineering', 9, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MCGS', 'Minor in Cognitive Science', 10, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MENG', 'Minor in English and Creative Expression', 11, false, 1, now(), now()),
    ('MinorConcSpecialization', 'MCME', 'Minor in in Computational Mechanics', 12, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CSTR', 'Concentration in Structures', 13, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CMVL', 'Concentration in Micro-electronics and VLSI Design', 14, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CTHF', 'Concentration in Thermal and Fluids', 15, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CMNF', 'Concentration in Manufacturing', 16, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CMED', 'Concentration in Mechanics and Design', 17, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CAIL', 'Concentration in Artificial Intelligence', 18, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CVIP', 'Concentration in Computer Vision and Image Processing', 19, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CAES', 'Concentration in Architecture and Embedded Systems', 20, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CTCS', 'Concentration in Theoretical Computer Science', 21, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CMAM', 'Concentration in Mathematical Modelling', 22, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CAMT', 'Concentration in Advanced Mathematics', 23, false, 1, now(), now()),
    ('MinorConcSpecialization', 'CCME', 'Concentration in Computational Mechanics', 24, false, 1, now(), now());
