--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2 (Debian 17.2-1.pgdg120+1)
-- Dumped by pg_dump version 17.2 (Debian 17.2-1.pgdg120+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: academiccalendar; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.academiccalendar OWNER TO app_user;

--
-- Name: academiccalendar_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.academiccalendar_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.academiccalendar_id_seq OWNER TO app_user;

--
-- Name: academiccalendar_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.academiccalendar_id_seq OWNED BY public.academiccalendar.id;


--
-- Name: academicmilestone; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.academicmilestone OWNER TO app_user;

--
-- Name: academicmilestone_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.academicmilestone_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.academicmilestone_id_seq OWNER TO app_user;

--
-- Name: academicmilestone_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.academicmilestone_id_seq OWNED BY public.academicmilestone.id;


--
-- Name: attendancephoto; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.attendancephoto OWNER TO app_user;

--
-- Name: attendancephoto_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.attendancephoto_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.attendancephoto_id_seq OWNER TO app_user;

--
-- Name: attendancephoto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.attendancephoto_id_seq OWNED BY public.attendancephoto.id;


--
-- Name: batchadvisors; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.batchadvisors OWNER TO app_user;

--
-- Name: batchadvisors_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.batchadvisors_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.batchadvisors_id_seq OWNER TO app_user;

--
-- Name: batchadvisors_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.batchadvisors_id_seq OWNED BY public.batchadvisors.id;


--
-- Name: course; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.course OWNER TO app_user;

--
-- Name: course_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.course_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.course_id_seq OWNER TO app_user;

--
-- Name: course_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.course_id_seq OWNED BY public.course.id;


--
-- Name: coursecategory; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.coursecategory OWNER TO app_user;

--
-- Name: coursecategory_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.coursecategory_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.coursecategory_id_seq OWNER TO app_user;

--
-- Name: coursecategory_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.coursecategory_id_seq OWNED BY public.coursecategory.id;


--
-- Name: courseenrollment; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.courseenrollment OWNER TO app_user;

--
-- Name: courseenrollment_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.courseenrollment_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.courseenrollment_id_seq OWNER TO app_user;

--
-- Name: courseenrollment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.courseenrollment_id_seq OWNED BY public.courseenrollment.id;


--
-- Name: courseinstructor; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.courseinstructor OWNER TO app_user;

--
-- Name: courseinstructor_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.courseinstructor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.courseinstructor_id_seq OWNER TO app_user;

--
-- Name: courseinstructor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.courseinstructor_id_seq OWNED BY public.courseinstructor.id;


--
-- Name: courseinstructorfeedback; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.courseinstructorfeedback OWNER TO app_user;

--
-- Name: courseinstructorfeedback_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.courseinstructorfeedback_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.courseinstructorfeedback_id_seq OWNER TO app_user;

--
-- Name: courseinstructorfeedback_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.courseinstructorfeedback_id_seq OWNED BY public.courseinstructorfeedback.id;


--
-- Name: courseoffering; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.courseoffering OWNER TO app_user;

--
-- Name: courseoffering_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.courseoffering_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.courseoffering_id_seq OWNER TO app_user;

--
-- Name: courseoffering_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.courseoffering_id_seq OWNED BY public.courseoffering.id;


--
-- Name: courseslottiming; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.courseslottiming OWNER TO app_user;

--
-- Name: courseslottiming_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.courseslottiming_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.courseslottiming_id_seq OWNER TO app_user;

--
-- Name: courseslottiming_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.courseslottiming_id_seq OWNED BY public.courseslottiming.id;


--
-- Name: dcforstudent; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.dcforstudent OWNER TO app_user;

--
-- Name: dcforstudent_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.dcforstudent_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dcforstudent_id_seq OWNER TO app_user;

--
-- Name: dcforstudent_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.dcforstudent_id_seq OWNED BY public.dcforstudent.id;


--
-- Name: dcmember; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.dcmember OWNER TO app_user;

--
-- Name: dcmember_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.dcmember_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.dcmember_id_seq OWNER TO app_user;

--
-- Name: dcmember_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.dcmember_id_seq OWNED BY public.dcmember.id;


--
-- Name: feedbackform; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.feedbackform OWNER TO app_user;

--
-- Name: feedbackform_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.feedbackform_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feedbackform_id_seq OWNER TO app_user;

--
-- Name: feedbackform_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.feedbackform_id_seq OWNED BY public.feedbackform.id;


--
-- Name: feedbackquestion; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.feedbackquestion OWNER TO app_user;

--
-- Name: feedbackquestion_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.feedbackquestion_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feedbackquestion_id_seq OWNER TO app_user;

--
-- Name: feedbackquestion_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.feedbackquestion_id_seq OWNED BY public.feedbackquestion.id;


--
-- Name: feestransaction; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.feestransaction OWNER TO app_user;

--
-- Name: feestransaction_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.feestransaction_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.feestransaction_id_seq OWNER TO app_user;

--
-- Name: feestransaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.feestransaction_id_seq OWNED BY public.feestransaction.id;


--
-- Name: knownface; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.knownface OWNER TO app_user;

--
-- Name: knownface_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.knownface_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.knownface_id_seq OWNER TO app_user;

--
-- Name: knownface_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.knownface_id_seq OWNED BY public.knownface.id;


--
-- Name: passwordresetkey; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.passwordresetkey OWNER TO app_user;

--
-- Name: passwordresetkey_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.passwordresetkey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.passwordresetkey_id_seq OWNER TO app_user;

--
-- Name: passwordresetkey_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.passwordresetkey_id_seq OWNED BY public.passwordresetkey.id;


--
-- Name: person; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.person OWNER TO app_user;

--
-- Name: person_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.person_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.person_id_seq OWNER TO app_user;

--
-- Name: person_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.person_id_seq OWNED BY public.person.id;


--
-- Name: phdprogressreport; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.phdprogressreport OWNER TO app_user;

--
-- Name: phdprogressreport_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.phdprogressreport_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.phdprogressreport_id_seq OWNER TO app_user;

--
-- Name: phdprogressreport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.phdprogressreport_id_seq OWNED BY public.phdprogressreport.id;


--
-- Name: studentattendance; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.studentattendance OWNER TO app_user;

--
-- Name: studentattendance_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.studentattendance_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentattendance_id_seq OWNER TO app_user;

--
-- Name: studentattendance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.studentattendance_id_seq OWNED BY public.studentattendance.id;


--
-- Name: studentcredits; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.studentcredits OWNER TO app_user;

--
-- Name: studentcredits_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.studentcredits_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentcredits_id_seq OWNER TO app_user;

--
-- Name: studentcredits_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.studentcredits_id_seq OWNED BY public.studentcredits.id;


--
-- Name: studentfeedbackstatus; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.studentfeedbackstatus OWNER TO app_user;

--
-- Name: studentfeedbackstatus_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.studentfeedbackstatus_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentfeedbackstatus_id_seq OWNER TO app_user;

--
-- Name: studentfeedbackstatus_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.studentfeedbackstatus_id_seq OWNED BY public.studentfeedbackstatus.id;


--
-- Name: studentsupervisor; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.studentsupervisor OWNER TO app_user;

--
-- Name: studentsupervisor_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.studentsupervisor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.studentsupervisor_id_seq OWNER TO app_user;

--
-- Name: studentsupervisor_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.studentsupervisor_id_seq OWNED BY public.studentsupervisor.id;


--
-- Name: systemsetting; Type: TABLE; Schema: public; Owner: app_user
--

CREATE TABLE public.systemsetting (
    id bigint NOT NULL,
    is_deleted boolean NOT NULL,
    txn_no integer NOT NULL,
    ins_ts timestamp without time zone NOT NULL,
    upd_ts timestamp without time zone NOT NULL,
    txn_login_id character varying(40),
    "group" character varying(60) NOT NULL,
    name character varying(200) NOT NULL,
    is_json boolean NOT NULL,
    value_text text,
    value_json json
);


ALTER TABLE public.systemsetting OWNER TO app_user;

--
-- Name: systemsetting_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.systemsetting_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.systemsetting_id_seq OWNER TO app_user;

--
-- Name: systemsetting_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.systemsetting_id_seq OWNED BY public.systemsetting.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public."user" OWNER TO app_user;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.user_id_seq OWNER TO app_user;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: userdoc; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.userdoc OWNER TO app_user;

--
-- Name: userdoc_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.userdoc_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.userdoc_id_seq OWNER TO app_user;

--
-- Name: userdoc_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.userdoc_id_seq OWNED BY public.userdoc.id;


--
-- Name: workflownote; Type: TABLE; Schema: public; Owner: app_user
--

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


ALTER TABLE public.workflownote OWNER TO app_user;

--
-- Name: workflownote_id_seq; Type: SEQUENCE; Schema: public; Owner: app_user
--

CREATE SEQUENCE public.workflownote_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.workflownote_id_seq OWNER TO app_user;

--
-- Name: workflownote_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: app_user
--

ALTER SEQUENCE public.workflownote_id_seq OWNED BY public.workflownote.id;


--
-- Name: academiccalendar id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.academiccalendar ALTER COLUMN id SET DEFAULT nextval('public.academiccalendar_id_seq'::regclass);


--
-- Name: academicmilestone id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.academicmilestone ALTER COLUMN id SET DEFAULT nextval('public.academicmilestone_id_seq'::regclass);


--
-- Name: attendancephoto id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.attendancephoto ALTER COLUMN id SET DEFAULT nextval('public.attendancephoto_id_seq'::regclass);


--
-- Name: batchadvisors id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.batchadvisors ALTER COLUMN id SET DEFAULT nextval('public.batchadvisors_id_seq'::regclass);


--
-- Name: course id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.course ALTER COLUMN id SET DEFAULT nextval('public.course_id_seq'::regclass);


--
-- Name: coursecategory id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.coursecategory ALTER COLUMN id SET DEFAULT nextval('public.coursecategory_id_seq'::regclass);


--
-- Name: courseenrollment id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseenrollment ALTER COLUMN id SET DEFAULT nextval('public.courseenrollment_id_seq'::regclass);


--
-- Name: courseinstructor id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructor ALTER COLUMN id SET DEFAULT nextval('public.courseinstructor_id_seq'::regclass);


--
-- Name: courseinstructorfeedback id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructorfeedback ALTER COLUMN id SET DEFAULT nextval('public.courseinstructorfeedback_id_seq'::regclass);


--
-- Name: courseoffering id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseoffering ALTER COLUMN id SET DEFAULT nextval('public.courseoffering_id_seq'::regclass);


--
-- Name: courseslottiming id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseslottiming ALTER COLUMN id SET DEFAULT nextval('public.courseslottiming_id_seq'::regclass);


--
-- Name: dcforstudent id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcforstudent ALTER COLUMN id SET DEFAULT nextval('public.dcforstudent_id_seq'::regclass);


--
-- Name: dcmember id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcmember ALTER COLUMN id SET DEFAULT nextval('public.dcmember_id_seq'::regclass);


--
-- Name: feedbackform id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feedbackform ALTER COLUMN id SET DEFAULT nextval('public.feedbackform_id_seq'::regclass);


--
-- Name: feedbackquestion id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feedbackquestion ALTER COLUMN id SET DEFAULT nextval('public.feedbackquestion_id_seq'::regclass);


--
-- Name: feestransaction id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feestransaction ALTER COLUMN id SET DEFAULT nextval('public.feestransaction_id_seq'::regclass);


--
-- Name: knownface id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.knownface ALTER COLUMN id SET DEFAULT nextval('public.knownface_id_seq'::regclass);


--
-- Name: passwordresetkey id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.passwordresetkey ALTER COLUMN id SET DEFAULT nextval('public.passwordresetkey_id_seq'::regclass);


--
-- Name: person id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.person ALTER COLUMN id SET DEFAULT nextval('public.person_id_seq'::regclass);


--
-- Name: phdprogressreport id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.phdprogressreport ALTER COLUMN id SET DEFAULT nextval('public.phdprogressreport_id_seq'::regclass);


--
-- Name: studentattendance id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentattendance ALTER COLUMN id SET DEFAULT nextval('public.studentattendance_id_seq'::regclass);


--
-- Name: studentcredits id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentcredits ALTER COLUMN id SET DEFAULT nextval('public.studentcredits_id_seq'::regclass);


--
-- Name: studentfeedbackstatus id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentfeedbackstatus ALTER COLUMN id SET DEFAULT nextval('public.studentfeedbackstatus_id_seq'::regclass);


--
-- Name: studentsupervisor id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentsupervisor ALTER COLUMN id SET DEFAULT nextval('public.studentsupervisor_id_seq'::regclass);


--
-- Name: systemsetting id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.systemsetting ALTER COLUMN id SET DEFAULT nextval('public.systemsetting_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: userdoc id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.userdoc ALTER COLUMN id SET DEFAULT nextval('public.userdoc_id_seq'::regclass);


--
-- Name: workflownote id; Type: DEFAULT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.workflownote ALTER COLUMN id SET DEFAULT nextval('public.workflownote_id_seq'::regclass);


--
-- Name: academiccalendar academiccalendar_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.academiccalendar
    ADD CONSTRAINT academiccalendar_pkey PRIMARY KEY (id);


--
-- Name: academicmilestone academicmilestone_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.academicmilestone
    ADD CONSTRAINT academicmilestone_pkey PRIMARY KEY (id);


--
-- Name: attendancephoto attendancephoto_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.attendancephoto
    ADD CONSTRAINT attendancephoto_pkey PRIMARY KEY (id);


--
-- Name: batchadvisors batchadvisors_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.batchadvisors
    ADD CONSTRAINT batchadvisors_pkey PRIMARY KEY (id);


--
-- Name: course course_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_pkey PRIMARY KEY (id);


--
-- Name: coursecategory coursecategory_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.coursecategory
    ADD CONSTRAINT coursecategory_pkey PRIMARY KEY (id);


--
-- Name: courseenrollment courseenrollment_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseenrollment
    ADD CONSTRAINT courseenrollment_pkey PRIMARY KEY (id);


--
-- Name: courseinstructor courseinstructor_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructor
    ADD CONSTRAINT courseinstructor_pkey PRIMARY KEY (id);


--
-- Name: courseinstructorfeedback courseinstructorfeedback_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructorfeedback
    ADD CONSTRAINT courseinstructorfeedback_pkey PRIMARY KEY (id);


--
-- Name: courseoffering courseoffering_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseoffering
    ADD CONSTRAINT courseoffering_pkey PRIMARY KEY (id);


--
-- Name: courseslottiming courseslottiming_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseslottiming
    ADD CONSTRAINT courseslottiming_pkey PRIMARY KEY (id);


--
-- Name: dcforstudent dcforstudent_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcforstudent
    ADD CONSTRAINT dcforstudent_pkey PRIMARY KEY (id);


--
-- Name: dcmember dcmember_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcmember
    ADD CONSTRAINT dcmember_pkey PRIMARY KEY (id);


--
-- Name: feedbackform feedbackform_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feedbackform
    ADD CONSTRAINT feedbackform_pkey PRIMARY KEY (id);


--
-- Name: feedbackquestion feedbackquestion_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feedbackquestion
    ADD CONSTRAINT feedbackquestion_pkey PRIMARY KEY (id);


--
-- Name: feestransaction feestransaction_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feestransaction
    ADD CONSTRAINT feestransaction_pkey PRIMARY KEY (id);


--
-- Name: knownface knownface_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.knownface
    ADD CONSTRAINT knownface_pkey PRIMARY KEY (id);


--
-- Name: passwordresetkey passwordresetkey_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.passwordresetkey
    ADD CONSTRAINT passwordresetkey_pkey PRIMARY KEY (id);


--
-- Name: person person_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.person
    ADD CONSTRAINT person_pkey PRIMARY KEY (id);


--
-- Name: phdprogressreport phdprogressreport_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.phdprogressreport
    ADD CONSTRAINT phdprogressreport_pkey PRIMARY KEY (id);


--
-- Name: studentattendance studentattendance_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_pkey PRIMARY KEY (id);


--
-- Name: studentcredits studentcredits_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentcredits
    ADD CONSTRAINT studentcredits_pkey PRIMARY KEY (id);


--
-- Name: studentfeedbackstatus studentfeedbackstatus_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_pkey PRIMARY KEY (id);


--
-- Name: studentsupervisor studentsupervisor_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentsupervisor
    ADD CONSTRAINT studentsupervisor_pkey PRIMARY KEY (id);


--
-- Name: systemsetting systemsetting_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.systemsetting
    ADD CONSTRAINT systemsetting_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: userdoc userdoc_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.userdoc
    ADD CONSTRAINT userdoc_pkey PRIMARY KEY (id);


--
-- Name: workflownote workflownote_pkey; Type: CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.workflownote
    ADD CONSTRAINT workflownote_pkey PRIMARY KEY (id);


--
-- Name: academiccalendar_acad_session_event_code; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX academiccalendar_acad_session_event_code ON public.academiccalendar USING btree (acad_session, event_code);


--
-- Name: academiccalendar_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX academiccalendar_txn_no ON public.academiccalendar USING btree (txn_no);


--
-- Name: academicmilestone_dc_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX academicmilestone_dc_id ON public.academicmilestone USING btree (dc_id);


--
-- Name: academicmilestone_dc_id_student_id_milestone; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX academicmilestone_dc_id_student_id_milestone ON public.academicmilestone USING btree (dc_id, student_id, milestone);


--
-- Name: academicmilestone_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX academicmilestone_student_id ON public.academicmilestone USING btree (student_id);


--
-- Name: academicmilestone_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX academicmilestone_txn_no ON public.academicmilestone USING btree (txn_no);


--
-- Name: attendancephoto_offering_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX attendancephoto_offering_id ON public.attendancephoto USING btree (offering_id);


--
-- Name: attendancephoto_offering_id_attend_dt_file_name; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX attendancephoto_offering_id_attend_dt_file_name ON public.attendancephoto USING btree (offering_id, attend_dt, file_name);


--
-- Name: attendancephoto_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX attendancephoto_txn_no ON public.attendancephoto USING btree (txn_no);


--
-- Name: batchadvisors_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX batchadvisors_txn_no ON public.batchadvisors USING btree (txn_no);


--
-- Name: batchadvisors_user_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX batchadvisors_user_id ON public.batchadvisors USING btree (user_id);


--
-- Name: batchadvisors_user_id_year_of_entry_for_degree; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX batchadvisors_user_id_year_of_entry_for_degree ON public.batchadvisors USING btree (user_id, year_of_entry, for_degree);


--
-- Name: course_author_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX course_author_id ON public.course USING btree (author_id);


--
-- Name: course_code; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX course_code ON public.course USING btree (code);


--
-- Name: course_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX course_txn_no ON public.course USING btree (txn_no);


--
-- Name: coursecategory_offering_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX coursecategory_offering_id ON public.coursecategory USING btree (offering_id);


--
-- Name: coursecategory_offering_id_degree_dept_category; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX coursecategory_offering_id_degree_dept_category ON public.coursecategory USING btree (offering_id, degree, dept, category);


--
-- Name: coursecategory_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX coursecategory_txn_no ON public.coursecategory USING btree (txn_no);


--
-- Name: courseenrollment_course_offering_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseenrollment_course_offering_id ON public.courseenrollment USING btree (course_offering_id);


--
-- Name: courseenrollment_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseenrollment_student_id ON public.courseenrollment USING btree (student_id);


--
-- Name: courseenrollment_student_id_course_offering_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX courseenrollment_student_id_course_offering_id ON public.courseenrollment USING btree (student_id, course_offering_id);


--
-- Name: courseenrollment_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseenrollment_txn_no ON public.courseenrollment USING btree (txn_no);


--
-- Name: courseinstructor_instructor_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseinstructor_instructor_id ON public.courseinstructor USING btree (instructor_id);


--
-- Name: courseinstructor_offering_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseinstructor_offering_id ON public.courseinstructor USING btree (offering_id);


--
-- Name: courseinstructor_offering_id_instructor_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX courseinstructor_offering_id_instructor_id ON public.courseinstructor USING btree (offering_id, instructor_id);


--
-- Name: courseinstructor_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseinstructor_txn_no ON public.courseinstructor USING btree (txn_no);


--
-- Name: courseinstructorfeedback_instructor_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseinstructorfeedback_instructor_id ON public.courseinstructorfeedback USING btree (instructor_id);


--
-- Name: courseinstructorfeedback_question_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseinstructorfeedback_question_id ON public.courseinstructorfeedback USING btree (question_id);


--
-- Name: courseinstructorfeedback_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseinstructorfeedback_txn_no ON public.courseinstructorfeedback USING btree (txn_no);


--
-- Name: courseoffering_course_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseoffering_course_id ON public.courseoffering USING btree (course_id);


--
-- Name: courseoffering_course_id_acad_session_status_section_dept_name; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX courseoffering_course_id_acad_session_status_section_dept_name ON public.courseoffering USING btree (course_id, acad_session, status, section, dept_name);


--
-- Name: courseoffering_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseoffering_txn_no ON public.courseoffering USING btree (txn_no);


--
-- Name: courseslottiming_slot_week_day_start_time; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX courseslottiming_slot_week_day_start_time ON public.courseslottiming USING btree (slot, week_day, start_time);


--
-- Name: courseslottiming_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX courseslottiming_txn_no ON public.courseslottiming USING btree (txn_no);


--
-- Name: dcforstudent_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX dcforstudent_student_id ON public.dcforstudent USING btree (student_id);


--
-- Name: dcforstudent_student_id_status_effective_from; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX dcforstudent_student_id_status_effective_from ON public.dcforstudent USING btree (student_id, status, effective_from);


--
-- Name: dcforstudent_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX dcforstudent_txn_no ON public.dcforstudent USING btree (txn_no);


--
-- Name: dcmember_dc_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX dcmember_dc_id ON public.dcmember USING btree (dc_id);


--
-- Name: dcmember_member_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX dcmember_member_id ON public.dcmember USING btree (member_id);


--
-- Name: dcmember_role_member_id_dc_id_is_external_ext_name; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX dcmember_role_member_id_dc_id_is_external_ext_name ON public.dcmember USING btree (role, member_id, dc_id, is_external, ext_name);


--
-- Name: dcmember_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX dcmember_txn_no ON public.dcmember USING btree (txn_no);


--
-- Name: feedbackform_form_name_form_type_is_active; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX feedbackform_form_name_form_type_is_active ON public.feedbackform USING btree (form_name, form_type, is_active);


--
-- Name: feedbackform_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX feedbackform_txn_no ON public.feedbackform USING btree (txn_no);


--
-- Name: feedbackquestion_form_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX feedbackquestion_form_id ON public.feedbackquestion USING btree (form_id);


--
-- Name: feedbackquestion_form_id_question; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX feedbackquestion_form_id_question ON public.feedbackquestion USING btree (form_id, question);


--
-- Name: feedbackquestion_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX feedbackquestion_txn_no ON public.feedbackquestion USING btree (txn_no);


--
-- Name: feestransaction_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX feestransaction_student_id ON public.feestransaction USING btree (student_id);


--
-- Name: feestransaction_student_id_acad_session_fees_txn_no_fees_c1d64d; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX feestransaction_student_id_acad_session_fees_txn_no_fees_c1d64d ON public.feestransaction USING btree (student_id, acad_session, fees_txn_no, fees_txn_bank, fees_txn_dt, doc_file_name, is_deleted);


--
-- Name: feestransaction_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX feestransaction_txn_no ON public.feestransaction USING btree (txn_no);


--
-- Name: knownface_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX knownface_txn_no ON public.knownface USING btree (txn_no);


--
-- Name: knownface_user_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX knownface_user_id ON public.knownface USING btree (user_id);


--
-- Name: passwordresetkey_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX passwordresetkey_txn_no ON public.passwordresetkey USING btree (txn_no);


--
-- Name: person_org_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX person_org_id ON public.person USING btree (org_id);


--
-- Name: person_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX person_txn_no ON public.person USING btree (txn_no);


--
-- Name: phdprogressreport_dc_member_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX phdprogressreport_dc_member_id ON public.phdprogressreport USING btree (dc_member_id);


--
-- Name: phdprogressreport_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX phdprogressreport_student_id ON public.phdprogressreport USING btree (student_id);


--
-- Name: phdprogressreport_student_id_dc_member_id_acad_session; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX phdprogressreport_student_id_dc_member_id_acad_session ON public.phdprogressreport USING btree (student_id, dc_member_id, acad_session);


--
-- Name: phdprogressreport_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX phdprogressreport_txn_no ON public.phdprogressreport USING btree (txn_no);


--
-- Name: studentattendance_enrollment_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentattendance_enrollment_id ON public.studentattendance USING btree (enrollment_id);


--
-- Name: studentattendance_enrollment_id_attend_dt; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX studentattendance_enrollment_id_attend_dt ON public.studentattendance USING btree (enrollment_id, attend_dt);


--
-- Name: studentattendance_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentattendance_txn_no ON public.studentattendance USING btree (txn_no);


--
-- Name: studentcredits_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentcredits_student_id ON public.studentcredits USING btree (student_id);


--
-- Name: studentcredits_student_id_acad_session; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX studentcredits_student_id_acad_session ON public.studentcredits USING btree (student_id, acad_session);


--
-- Name: studentcredits_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentcredits_txn_no ON public.studentcredits USING btree (txn_no);


--
-- Name: studentfeedbackstatus_course_instructor_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentfeedbackstatus_course_instructor_id ON public.studentfeedbackstatus USING btree (course_instructor_id);


--
-- Name: studentfeedbackstatus_course_instructor_id_student_id_fe_ce0120; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX studentfeedbackstatus_course_instructor_id_student_id_fe_ce0120 ON public.studentfeedbackstatus USING btree (course_instructor_id, student_id, feedback_form_id);


--
-- Name: studentfeedbackstatus_feedback_form_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentfeedbackstatus_feedback_form_id ON public.studentfeedbackstatus USING btree (feedback_form_id);


--
-- Name: studentfeedbackstatus_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentfeedbackstatus_student_id ON public.studentfeedbackstatus USING btree (student_id);


--
-- Name: studentfeedbackstatus_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentfeedbackstatus_txn_no ON public.studentfeedbackstatus USING btree (txn_no);


--
-- Name: studentsupervisor_student_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentsupervisor_student_id ON public.studentsupervisor USING btree (student_id);


--
-- Name: studentsupervisor_student_id_supervisor_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX studentsupervisor_student_id_supervisor_id ON public.studentsupervisor USING btree (student_id, supervisor_id);


--
-- Name: studentsupervisor_supervisor_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentsupervisor_supervisor_id ON public.studentsupervisor USING btree (supervisor_id);


--
-- Name: studentsupervisor_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX studentsupervisor_txn_no ON public.studentsupervisor USING btree (txn_no);


--
-- Name: systemsetting_group; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX systemsetting_group ON public.systemsetting USING btree ("group");


--
-- Name: systemsetting_group_name_is_json; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX systemsetting_group_name_is_json ON public.systemsetting USING btree ("group", name, is_json);


--
-- Name: systemsetting_is_json; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX systemsetting_is_json ON public.systemsetting USING btree (is_json);


--
-- Name: systemsetting_name; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX systemsetting_name ON public.systemsetting USING btree (name);


--
-- Name: systemsetting_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX systemsetting_txn_no ON public.systemsetting USING btree (txn_no);


--
-- Name: user_email; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX user_email ON public."user" USING btree (email);


--
-- Name: user_login_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX user_login_id ON public."user" USING btree (login_id);


--
-- Name: user_person_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE UNIQUE INDEX user_person_id ON public."user" USING btree (person_id);


--
-- Name: user_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX user_txn_no ON public."user" USING btree (txn_no);


--
-- Name: userdoc_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX userdoc_txn_no ON public.userdoc USING btree (txn_no);


--
-- Name: userdoc_user_id; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX userdoc_user_id ON public.userdoc USING btree (user_id);


--
-- Name: workflownote_txn_no; Type: INDEX; Schema: public; Owner: app_user
--

CREATE INDEX workflownote_txn_no ON public.workflownote USING btree (txn_no);


--
-- Name: academicmilestone academicmilestone_dc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.academicmilestone
    ADD CONSTRAINT academicmilestone_dc_id_fkey FOREIGN KEY (dc_id) REFERENCES public.dcforstudent(id) ON DELETE CASCADE;


--
-- Name: academicmilestone academicmilestone_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.academicmilestone
    ADD CONSTRAINT academicmilestone_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: attendancephoto attendancephoto_offering_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.attendancephoto
    ADD CONSTRAINT attendancephoto_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.courseoffering(id) ON DELETE CASCADE;


--
-- Name: batchadvisors batchadvisors_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.batchadvisors
    ADD CONSTRAINT batchadvisors_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: course course_author_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.course
    ADD CONSTRAINT course_author_id_fkey FOREIGN KEY (author_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: coursecategory coursecategory_offering_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.coursecategory
    ADD CONSTRAINT coursecategory_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.courseoffering(id) ON DELETE SET NULL;


--
-- Name: courseenrollment courseenrollment_course_offering_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseenrollment
    ADD CONSTRAINT courseenrollment_course_offering_id_fkey FOREIGN KEY (course_offering_id) REFERENCES public.courseoffering(id) ON DELETE CASCADE;


--
-- Name: courseenrollment courseenrollment_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseenrollment
    ADD CONSTRAINT courseenrollment_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: courseinstructor courseinstructor_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructor
    ADD CONSTRAINT courseinstructor_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public."user"(id) ON DELETE SET NULL;


--
-- Name: courseinstructor courseinstructor_offering_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructor
    ADD CONSTRAINT courseinstructor_offering_id_fkey FOREIGN KEY (offering_id) REFERENCES public.courseoffering(id) ON DELETE SET NULL;


--
-- Name: courseinstructorfeedback courseinstructorfeedback_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructorfeedback
    ADD CONSTRAINT courseinstructorfeedback_instructor_id_fkey FOREIGN KEY (instructor_id) REFERENCES public.courseinstructor(id) ON DELETE CASCADE;


--
-- Name: courseinstructorfeedback courseinstructorfeedback_question_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseinstructorfeedback
    ADD CONSTRAINT courseinstructorfeedback_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.feedbackquestion(id) ON DELETE CASCADE;


--
-- Name: courseoffering courseoffering_course_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.courseoffering
    ADD CONSTRAINT courseoffering_course_id_fkey FOREIGN KEY (course_id) REFERENCES public.course(id) ON DELETE SET NULL;


--
-- Name: dcforstudent dcforstudent_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcforstudent
    ADD CONSTRAINT dcforstudent_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: dcmember dcmember_dc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcmember
    ADD CONSTRAINT dcmember_dc_id_fkey FOREIGN KEY (dc_id) REFERENCES public.dcforstudent(id) ON DELETE CASCADE;


--
-- Name: dcmember dcmember_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.dcmember
    ADD CONSTRAINT dcmember_member_id_fkey FOREIGN KEY (member_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: feedbackquestion feedbackquestion_form_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feedbackquestion
    ADD CONSTRAINT feedbackquestion_form_id_fkey FOREIGN KEY (form_id) REFERENCES public.feedbackform(id) ON DELETE CASCADE;


--
-- Name: feestransaction feestransaction_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.feestransaction
    ADD CONSTRAINT feestransaction_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: knownface knownface_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.knownface
    ADD CONSTRAINT knownface_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: phdprogressreport phdprogressreport_dc_member_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.phdprogressreport
    ADD CONSTRAINT phdprogressreport_dc_member_id_fkey FOREIGN KEY (dc_member_id) REFERENCES public.dcmember(id) ON DELETE CASCADE;


--
-- Name: phdprogressreport phdprogressreport_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.phdprogressreport
    ADD CONSTRAINT phdprogressreport_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: studentattendance studentattendance_enrollment_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentattendance
    ADD CONSTRAINT studentattendance_enrollment_id_fkey FOREIGN KEY (enrollment_id) REFERENCES public.courseenrollment(id) ON DELETE CASCADE;


--
-- Name: studentcredits studentcredits_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentcredits
    ADD CONSTRAINT studentcredits_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id);


--
-- Name: studentfeedbackstatus studentfeedbackstatus_course_instructor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_course_instructor_id_fkey FOREIGN KEY (course_instructor_id) REFERENCES public.courseinstructor(id) ON DELETE CASCADE;


--
-- Name: studentfeedbackstatus studentfeedbackstatus_feedback_form_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_feedback_form_id_fkey FOREIGN KEY (feedback_form_id) REFERENCES public.feedbackform(id) ON DELETE CASCADE;


--
-- Name: studentfeedbackstatus studentfeedbackstatus_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentfeedbackstatus
    ADD CONSTRAINT studentfeedbackstatus_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.courseenrollment(id) ON DELETE CASCADE;


--
-- Name: studentsupervisor studentsupervisor_student_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentsupervisor
    ADD CONSTRAINT studentsupervisor_student_id_fkey FOREIGN KEY (student_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: studentsupervisor studentsupervisor_supervisor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.studentsupervisor
    ADD CONSTRAINT studentsupervisor_supervisor_id_fkey FOREIGN KEY (supervisor_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: user user_person_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_person_id_fkey FOREIGN KEY (person_id) REFERENCES public.person(id);


--
-- Name: userdoc userdoc_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: app_user
--

ALTER TABLE ONLY public.userdoc
    ADD CONSTRAINT userdoc_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

