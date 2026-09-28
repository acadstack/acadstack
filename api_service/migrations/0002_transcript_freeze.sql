-- Reproducible transcripts: closing a session copies each enrolment's
-- credits onto the enrolment (NULL while the session is open), and every
-- grade change is logged.

ALTER TABLE public.courseenrollment ADD COLUMN credits numeric(6,2);

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

INSERT INTO public.permission (code, description, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('sessions.close', 'Close an academic session, freezing its credits and grades', false, 1, now(), now())
    ON CONFLICT (code) DO NOTHING;

INSERT INTO public.rolepermission (role, permission, is_deleted, txn_no, ins_ts, upd_ts) VALUES
    ('ACA', 'sessions.close', false, 1, now(), now())
    ON CONFLICT (role, permission) DO NOTHING;
