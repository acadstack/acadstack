-- Baseline schema for a new AcadStack database.
-- Later schema changes go in new numbered files next to this one; do not edit
-- this file once an installation has applied it. (None has yet: until the
-- first deployment, schema changes are folded in here.)

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

CREATE TABLE public.academicsession (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    code character varying(10) NOT NULL,
    is_additional boolean NOT NULL
);

CREATE SEQUENCE public.academicsession_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.academicsession_id_seq OWNED BY public.academicsession.id;

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
    freq character varying(1),
    level character varying(3) NOT NULL,
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
    remarks text,
    -- The course's credits, copied when the session is closed (NULL while
    -- it is open), so later course changes don't change transcripts
    credits numeric(6,2)
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
    sort_order integer NOT NULL,
    attrs jsonb DEFAULT '{}'::jsonb NOT NULL
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

ALTER TABLE ONLY public.academicsession ALTER COLUMN id SET DEFAULT nextval('public.academicsession_id_seq'::regclass);

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

ALTER TABLE ONLY public.academicsession
    ADD CONSTRAINT academicsession_pkey PRIMARY KEY (id);

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

CREATE UNIQUE INDEX academicsession_code ON public.academicsession USING btree (code);

CREATE INDEX academicsession_txn_no ON public.academicsession USING btree (txn_no);

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

CREATE TABLE public.role (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    code character varying(4) NOT NULL,
    label character varying(100) NOT NULL
);

CREATE SEQUENCE public.role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.role_id_seq OWNED BY public.role.id;

ALTER TABLE ONLY public.role ALTER COLUMN id SET DEFAULT nextval('public.role_id_seq'::regclass);

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX role_code ON public.role USING btree (code);

CREATE INDEX role_txn_no ON public.role USING btree (txn_no);

CREATE TABLE public.permission (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    code character varying(60) NOT NULL,
    description character varying(200) NOT NULL
);

CREATE SEQUENCE public.permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.permission_id_seq OWNED BY public.permission.id;

ALTER TABLE ONLY public.permission ALTER COLUMN id SET DEFAULT nextval('public.permission_id_seq'::regclass);

ALTER TABLE ONLY public.permission
    ADD CONSTRAINT permission_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX permission_code ON public.permission USING btree (code);

CREATE INDEX permission_txn_no ON public.permission USING btree (txn_no);

CREATE TABLE public.rolepermission (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    role character varying(4) NOT NULL,
    permission character varying(60) NOT NULL
);

CREATE SEQUENCE public.rolepermission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.rolepermission_id_seq OWNED BY public.rolepermission.id;

ALTER TABLE ONLY public.rolepermission ALTER COLUMN id SET DEFAULT nextval('public.rolepermission_id_seq'::regclass);

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT rolepermission_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX rolepermission_role_permission ON public.rolepermission USING btree (role, permission);

CREATE INDEX rolepermission_txn_no ON public.rolepermission USING btree (txn_no);

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT rolepermission_role_fkey FOREIGN KEY (role) REFERENCES public.role(code) ON DELETE CASCADE;

ALTER TABLE ONLY public.rolepermission
    ADD CONSTRAINT rolepermission_permission_fkey FOREIGN KEY (permission) REFERENCES public.permission(code) ON DELETE CASCADE;

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_role_fkey FOREIGN KEY (role) REFERENCES public.role(code);

-- Every grade change is logged, for reproducible transcripts.

CREATE TABLE public.gradechange (
    id bigserial PRIMARY KEY,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    enrolment_id bigint NOT NULL
        REFERENCES public.courseenrollment(id) ON DELETE CASCADE,
    old_grade character varying(2) NOT NULL,
    new_grade character varying(2) NOT NULL,
    changed_by character varying(40) NOT NULL,
    reason text
);

CREATE INDEX gradechange_enrolment_id ON public.gradechange USING btree (enrolment_id);

CREATE INDEX gradechange_txn_no ON public.gradechange USING btree (txn_no);

-- Evaluation components of a course offering (mid-sem, end-sem, lab, ...)
-- and each enrolled student's score (0-100) in them, uploaded with grades.

CREATE TABLE public.evalcomponent (
    id bigserial PRIMARY KEY,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    offering_id bigint NOT NULL
        REFERENCES public.courseoffering(id) ON DELETE CASCADE,
    code character varying(10) NOT NULL,
    label character varying(100) NOT NULL,
    weight numeric(5,2),
    UNIQUE (offering_id, code)
);

CREATE INDEX evalcomponent_txn_no ON public.evalcomponent USING btree (txn_no);

CREATE TABLE public.evalscore (
    id bigserial PRIMARY KEY,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    enrolment_id bigint NOT NULL
        REFERENCES public.courseenrollment(id) ON DELETE CASCADE,
    component_id bigint NOT NULL
        REFERENCES public.evalcomponent(id) ON DELETE CASCADE,
    score numeric(5,2) NOT NULL CHECK (score >= 0 AND score <= 100),
    UNIQUE (enrolment_id, component_id)
);

CREATE INDEX evalscore_component_id ON public.evalscore USING btree (component_id);

CREATE INDEX evalscore_txn_no ON public.evalscore USING btree (txn_no);

-- Roles and their permissions. The code checks permissions only; see
-- policy.py. Users holding permissions.manage edit these.

