-- Audit logs table that will maintain the old records in all audited entities.
-- The latest row will always be in the corresponding entity table itself.

DROP TABLE IF EXISTS audit_log;
CREATE TABLE audit_log (
    audit_id int NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entity_id BIGINT NOT NULL,
    entity_name varchar(255) NOT NULL,
    old_row_data JSON,
    dml_type ENUM('INSERT', 'UPDATE', 'DELETE') NOT NULL,
    dml_timestamp TIMESTAMP NOT NULL,
    dml_created_by VARCHAR(255) NULL,
    KEY `IDX_entity_id_name_dml` (`entity_id`,`entity_name`,`dml_type`)
);

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table academiccalendar
DROP TRIGGER IF EXISTS TRG_academic_calendar_insert;
CREATE TRIGGER TRG_academic_calendar_insert
AFTER INSERT ON academiccalendar
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "academic_calendar",
        JSON_OBJECT(
            "acad_session", NEW.acad_session,
            "event_code", NEW.event_code,
            "event_value", NEW.event_value,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_academic_calendar_update;
delimiter //
CREATE TRIGGER TRG_academic_calendar_update
AFTER UPDATE ON academiccalendar FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "academic_calendar",
        JSON_OBJECT(
            "acad_session", OLD.acad_session,
            "event_code", OLD.event_code,
            "event_value", OLD.event_value,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_academic_calendar_delete;
CREATE TRIGGER TRG_academic_calendar_delete
AFTER DELETE ON academiccalendar
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "academic_calendar",
        JSON_OBJECT(
            "acad_session", OLD.acad_session,
            "event_code", OLD.event_code,
            "event_value", OLD.event_value,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table course

DROP TRIGGER IF EXISTS TRG_course_insert;
CREATE TRIGGER TRG_course_insert
AFTER INSERT ON course
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "course",
        JSON_OBJECT(
            "code", NEW.code,
            "title", NEW.title,
            "ltp", NEW.ltp,
            "status", NEW.status,
            "author_id", NEW.author_id,
            "freq", NEW.freq,
            "has_lab", NEW.has_lab,
            "prereqs", NEW.prereqs,
            "objectives", NEW.objectives,
            "req_visiting_fac", NEW.req_visiting_fac,
            "course_supersedes", NEW.course_supersedes,
            "course_overlaps", NEW.course_overlaps,
            "tkp", NEW.tkp,
            "tgap", NEW.tgap,
            "modules", NEW.modules,
            "teaching", NEW.teaching,
            "learning", NEW.learning,
            "evaluation", NEW.evaluation,
            "ref_material", NEW.ref_material,

            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_course_update;
delimiter //
CREATE TRIGGER TRG_course_update
AFTER UPDATE ON course FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "course",
        JSON_OBJECT(
            "code", OLD.code,
            "title", OLD.title,
            "ltp", OLD.ltp,
            "status", OLD.status,
            "author_id", OLD.author_id,
            "freq", OLD.freq,
            "has_lab", OLD.has_lab,
            "prereqs", OLD.prereqs,
            "objectives", OLD.objectives,
            "req_visiting_fac", OLD.req_visiting_fac,
            "course_supersedes", OLD.course_supersedes,
            "course_overlaps", OLD.course_overlaps,
            "tkp", OLD.tkp,
            "tgap", OLD.tgap,
            "modules", OLD.modules,
            "teaching", OLD.teaching,
            "learning", OLD.learning,
            "evaluation", OLD.evaluation,
            "ref_material", OLD.ref_material,

            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_course_delete;
CREATE TRIGGER TRG_course_delete
AFTER DELETE ON course
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "course",
        JSON_OBJECT(
            "code", OLD.code,
            "title", OLD.title,
            "ltp", OLD.ltp,
            "status", OLD.status,
            "author_id", OLD.author_id,
            "freq", OLD.freq,
            "has_lab", OLD.has_lab,
            "prereqs", OLD.prereqs,
            "objectives", OLD.objectives,
            "req_visiting_fac", OLD.req_visiting_fac,
            "course_supersedes", OLD.course_supersedes,
            "course_overlaps", OLD.course_overlaps,
            "tkp", OLD.tkp,
            "tgap", OLD.tgap,
            "modules", OLD.modules,
            "teaching", OLD.teaching,
            "learning", OLD.learning,
            "evaluation", OLD.evaluation,
            "ref_material", OLD.ref_material,

            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );
    
-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table courseenrollment
DROP TRIGGER IF EXISTS TRG_courseenrollment_insert;
CREATE TRIGGER TRG_courseenrollment_insert
AFTER INSERT ON courseenrollment
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "courseenrollment",
        JSON_OBJECT(
            "course_offering_id", NEW.course_offering_id,
            "student_id", NEW.student_id,
            "enrol_type", NEW.enrol_type,
            "enrol_status", NEW.enrol_status,
            "grade", NEW.grade,
            "current_score", NEW.current_score,
            "remarks", NEW.remarks,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_courseenrollment_update;
delimiter //
CREATE TRIGGER TRG_courseenrollment_update
AFTER UPDATE ON courseenrollment FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseenrollment",
        JSON_OBJECT(
            "course_offering_id", OLD.course_offering_id,
            "student_id", OLD.student_id,
            "enrol_type", OLD.enrol_type,
            "enrol_status", OLD.enrol_status,
            "grade", OLD.grade,
            "current_score", OLD.current_score,
            "remarks", OLD.remarks,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_courseenrollment_delete;
CREATE TRIGGER TRG_courseenrollment_delete
AFTER DELETE ON courseenrollment
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseenrollment",
        JSON_OBJECT(
            "course_offering_id", OLD.course_offering_id,
            "student_id", OLD.student_id,
            "enrol_type", OLD.enrol_type,
            "enrol_status", OLD.enrol_status,
            "grade", OLD.grade,
            "current_score", OLD.current_score,
            "remarks", OLD.remarks,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );


-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table courseoffering

DROP TRIGGER IF EXISTS TRG_courseoffering_insert;
CREATE TRIGGER TRG_courseoffering_insert
AFTER INSERT ON courseoffering
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "courseoffering",
        JSON_OBJECT(
            "acad_session", NEW.acad_session,
            "course_id", NEW.course_id,
            "status", NEW.status,
            "slot", NEW.slot,
            "section", NEW.section,
            "dept_name", NEW.dept_name,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_courseoffering_update;
delimiter //
CREATE TRIGGER TRG_courseoffering_update
AFTER UPDATE ON courseoffering FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseoffering",
        JSON_OBJECT(
            "acad_session", OLD.acad_session,
            "course_id", OLD.course_id,
            "status", OLD.status,
            "slot", OLD.slot,
            "section", OLD.section,
            "dept_name", OLD.dept_name,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_courseoffering_delete;
CREATE TRIGGER TRG_courseoffering_delete
AFTER DELETE ON courseoffering
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseoffering",
        JSON_OBJECT(
            "acad_session", OLD.acad_session,
            "course_id", OLD.course_id,
            "status", OLD.status,
            "slot", OLD.slot,
            "section", OLD.section,
            "dept_name", OLD.dept_name,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table courseinstructor

DROP TRIGGER IF EXISTS TRG_courseinstructor_insert;
CREATE TRIGGER TRG_courseinstructor_insert
AFTER INSERT ON courseinstructor
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "courseinstructor",
        JSON_OBJECT(
            "offering_id", NEW.offering_id,
            "instructor_id", NEW.instructor_id,
            "is_coordinator", NEW.is_coordinator,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_courseinstructor_update;
delimiter //
CREATE TRIGGER TRG_courseinstructor_update
AFTER UPDATE ON courseinstructor FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseinstructor",
        JSON_OBJECT(
            "offering_id", OLD.offering_id,
            "instructor_id", OLD.instructor_id,
            "is_coordinator", OLD.is_coordinator,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_courseinstructor_delete;
CREATE TRIGGER TRG_courseinstructor_delete
AFTER DELETE ON courseinstructor
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseinstructor",
        JSON_OBJECT(
            "offering_id", OLD.offering_id,
            "instructor_id", OLD.instructor_id,
            "is_coordinator", OLD.is_coordinator,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table coursecategory

DROP TRIGGER IF EXISTS TRG_coursecategory_insert;
CREATE TRIGGER TRG_coursecategory_insert
AFTER INSERT ON coursecategory
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "coursecategory",
        JSON_OBJECT(
            "offering_id", NEW.offering_id,
            "degree", NEW.degree,
            "dept", NEW.dept,
            "category", NEW.category,
            "for_entry_years", NEW.for_entry_years,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_coursecategory_update;
delimiter //
CREATE TRIGGER TRG_coursecategory_update
AFTER UPDATE ON coursecategory FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "coursecategory",
        JSON_OBJECT(
            "offering_id", OLD.offering_id,
            "degree", OLD.degree,
            "dept", OLD.dept,
            "category", OLD.category,
            "for_entry_years", OLD.for_entry_years,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_coursecategory_delete;
CREATE TRIGGER TRG_coursecategory_delete
AFTER DELETE ON coursecategory
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "coursecategory",
        JSON_OBJECT(
            "offering_id", OLD.offering_id,
            "degree", OLD.degree,
            "dept", OLD.dept,
            "category", OLD.category,
            "for_entry_years", OLD.for_entry_years,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table courseinstructorfeedback

DROP TRIGGER IF EXISTS TRG_courseinstructorfeedback_insert;
CREATE TRIGGER TRG_courseinstructorfeedback_insert
AFTER INSERT ON courseinstructorfeedback
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "courseinstructorfeedback",
        JSON_OBJECT(
            "instructor_id", NEW.instructor_id,
            "question_id", NEW.question_id,
            "feedback", NEW.feedback,
            "submission_id", NEW.submission_id,
            "acad_session", NEW.acad_session,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_courseinstructorfeedback_update;
delimiter //
CREATE TRIGGER TRG_courseinstructorfeedback_update
AFTER UPDATE ON courseinstructorfeedback FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseinstructorfeedback",
        JSON_OBJECT(
            "instructor_id", OLD.instructor_id,
            "question_id", OLD.question_id,
            "feedback", OLD.feedback,
            "submission_id", OLD.submission_id,
            "acad_session", OLD.acad_session,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_courseinstructorfeedback_delete;
CREATE TRIGGER TRG_courseinstructorfeedback_delete
AFTER DELETE ON courseinstructorfeedback
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "courseinstructorfeedback",
        JSON_OBJECT(
            "instructor_id", OLD.instructor_id,
            "question_id", OLD.question_id,
            "feedback", OLD.feedback,
            "submission_id", OLD.submission_id,
            "acad_session", OLD.acad_session,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table studentfeedbackstatus

DROP TRIGGER IF EXISTS TRG_studentfeedbackstatus_insert;
CREATE TRIGGER TRG_studentfeedbackstatus_insert
AFTER INSERT ON studentfeedbackstatus
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "studentfeedbackstatus",
        JSON_OBJECT(
            "feedback_form_id", NEW.feedback_form_id,
            "course_instructor_id", NEW.course_instructor_id,
            "student_id", NEW.student_id,
            "is_submitted", NEW.is_submitted,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_studentfeedbackstatus_update;
delimiter //
CREATE TRIGGER TRG_studentfeedbackstatus_update
AFTER UPDATE ON studentfeedbackstatus FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "studentfeedbackstatus",
        JSON_OBJECT(
            "feedback_form_id", OLD.feedback_form_id,
            "course_instructor_id", OLD.course_instructor_id,
            "student_id", OLD.student_id,
            "is_submitted", OLD.is_submitted,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_studentfeedbackstatus_delete;
CREATE TRIGGER TRG_studentfeedbackstatus_delete
AFTER DELETE ON studentfeedbackstatus
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "studentfeedbackstatus",
        JSON_OBJECT(
            "feedback_form_id", OLD.feedback_form_id,
            "course_instructor_id", OLD.course_instructor_id,
            "student_id", OLD.student_id,
            "is_submitted", OLD.is_submitted,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table feedbackform

DROP TRIGGER IF EXISTS TRG_feedbackform_insert;
CREATE TRIGGER TRG_feedbackform_insert
AFTER INSERT ON feedbackform
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "feedbackform",
        JSON_OBJECT(
            "form_name", NEW.form_name,
            "is_active", NEW.is_active,
            "form_type", NEW.form_type,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_feedbackform_update;
delimiter //
CREATE TRIGGER TRG_feedbackform_update
AFTER UPDATE ON feedbackform FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "feedbackform",
        JSON_OBJECT(
            "form_name", OLD.form_name,
            "is_active", OLD.is_active,
            "form_type", OLD.form_type,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_feedbackform_delete;
CREATE TRIGGER TRG_feedbackform_delete
AFTER DELETE ON feedbackform
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "feedbackform",
        JSON_OBJECT(
            "form_name", OLD.form_name,
            "is_active", OLD.is_active,
            "form_type", OLD.form_type,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table feedbackquestion

DROP TRIGGER IF EXISTS TRG_feedbackquestion_insert;
CREATE TRIGGER TRG_feedbackquestion_insert
AFTER INSERT ON feedbackquestion
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "feedbackquestion",
        JSON_OBJECT(
            "form_id", NEW.form_id,
            "question", NEW.question,
            "ans_options", NEW.ans_options,
            "is_optional", NEW.is_optional,
            "is_multianswer", NEW.is_multianswer,
            "is_text", NEW.is_text,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_feedbackquestion_update;
delimiter //
CREATE TRIGGER TRG_feedbackquestion_update
AFTER UPDATE ON feedbackquestion FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "feedbackquestion",
        JSON_OBJECT(
            "form_id", OLD.form_id,
            "question", OLD.question,
            "ans_options", OLD.ans_options,
            "is_optional", OLD.is_optional,
            "is_multianswer", OLD.is_multianswer,
            "is_text", OLD.is_text,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_feedbackquestion_delete;
CREATE TRIGGER TRG_feedbackquestion_delete
AFTER DELETE ON feedbackquestion
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "feedbackquestion",
        JSON_OBJECT(
            "form_id", OLD.form_id,
            "question", OLD.question,
            "ans_options", OLD.ans_options,
            "is_optional", OLD.is_optional,
            "is_multianswer", OLD.is_multianswer,
            "is_text", OLD.is_text,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table person

DROP TRIGGER IF EXISTS TRG_person_insert;
CREATE TRIGGER TRG_person_insert
AFTER INSERT ON person
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "person",
        JSON_OBJECT(
            "org_id", NEW.org_id,
            "gender", NEW.gender,
            "dept_name", NEW.dept_name,
            "year_of_entry", NEW.year_of_entry,
            "degree", NEW.degree,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_person_update;
delimiter //
CREATE TRIGGER TRG_person_update
AFTER UPDATE ON person FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "person",
        JSON_OBJECT(
            "org_id", OLD.org_id,
            "gender", OLD.gender,
            "dept_name", OLD.dept_name,
            "year_of_entry", OLD.year_of_entry,
            "degree", OLD.degree,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_person_delete;
CREATE TRIGGER TRG_person_delete
AFTER DELETE ON person
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "person",
        JSON_OBJECT(
            "org_id", OLD.org_id,
            "gender", OLD.gender,
            "dept_name", OLD.dept_name,
            "year_of_entry", OLD.year_of_entry,
            "degree", OLD.degree,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );

-- Define the trigger for INSERT, UPDATE and DELETE
-- operations on the table user

DROP TRIGGER IF EXISTS TRG_user_insert;
CREATE TRIGGER TRG_user_insert
AFTER INSERT ON user
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        NEW.id,
        "user",
        JSON_OBJECT(
            "login_id", NEW.login_id,
            "email", NEW.email,
            "first_name", NEW.first_name,
            "last_name", NEW.last_name,
            "is_locked", NEW.is_locked,
            "person_id", NEW.person_id,
            "role", NEW.role,
            "is_deleted", NEW.is_deleted,
            "txn_no", NEW.txn_no,
            "ins_ts", NEW.ins_ts,
            "upd_ts", NEW.upd_ts,
            "txn_login_id", NEW.txn_login_id
        ),
        'INSERT',
        CURRENT_TIMESTAMP,
        USER()
    );

DROP TRIGGER IF EXISTS TRG_user_update;
delimiter //
CREATE TRIGGER TRG_user_update
AFTER UPDATE ON user FOR EACH ROW 
BEGIN
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "user",
        JSON_OBJECT(
            "login_id", OLD.login_id,
            "email", OLD.email,
            "first_name", OLD.first_name,
            "last_name", OLD.last_name,
            "is_locked", OLD.is_locked,
            "person_id", OLD.person_id,
            "role", OLD.role,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'UPDATE',
        CURRENT_TIMESTAMP,
        USER()
    );
END;//
delimiter ;

DROP TRIGGER IF EXISTS TRG_user_delete;
CREATE TRIGGER TRG_user_delete
AFTER DELETE ON user
FOR EACH ROW 
    INSERT INTO audit_log (
        entity_id,
        entity_name,
        old_row_data,
        dml_type,
        dml_timestamp,
        dml_created_by
    )
    VALUES(
        OLD.id,
        "user",
        JSON_OBJECT(
            "login_id", OLD.login_id,
            "email", OLD.email,
            "first_name", OLD.first_name,
            "last_name", OLD.last_name,
            "is_locked", OLD.is_locked,
            "person_id", OLD.person_id,
            "role", OLD.role,
            "is_deleted", OLD.is_deleted,
            "txn_no", OLD.txn_no,
            "ins_ts", OLD.ins_ts,
            "upd_ts", OLD.upd_ts,
            "txn_login_id", OLD.txn_login_id
        ),
        'DELETE',
        CURRENT_TIMESTAMP,
        USER()
    );