INSERT INTO public.role (code, label, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('STU', 'Student', false, 1, now(), now()),
    ('ACA', 'Academic Section', false, 1, now(), now()),
    ('FAC', 'Faculty', false, 1, now(), now()),
    ('HOD', 'Head of Dept.', false, 1, now(), now()),
    ('DEA', 'Dean of Academics', false, 1, now(), now()),
    ('SUP', 'Superuser', false, 1, now(), now()),
    ('GUE', 'Guest', false, 1, now(), now()),
    ('PLA', 'Placement Cell', false, 1, now(), now()),
    ('ADV', 'Advisor', false, 1, now(), now()),
    ('RES', 'Research Section', false, 1, now(), now());

INSERT INTO public.permission (code, description, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('app.access', 'Use the application: home page and reference lists', false, 1, now(), now()),
    ('settings.manage', 'View and change the settings', false, 1, now(), now()),
    ('permissions.manage', 'View and change roles and their permissions', false, 1, now(), now()),
    ('users.find', 'Search users', false, 1, now(), now()),
    ('users.lookup', 'Look up instructors and students by name or entry number', false, 1, now(), now()),
    ('users.view:own', 'View a user''s details and photo', false, 1, now(), now()),
    ('users.view:any', 'View a user''s details and photo', false, 1, now(), now()),
    ('users.edit:own', 'Edit a user; own: only one''s own names', false, 1, now(), now()),
    ('users.edit:any', 'Edit a user; own: only one''s own names', false, 1, now(), now()),
    ('users.bulk_add', 'Add users from a CSV file', false, 1, now(), now()),
    ('users.delete', 'Delete users', false, 1, now(), now()),
    ('users.view_active', 'See who is logged in', false, 1, now(), now()),
    ('students.find', 'Search students', false, 1, now(), now()),
    ('students.academics:own', 'View a student''s enrolments, grades and attendance', false, 1, now(), now()),
    ('students.academics:any', 'View a student''s enrolments, grades and attendance', false, 1, now(), now()),
    ('student_docs.upload', 'Upload a document to a student''s record', false, 1, now(), now()),
    ('student_docs.access:own', 'View and delete a student''s documents', false, 1, now(), now()),
    ('student_docs.access:any', 'View and delete a student''s documents', false, 1, now(), now()),
    ('fees.view:own', 'View a student''s fee payment records', false, 1, now(), now()),
    ('fees.view:any', 'View a student''s fee payment records', false, 1, now(), now()),
    ('fees.submit:own', 'Submit a student''s fee payment details', false, 1, now(), now()),
    ('fees.submit:any', 'Submit a student''s fee payment details', false, 1, now(), now()),
    ('fees.delete:own', 'Delete a student''s fee payment record', false, 1, now(), now()),
    ('fees.delete:any', 'Delete a student''s fee payment record', false, 1, now(), now()),
    ('fees.report', 'Fee payments report', false, 1, now(), now()),
    ('advisors.view', 'Find the batch advisor of a batch', false, 1, now(), now()),
    ('advisors.assign', 'Assign batch advisors', false, 1, now(), now()),
    ('instructors.view:own', 'View an instructor''s courses and advisor duties; own: one''s own', false, 1, now(), now()),
    ('instructors.view:any', 'View an instructor''s courses and advisor duties; own: one''s own', false, 1, now(), now()),
    ('faces.add', 'Add one''s own face photo', false, 1, now(), now()),
    ('faces.replace', 'Replace one''s own face photo once it is on record', false, 1, now(), now()),
    ('faces.bulk_add', 'Upload face photos of many users from a ZIP file', false, 1, now(), now()),
    ('courses.view', 'View and search courses', false, 1, now(), now()),
    ('courses.edit:own', 'Create courses and edit them; own: courses one authored; pg: PG and all-level courses', false, 1, now(), now()),
    ('courses.edit:pg', 'Create courses and edit them; own: courses one authored; pg: PG and all-level courses', false, 1, now(), now()),
    ('courses.edit:any', 'Create courses and edit them; own: courses one authored; pg: PG and all-level courses', false, 1, now(), now()),
    ('courses.edit_approved', 'Edit a course that is approved or retired', false, 1, now(), now()),
    ('courses.bulk_add', 'Add courses from a CSV file', false, 1, now(), now()),
    ('slots.manage', 'View and edit the course slot timings', false, 1, now(), now()),
    ('calendar.view', 'View the academic calendar', false, 1, now(), now()),
    ('calendar.edit', 'Edit the academic calendar', false, 1, now(), now()),
    ('offerings.view', 'View and search course offerings', false, 1, now(), now()),
    ('offerings.view_stats', 'View grade and attendance statistics of an offering', false, 1, now(), now()),
    ('offerings.view_running:own', 'List running offerings; own: the ones one teaches', false, 1, now(), now()),
    ('offerings.view_running:any', 'List running offerings; own: the ones one teaches', false, 1, now(), now()),
    ('offerings.edit:own', 'Create offerings and edit them; own: as coordinator; dept: of one''s department', false, 1, now(), now()),
    ('offerings.edit:dept', 'Create offerings and edit them; own: as coordinator; dept: of one''s department', false, 1, now(), now()),
    ('offerings.edit:any', 'Create offerings and edit them; own: as coordinator; dept: of one''s department', false, 1, now(), now()),
    ('offerings.edit_closed', 'Change an offering that has finished or been cancelled', false, 1, now(), now()),
    ('enrolments.enrol:own', 'Request enrolment in courses; own: for oneself', false, 1, now(), now()),
    ('enrolments.enrol:any', 'Request enrolment in courses; own: for oneself', false, 1, now(), now()),
    ('enrolments.change:own', 'Drop or withdraw an enrolment; own: one''s own', false, 1, now(), now()),
    ('enrolments.change:any', 'Drop or withdraw an enrolment; own: one''s own', false, 1, now(), now()),
    ('enrolments.edit:own', 'View and edit enrolments, overriding dates and statuses; own: in courses one coordinates; dept: in offerings of one''s department', false, 1, now(), now()),
    ('enrolments.edit:dept', 'View and edit enrolments, overriding dates and statuses; own: in courses one coordinates; dept: in offerings of one''s department', false, 1, now(), now()),
    ('enrolments.edit:any', 'View and edit enrolments, overriding dates and statuses; own: in courses one coordinates; dept: in offerings of one''s department', false, 1, now(), now()),
    ('enrolments.approve:own', 'Approve enrolments; own: as instructor or batch advisor; any: as advisor for any enrolment', false, 1, now(), now()),
    ('enrolments.approve:any', 'Approve enrolments; own: as instructor or batch advisor; any: as advisor for any enrolment', false, 1, now(), now()),
    ('enrolments.pending_instructor', 'List enrolments awaiting one''s approval as instructor', false, 1, now(), now()),
    ('enrolments.pending_advisor:own', 'List enrolments awaiting approval; own: as batch advisor; dept: PhD students of one''s department', false, 1, now(), now()),
    ('enrolments.pending_advisor:dept', 'List enrolments awaiting approval; own: as batch advisor; dept: PhD students of one''s department', false, 1, now(), now()),
    ('enrolments.bulk_enrol', 'Enrol a batch of students in a course', false, 1, now(), now()),
    ('enrolments.download', 'Download enrolment lists', false, 1, now(), now()),
    ('grades.upload:own', 'Upload grades; own: for courses one coordinates', false, 1, now(), now()),
    ('grades.upload:any', 'Upload grades; own: for courses one coordinates', false, 1, now(), now()),
    ('grades.reports', 'Grade sheets, degree certificates and grade submission status', false, 1, now(), now()),
    ('grades.distribution', 'Course-wise grade distribution report', false, 1, now(), now()),
    ('grades.cgpa_report', 'CGPA and SGPA report', false, 1, now(), now()),
    ('sessions.close', 'Close an academic session, freezing its credits and grades', false, 1, now(), now()),
    ('credits.reports', 'Earned credits reports', false, 1, now(), now()),
    ('credits.generate', 'Generate students'' credits data', false, 1, now(), now()),
    ('credits.notify_violation', 'Email students about credit requirement violations', false, 1, now(), now()),
    ('reports.course_enrolments', 'Course enrolments report', false, 1, now(), now()),
    ('reports.student_strength', 'Degree/course-wise student strength report', false, 1, now(), now()),
    ('reports.student_strength_download', 'Download degree-wise student lists', false, 1, now(), now()),
    ('reports.students_list', 'Download student lists for placement', false, 1, now(), now()),
    ('attendance.mark:own', 'Upload attendance photos; own: for courses one coordinates', false, 1, now(), now()),
    ('attendance.mark:any', 'Upload attendance photos; own: for courses one coordinates', false, 1, now(), now()),
    ('attendance.view:own', 'View a course''s attendance; own: of courses one teaches', false, 1, now(), now()),
    ('attendance.view:any', 'View a course''s attendance; own: of courses one teaches', false, 1, now(), now()),
    ('feedback.view_forms', 'View feedback forms', false, 1, now(), now()),
    ('feedback.manage_forms', 'Create and edit feedback forms', false, 1, now(), now()),
    ('feedback.submit', 'Submit course feedback as a student', false, 1, now(), now()),
    ('feedback.view_instructor:own', 'View an instructor''s feedback; own: one''s own', false, 1, now(), now()),
    ('feedback.view_instructor:any', 'View an instructor''s feedback; own: one''s own', false, 1, now(), now()),
    ('feedback.reports', 'Feedback reports', false, 1, now(), now()),
    ('dc.view:own', 'View and search doctoral committees; own: one''s own', false, 1, now(), now()),
    ('dc.view:any', 'View and search doctoral committees; own: one''s own', false, 1, now(), now()),
    ('dc.edit:own', 'Propose and edit doctoral committees; own: as supervisor; dept: of one''s department', false, 1, now(), now()),
    ('dc.edit:dept', 'Propose and edit doctoral committees; own: as supervisor; dept: of one''s department', false, 1, now(), now()),
    ('dc.edit:any', 'Propose and edit doctoral committees; own: as supervisor; dept: of one''s department', false, 1, now(), now()),
    ('ppr.view:own', 'View PhD progress reports; own: as a DC member of the student', false, 1, now(), now()),
    ('ppr.view:any', 'View PhD progress reports; own: as a DC member of the student', false, 1, now(), now()),
    ('ppr.edit:own', 'Submit PhD progress reports; own: as a DC member of the student; any: also set any status', false, 1, now(), now()),
    ('ppr.edit:any', 'Submit PhD progress reports; own: as a DC member of the student; any: also set any status', false, 1, now(), now()),
    ('wfnotes.view', 'View workflow notes', false, 1, now(), now()),
    ('wfnotes.edit', 'Add and delete one''s workflow notes', false, 1, now(), now()),
    ('roster.student', 'Counts as a student: found by entry-number lookups, bulk enrolment, grade sheets and student lists', false, 1, now(), now()),
    ('roster.instructor', 'Counts as an instructor: offered in the instructor lookup, can supervise a DC', false, 1, now(), now()),
    ('roster.acad_section', 'Counts as the academic section: receives grade submission emails', false, 1, now(), now());

INSERT INTO public.rolepermission (role, permission, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('STU', 'roster.student', false, 1, now(), now()),
    ('FAC', 'roster.instructor', false, 1, now(), now()),
    ('ACA', 'roster.acad_section', false, 1, now(), now()),
    ('STU', 'advisors.view', false, 1, now(), now()),
    ('STU', 'app.access', false, 1, now(), now()),
    ('STU', 'calendar.view', false, 1, now(), now()),
    ('STU', 'courses.view', false, 1, now(), now()),
    ('STU', 'dc.view:own', false, 1, now(), now()),
    ('STU', 'enrolments.change:own', false, 1, now(), now()),
    ('STU', 'enrolments.enrol:own', false, 1, now(), now()),
    ('STU', 'faces.add', false, 1, now(), now()),
    ('STU', 'feedback.submit', false, 1, now(), now()),
    ('STU', 'feedback.view_forms', false, 1, now(), now()),
    ('STU', 'fees.delete:own', false, 1, now(), now()),
    ('STU', 'fees.submit:own', false, 1, now(), now()),
    ('STU', 'fees.view:own', false, 1, now(), now()),
    ('STU', 'offerings.view', false, 1, now(), now()),
    ('STU', 'offerings.view_running:own', false, 1, now(), now()),
    ('STU', 'student_docs.access:own', false, 1, now(), now()),
    ('STU', 'students.academics:own', false, 1, now(), now()),
    ('STU', 'users.edit:own', false, 1, now(), now()),
    ('STU', 'users.lookup', false, 1, now(), now()),
    ('STU', 'users.view:own', false, 1, now(), now()),
    ('STU', 'wfnotes.view', false, 1, now(), now()),
    ('ACA', 'advisors.assign', false, 1, now(), now()),
    ('ACA', 'advisors.view', false, 1, now(), now()),
    ('ACA', 'app.access', false, 1, now(), now()),
    ('ACA', 'attendance.mark:any', false, 1, now(), now()),
    ('ACA', 'attendance.view:any', false, 1, now(), now()),
    ('ACA', 'calendar.edit', false, 1, now(), now()),
    ('ACA', 'calendar.view', false, 1, now(), now()),
    ('ACA', 'courses.bulk_add', false, 1, now(), now()),
    ('ACA', 'courses.edit:any', false, 1, now(), now()),
    ('ACA', 'courses.edit_approved', false, 1, now(), now()),
    ('ACA', 'courses.view', false, 1, now(), now()),
    ('ACA', 'credits.generate', false, 1, now(), now()),
    ('ACA', 'credits.notify_violation', false, 1, now(), now()),
    ('ACA', 'credits.reports', false, 1, now(), now()),
    ('ACA', 'dc.edit:any', false, 1, now(), now()),
    ('ACA', 'dc.view:any', false, 1, now(), now()),
    ('ACA', 'enrolments.approve:any', false, 1, now(), now()),
    ('ACA', 'enrolments.bulk_enrol', false, 1, now(), now()),
    ('ACA', 'enrolments.change:any', false, 1, now(), now()),
    ('ACA', 'enrolments.download', false, 1, now(), now()),
    ('ACA', 'enrolments.edit:any', false, 1, now(), now()),
    ('ACA', 'enrolments.enrol:any', false, 1, now(), now()),
    ('ACA', 'enrolments.pending_advisor:own', false, 1, now(), now()),
    ('ACA', 'enrolments.pending_instructor', false, 1, now(), now()),
    ('ACA', 'faces.add', false, 1, now(), now()),
    ('ACA', 'faces.bulk_add', false, 1, now(), now()),
    ('ACA', 'faces.replace', false, 1, now(), now()),
    ('ACA', 'feedback.manage_forms', false, 1, now(), now()),
    ('ACA', 'feedback.reports', false, 1, now(), now()),
    ('ACA', 'feedback.view_forms', false, 1, now(), now()),
    ('ACA', 'feedback.view_instructor:any', false, 1, now(), now()),
    ('ACA', 'fees.delete:any', false, 1, now(), now()),
    ('ACA', 'fees.report', false, 1, now(), now()),
    ('ACA', 'fees.submit:any', false, 1, now(), now()),
    ('ACA', 'fees.view:any', false, 1, now(), now()),
    ('ACA', 'grades.cgpa_report', false, 1, now(), now()),
    ('ACA', 'grades.distribution', false, 1, now(), now()),
    ('ACA', 'grades.reports', false, 1, now(), now()),
    ('ACA', 'grades.upload:any', false, 1, now(), now()),
    ('ACA', 'instructors.view:any', false, 1, now(), now()),
    ('ACA', 'offerings.edit:any', false, 1, now(), now()),
    ('ACA', 'offerings.edit_closed', false, 1, now(), now()),
    ('ACA', 'offerings.view', false, 1, now(), now()),
    ('ACA', 'offerings.view_running:any', false, 1, now(), now()),
    ('ACA', 'offerings.view_stats', false, 1, now(), now()),
    ('ACA', 'ppr.edit:any', false, 1, now(), now()),
    ('ACA', 'ppr.view:any', false, 1, now(), now()),
    ('ACA', 'reports.course_enrolments', false, 1, now(), now()),
    ('ACA', 'reports.student_strength', false, 1, now(), now()),
    ('ACA', 'reports.student_strength_download', false, 1, now(), now()),
    ('ACA', 'sessions.close', false, 1, now(), now()),
    ('ACA', 'slots.manage', false, 1, now(), now()),
    ('ACA', 'student_docs.access:any', false, 1, now(), now()),
    ('ACA', 'student_docs.upload', false, 1, now(), now()),
    ('ACA', 'students.academics:any', false, 1, now(), now()),
    ('ACA', 'students.find', false, 1, now(), now()),
    ('ACA', 'users.bulk_add', false, 1, now(), now()),
    ('ACA', 'users.edit:any', false, 1, now(), now()),
    ('ACA', 'users.find', false, 1, now(), now()),
    ('ACA', 'users.lookup', false, 1, now(), now()),
    ('ACA', 'users.view:any', false, 1, now(), now()),
    ('ACA', 'users.view_active', false, 1, now(), now()),
    ('ACA', 'wfnotes.edit', false, 1, now(), now()),
    ('ACA', 'wfnotes.view', false, 1, now(), now()),
    ('FAC', 'advisors.view', false, 1, now(), now()),
    ('FAC', 'app.access', false, 1, now(), now()),
    ('FAC', 'attendance.mark:own', false, 1, now(), now()),
    ('FAC', 'attendance.view:own', false, 1, now(), now()),
    ('FAC', 'calendar.view', false, 1, now(), now()),
    ('FAC', 'courses.edit:own', false, 1, now(), now()),
    ('FAC', 'courses.view', false, 1, now(), now()),
    ('FAC', 'credits.reports', false, 1, now(), now()),
    ('FAC', 'dc.edit:own', false, 1, now(), now()),
    ('FAC', 'dc.view:any', false, 1, now(), now()),
    ('FAC', 'enrolments.approve:own', false, 1, now(), now()),
    ('FAC', 'enrolments.change:any', false, 1, now(), now()),
    ('FAC', 'enrolments.download', false, 1, now(), now()),
    ('FAC', 'enrolments.edit:own', false, 1, now(), now()),
    ('FAC', 'enrolments.pending_instructor', false, 1, now(), now()),
    ('FAC', 'faces.add', false, 1, now(), now()),
    ('FAC', 'faces.replace', false, 1, now(), now()),
    ('FAC', 'feedback.view_forms', false, 1, now(), now()),
    ('FAC', 'feedback.view_instructor:own', false, 1, now(), now()),
    ('FAC', 'fees.delete:own', false, 1, now(), now()),
    ('FAC', 'fees.submit:any', false, 1, now(), now()),
    ('FAC', 'fees.view:any', false, 1, now(), now()),
    ('FAC', 'grades.upload:own', false, 1, now(), now()),
    ('FAC', 'instructors.view:own', false, 1, now(), now()),
    ('FAC', 'offerings.edit:own', false, 1, now(), now()),
    ('FAC', 'offerings.view', false, 1, now(), now()),
    ('FAC', 'offerings.view_running:own', false, 1, now(), now()),
    ('FAC', 'offerings.view_stats', false, 1, now(), now()),
    ('FAC', 'ppr.edit:own', false, 1, now(), now()),
    ('FAC', 'ppr.view:own', false, 1, now(), now()),
    ('FAC', 'student_docs.access:own', false, 1, now(), now()),
    ('FAC', 'student_docs.upload', false, 1, now(), now()),
    ('FAC', 'students.academics:any', false, 1, now(), now()),
    ('FAC', 'students.find', false, 1, now(), now()),
    ('FAC', 'users.edit:own', false, 1, now(), now()),
    ('FAC', 'users.find', false, 1, now(), now()),
    ('FAC', 'users.lookup', false, 1, now(), now()),
    ('FAC', 'users.view:any', false, 1, now(), now()),
    ('FAC', 'wfnotes.edit', false, 1, now(), now()),
    ('FAC', 'wfnotes.view', false, 1, now(), now()),
    ('HOD', 'advisors.view', false, 1, now(), now()),
    ('HOD', 'app.access', false, 1, now(), now()),
    ('HOD', 'attendance.view:any', false, 1, now(), now()),
    ('HOD', 'calendar.view', false, 1, now(), now()),
    ('HOD', 'courses.edit:any', false, 1, now(), now()),
    ('HOD', 'courses.view', false, 1, now(), now()),
    ('HOD', 'credits.reports', false, 1, now(), now()),
    ('HOD', 'dc.edit:dept', false, 1, now(), now()),
    ('HOD', 'dc.view:any', false, 1, now(), now()),
    ('HOD', 'enrolments.approve:any', false, 1, now(), now()),
    ('HOD', 'enrolments.approve:own', false, 1, now(), now()),
    ('HOD', 'enrolments.change:any', false, 1, now(), now()),
    ('HOD', 'enrolments.download', false, 1, now(), now()),
    ('HOD', 'enrolments.edit:dept', false, 1, now(), now()),
    ('HOD', 'enrolments.pending_advisor:dept', false, 1, now(), now()),
    ('HOD', 'faces.add', false, 1, now(), now()),
    ('HOD', 'faces.replace', false, 1, now(), now()),
    ('HOD', 'feedback.view_forms', false, 1, now(), now()),
    ('HOD', 'fees.delete:own', false, 1, now(), now()),
    ('HOD', 'fees.submit:any', false, 1, now(), now()),
    ('HOD', 'fees.view:any', false, 1, now(), now()),
    ('HOD', 'instructors.view:any', false, 1, now(), now()),
    ('HOD', 'offerings.edit:dept', false, 1, now(), now()),
    ('HOD', 'offerings.view', false, 1, now(), now()),
    ('HOD', 'offerings.view_running:own', false, 1, now(), now()),
    ('HOD', 'offerings.view_stats', false, 1, now(), now()),
    ('HOD', 'ppr.edit:own', false, 1, now(), now()),
    ('HOD', 'ppr.view:own', false, 1, now(), now()),
    ('HOD', 'reports.student_strength_download', false, 1, now(), now()),
    ('HOD', 'student_docs.access:own', false, 1, now(), now()),
    ('HOD', 'student_docs.upload', false, 1, now(), now()),
    ('HOD', 'students.academics:any', false, 1, now(), now()),
    ('HOD', 'students.find', false, 1, now(), now()),
    ('HOD', 'users.edit:own', false, 1, now(), now()),
    ('HOD', 'users.find', false, 1, now(), now()),
    ('HOD', 'users.lookup', false, 1, now(), now()),
    ('HOD', 'users.view:any', false, 1, now(), now()),
    ('HOD', 'wfnotes.edit', false, 1, now(), now()),
    ('HOD', 'wfnotes.view', false, 1, now(), now()),
    ('DEA', 'advisors.assign', false, 1, now(), now()),
    ('DEA', 'advisors.view', false, 1, now(), now()),
    ('DEA', 'app.access', false, 1, now(), now()),
    ('DEA', 'attendance.view:any', false, 1, now(), now()),
    ('DEA', 'calendar.edit', false, 1, now(), now()),
    ('DEA', 'calendar.view', false, 1, now(), now()),
    ('DEA', 'courses.bulk_add', false, 1, now(), now()),
    ('DEA', 'courses.edit:any', false, 1, now(), now()),
    ('DEA', 'courses.edit_approved', false, 1, now(), now()),
    ('DEA', 'courses.view', false, 1, now(), now()),
    ('DEA', 'credits.generate', false, 1, now(), now()),
    ('DEA', 'credits.reports', false, 1, now(), now()),
    ('DEA', 'dc.edit:any', false, 1, now(), now()),
    ('DEA', 'dc.view:any', false, 1, now(), now()),
    ('DEA', 'enrolments.approve:any', false, 1, now(), now()),
    ('DEA', 'enrolments.bulk_enrol', false, 1, now(), now()),
    ('DEA', 'enrolments.change:any', false, 1, now(), now()),
    ('DEA', 'enrolments.download', false, 1, now(), now()),
    ('DEA', 'enrolments.edit:any', false, 1, now(), now()),
    ('DEA', 'enrolments.pending_advisor:own', false, 1, now(), now()),
    ('DEA', 'enrolments.pending_instructor', false, 1, now(), now()),
    ('DEA', 'faces.add', false, 1, now(), now()),
    ('DEA', 'faces.replace', false, 1, now(), now()),
    ('DEA', 'feedback.manage_forms', false, 1, now(), now()),
    ('DEA', 'feedback.reports', false, 1, now(), now()),
    ('DEA', 'feedback.view_forms', false, 1, now(), now()),
    ('DEA', 'feedback.view_instructor:any', false, 1, now(), now()),
    ('DEA', 'fees.delete:any', false, 1, now(), now()),
    ('DEA', 'fees.report', false, 1, now(), now()),
    ('DEA', 'fees.submit:any', false, 1, now(), now()),
    ('DEA', 'fees.view:any', false, 1, now(), now()),
    ('DEA', 'grades.cgpa_report', false, 1, now(), now()),
    ('DEA', 'grades.distribution', false, 1, now(), now()),
    ('DEA', 'grades.reports', false, 1, now(), now()),
    ('DEA', 'grades.upload:any', false, 1, now(), now()),
    ('DEA', 'instructors.view:any', false, 1, now(), now()),
    ('DEA', 'offerings.edit:any', false, 1, now(), now()),
    ('DEA', 'offerings.edit_closed', false, 1, now(), now()),
    ('DEA', 'offerings.view', false, 1, now(), now()),
    ('DEA', 'offerings.view_running:any', false, 1, now(), now()),
    ('DEA', 'offerings.view_stats', false, 1, now(), now()),
    ('DEA', 'ppr.edit:any', false, 1, now(), now()),
    ('DEA', 'ppr.view:any', false, 1, now(), now()),
    ('DEA', 'reports.course_enrolments', false, 1, now(), now()),
    ('DEA', 'reports.student_strength', false, 1, now(), now()),
    ('DEA', 'reports.student_strength_download', false, 1, now(), now()),
    ('DEA', 'slots.manage', false, 1, now(), now()),
    ('DEA', 'student_docs.access:any', false, 1, now(), now()),
    ('DEA', 'student_docs.upload', false, 1, now(), now()),
    ('DEA', 'students.academics:any', false, 1, now(), now()),
    ('DEA', 'students.find', false, 1, now(), now()),
    ('DEA', 'users.edit:own', false, 1, now(), now()),
    ('DEA', 'users.find', false, 1, now(), now()),
    ('DEA', 'users.lookup', false, 1, now(), now()),
    ('DEA', 'users.view:any', false, 1, now(), now()),
    ('DEA', 'users.view_active', false, 1, now(), now()),
    ('DEA', 'wfnotes.edit', false, 1, now(), now()),
    ('DEA', 'wfnotes.view', false, 1, now(), now()),
    ('SUP', 'advisors.assign', false, 1, now(), now()),
    ('SUP', 'advisors.view', false, 1, now(), now()),
    ('SUP', 'app.access', false, 1, now(), now()),
    ('SUP', 'attendance.view:any', false, 1, now(), now()),
    ('SUP', 'calendar.edit', false, 1, now(), now()),
    ('SUP', 'calendar.view', false, 1, now(), now()),
    ('SUP', 'courses.bulk_add', false, 1, now(), now()),
    ('SUP', 'courses.edit:any', false, 1, now(), now()),
    ('SUP', 'courses.view', false, 1, now(), now()),
    ('SUP', 'credits.notify_violation', false, 1, now(), now()),
    ('SUP', 'credits.reports', false, 1, now(), now()),
    ('SUP', 'dc.view:any', false, 1, now(), now()),
    ('SUP', 'enrolments.change:any', false, 1, now(), now()),
    ('SUP', 'enrolments.download', false, 1, now(), now()),
    ('SUP', 'faces.add', false, 1, now(), now()),
    ('SUP', 'faces.replace', false, 1, now(), now()),
    ('SUP', 'feedback.view_forms', false, 1, now(), now()),
    ('SUP', 'fees.delete:any', false, 1, now(), now()),
    ('SUP', 'fees.submit:any', false, 1, now(), now()),
    ('SUP', 'fees.view:any', false, 1, now(), now()),
    ('SUP', 'grades.reports', false, 1, now(), now()),
    ('SUP', 'offerings.edit:any', false, 1, now(), now()),
    ('SUP', 'offerings.view', false, 1, now(), now()),
    ('SUP', 'offerings.view_running:any', false, 1, now(), now()),
    ('SUP', 'offerings.view_stats', false, 1, now(), now()),
    ('SUP', 'permissions.manage', false, 1, now(), now()),
    ('SUP', 'ppr.edit:any', false, 1, now(), now()),
    ('SUP', 'ppr.view:any', false, 1, now(), now()),
    ('SUP', 'sessions.close', false, 1, now(), now()),
    ('SUP', 'settings.manage', false, 1, now(), now()),
    ('SUP', 'student_docs.access:own', false, 1, now(), now()),
    ('SUP', 'student_docs.upload', false, 1, now(), now()),
    ('SUP', 'slots.manage', false, 1, now(), now()),
    ('SUP', 'students.academics:any', false, 1, now(), now()),
    ('SUP', 'students.find', false, 1, now(), now()),
    ('SUP', 'users.bulk_add', false, 1, now(), now()),
    ('SUP', 'users.delete', false, 1, now(), now()),
    ('SUP', 'users.edit:any', false, 1, now(), now()),
    ('SUP', 'users.find', false, 1, now(), now()),
    ('SUP', 'users.lookup', false, 1, now(), now()),
    ('SUP', 'users.view:any', false, 1, now(), now()),
    ('SUP', 'users.view_active', false, 1, now(), now()),
    ('SUP', 'wfnotes.edit', false, 1, now(), now()),
    ('SUP', 'wfnotes.view', false, 1, now(), now()),
    ('GUE', 'advisors.view', false, 1, now(), now()),
    ('GUE', 'app.access', false, 1, now(), now()),
    ('GUE', 'attendance.view:own', false, 1, now(), now()),
    ('GUE', 'calendar.view', false, 1, now(), now()),
    ('GUE', 'courses.view', false, 1, now(), now()),
    ('GUE', 'credits.reports', false, 1, now(), now()),
    ('GUE', 'dc.view:any', false, 1, now(), now()),
    ('GUE', 'enrolments.change:any', false, 1, now(), now()),
    ('GUE', 'enrolments.download', false, 1, now(), now()),
    ('GUE', 'faces.add', false, 1, now(), now()),
    ('GUE', 'faces.replace', false, 1, now(), now()),
    ('GUE', 'feedback.view_forms', false, 1, now(), now()),
    ('GUE', 'fees.delete:own', false, 1, now(), now()),
    ('GUE', 'fees.submit:any', false, 1, now(), now()),
    ('GUE', 'fees.view:any', false, 1, now(), now()),
    ('GUE', 'grades.cgpa_report', false, 1, now(), now()),
    ('GUE', 'offerings.view', false, 1, now(), now()),
    ('GUE', 'offerings.view_running:own', false, 1, now(), now()),
    ('GUE', 'offerings.view_stats', false, 1, now(), now()),
    ('GUE', 'ppr.edit:own', false, 1, now(), now()),
    ('GUE', 'ppr.view:own', false, 1, now(), now()),
    ('GUE', 'student_docs.access:own', false, 1, now(), now()),
    ('GUE', 'student_docs.upload', false, 1, now(), now()),
    ('GUE', 'students.academics:any', false, 1, now(), now()),
    ('GUE', 'students.find', false, 1, now(), now()),
    ('GUE', 'users.edit:own', false, 1, now(), now()),
    ('GUE', 'users.find', false, 1, now(), now()),
    ('GUE', 'users.lookup', false, 1, now(), now()),
    ('GUE', 'users.view:any', false, 1, now(), now()),
    ('GUE', 'wfnotes.edit', false, 1, now(), now()),
    ('GUE', 'wfnotes.view', false, 1, now(), now()),
    ('PLA', 'advisors.view', false, 1, now(), now()),
    ('PLA', 'app.access', false, 1, now(), now()),
    ('PLA', 'calendar.view', false, 1, now(), now()),
    ('PLA', 'courses.view', false, 1, now(), now()),
    ('PLA', 'credits.reports', false, 1, now(), now()),
    ('PLA', 'dc.view:any', false, 1, now(), now()),
    ('PLA', 'enrolments.change:any', false, 1, now(), now()),
    ('PLA', 'enrolments.download', false, 1, now(), now()),
    ('PLA', 'faces.add', false, 1, now(), now()),
    ('PLA', 'faces.replace', false, 1, now(), now()),
    ('PLA', 'feedback.view_forms', false, 1, now(), now()),
    ('PLA', 'fees.delete:own', false, 1, now(), now()),
    ('PLA', 'fees.submit:any', false, 1, now(), now()),
    ('PLA', 'fees.view:any', false, 1, now(), now()),
    ('PLA', 'offerings.view', false, 1, now(), now()),
    ('PLA', 'offerings.view_running:own', false, 1, now(), now()),
    ('PLA', 'offerings.view_stats', false, 1, now(), now()),
    ('PLA', 'ppr.edit:own', false, 1, now(), now()),
    ('PLA', 'ppr.view:own', false, 1, now(), now()),
    ('PLA', 'reports.students_list', false, 1, now(), now()),
    ('PLA', 'student_docs.access:own', false, 1, now(), now()),
    ('PLA', 'student_docs.upload', false, 1, now(), now()),
    ('PLA', 'students.academics:any', false, 1, now(), now()),
    ('PLA', 'students.find', false, 1, now(), now()),
    ('PLA', 'users.edit:own', false, 1, now(), now()),
    ('PLA', 'users.find', false, 1, now(), now()),
    ('PLA', 'users.lookup', false, 1, now(), now()),
    ('PLA', 'users.view:any', false, 1, now(), now()),
    ('PLA', 'wfnotes.edit', false, 1, now(), now()),
    ('PLA', 'wfnotes.view', false, 1, now(), now()),
    ('ADV', 'advisors.view', false, 1, now(), now()),
    ('ADV', 'app.access', false, 1, now(), now()),
    ('ADV', 'attendance.view:own', false, 1, now(), now()),
    ('ADV', 'calendar.view', false, 1, now(), now()),
    ('ADV', 'courses.view', false, 1, now(), now()),
    ('ADV', 'credits.reports', false, 1, now(), now()),
    ('ADV', 'dc.view:any', false, 1, now(), now()),
    ('ADV', 'enrolments.approve:own', false, 1, now(), now()),
    ('ADV', 'enrolments.change:any', false, 1, now(), now()),
    ('ADV', 'enrolments.download', false, 1, now(), now()),
    ('ADV', 'enrolments.pending_advisor:own', false, 1, now(), now()),
    ('ADV', 'faces.add', false, 1, now(), now()),
    ('ADV', 'faces.replace', false, 1, now(), now()),
    ('ADV', 'feedback.view_forms', false, 1, now(), now()),
    ('ADV', 'fees.delete:own', false, 1, now(), now()),
    ('ADV', 'fees.submit:any', false, 1, now(), now()),
    ('ADV', 'fees.view:any', false, 1, now(), now()),
    ('ADV', 'offerings.view', false, 1, now(), now()),
    ('ADV', 'offerings.view_running:own', false, 1, now(), now()),
    ('ADV', 'offerings.view_stats', false, 1, now(), now()),
    ('ADV', 'ppr.edit:own', false, 1, now(), now()),
    ('ADV', 'ppr.view:own', false, 1, now(), now()),
    ('ADV', 'student_docs.access:own', false, 1, now(), now()),
    ('ADV', 'student_docs.upload', false, 1, now(), now()),
    ('ADV', 'students.academics:any', false, 1, now(), now()),
    ('ADV', 'students.find', false, 1, now(), now()),
    ('ADV', 'users.edit:own', false, 1, now(), now()),
    ('ADV', 'users.find', false, 1, now(), now()),
    ('ADV', 'users.lookup', false, 1, now(), now()),
    ('ADV', 'users.view:any', false, 1, now(), now()),
    ('ADV', 'wfnotes.edit', false, 1, now(), now()),
    ('ADV', 'wfnotes.view', false, 1, now(), now()),
    ('RES', 'advisors.view', false, 1, now(), now()),
    ('RES', 'app.access', false, 1, now(), now()),
    ('RES', 'attendance.view:own', false, 1, now(), now()),
    ('RES', 'calendar.view', false, 1, now(), now()),
    ('RES', 'courses.edit:pg', false, 1, now(), now()),
    ('RES', 'courses.edit_approved', false, 1, now(), now()),
    ('RES', 'courses.view', false, 1, now(), now()),
    ('RES', 'credits.reports', false, 1, now(), now()),
    ('RES', 'dc.view:any', false, 1, now(), now()),
    ('RES', 'enrolments.change:any', false, 1, now(), now()),
    ('RES', 'enrolments.download', false, 1, now(), now()),
    ('RES', 'faces.add', false, 1, now(), now()),
    ('RES', 'faces.replace', false, 1, now(), now()),
    ('RES', 'feedback.view_forms', false, 1, now(), now()),
    ('RES', 'fees.delete:own', false, 1, now(), now()),
    ('RES', 'fees.submit:any', false, 1, now(), now()),
    ('RES', 'fees.view:any', false, 1, now(), now()),
    ('RES', 'offerings.view', false, 1, now(), now()),
    ('RES', 'offerings.view_running:own', false, 1, now(), now()),
    ('RES', 'offerings.view_stats', false, 1, now(), now()),
    ('RES', 'ppr.edit:own', false, 1, now(), now()),
    ('RES', 'ppr.view:own', false, 1, now(), now()),
    ('RES', 'student_docs.access:own', false, 1, now(), now()),
    ('RES', 'student_docs.upload', false, 1, now(), now()),
    ('RES', 'students.academics:any', false, 1, now(), now()),
    ('RES', 'students.find', false, 1, now(), now()),
    ('RES', 'users.edit:own', false, 1, now(), now()),
    ('RES', 'users.find', false, 1, now(), now()),
    ('RES', 'users.lookup', false, 1, now(), now()),
    ('RES', 'users.view:any', false, 1, now(), now()),
    ('RES', 'wfnotes.edit', false, 1, now(), now()),
    ('RES', 'wfnotes.view', false, 1, now(), now());


-- The lists that differ between universities are edited on the Lists screen
-- (/vocab_save). Only the department wildcard that the code relies on is seeded.

INSERT INTO public.vocabitem (vocab, code, label, sort_order, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('Departments', 'ALL', 'All Departments', 0, false, 1, now(), now());
