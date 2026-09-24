import json
import uuid
from quart.helpers import send_file
from create_email import send_access_violation_alert
from validation_checks import (is_current_user_in_role_and_id, 
                               get_event_date, 
                               is_feedback_open)
from quart import Blueprint, request
import logging
import api_common as apiVC
import models as DB
import common as C

def init_routes(bp: Blueprint):
    bp.add_url_rule('/form_save', view_func=save_feedback_form, methods=['POST'])
    bp.add_url_rule('/get_feedback_forms', view_func=get_feedback_forms, methods=['GET'])
    bp.add_url_rule('/load_feedback_form/<int:form_id>', view_func=load_feedback_form, methods=['GET'])
    bp.add_url_rule('/get_active_feedback_form/<string:form_type>', view_func=get_active_feedback_form, methods=['GET'])
    bp.add_url_rule('/student_enrolments_for_fb/<string:form_type>', view_func=student_enrolments_for_fb,
                       methods=['GET'])
    bp.add_url_rule('/save_course_instructor_feedback', view_func=save_course_instructor_feedback,
                       methods=['POST'])
    bp.add_url_rule('/get_instructor_feedback/<int:co_id>/<int:user_id>/<string:fb_type>',
                       view_func=get_instructor_feedback, methods=['GET'])
    bp.add_url_rule('/download_feedback_stats/<string:form_type>/<string:acad_session>',
                       view_func=download_feedback_stats, methods=['GET'])
    bp.add_url_rule('/download_course_wise_faculty_score/<string:form_type>/<string:acad_session>',
                       view_func=download_course_wise_faculty_score, methods=['GET'])
    bp.add_url_rule('/download_quewise_facfeedbk_score/<string:form_type>/<string:acad_session>',
                       view_func=download_quewise_facfeedbk_score, methods=['GET'])


@C.rbac(permissions=["feedback.manage_form"])
async def save_feedback_form():
    fd = await request.get_json(force=True)
    logging.info("Saving feedback form details: {}".format(fd))
    with DB.db.atomic() as txn:
        if "id" in fd and int(fd["id"]) > 0:
            ff = DB.FeedbackForm.get_by_id(int(fd["id"]))
            C.update_model_skip_unknown(ff, fd)
            apiVC.update_entity(DB.FeedbackForm, ff)
        else:
            ff = DB.FeedbackForm()
            C.update_model_skip_unknown(ff, fd)
            apiVC.save_entity(ff)

        # Save the questions
        for q in fd["form_questions"]:
            if "is_deleted" in q and q["is_deleted"]:
                if "id" in q:
                    DB.FeedbackQuestion.delete_by_id(int(q["id"]))
            elif "id" in q and int(q["id"]) > 0:
                q_db = DB.FeedbackQuestion.get_by_id(int(q["id"]))
                C.update_model_skip_unknown(q_db, q)
                apiVC.update_entity(DB.FeedbackQuestion, q_db)
            else:
                q_db = DB.FeedbackQuestion()
                q_db.form = ff
                C.update_model_skip_unknown(q_db, q)
                apiVC.save_entity(q_db)

        txn.commit()

    return apiVC.ok_json("saved successfully!")


@C.rbac
def get_feedback_forms():
    res = DB.FeedbackForm.select()
    serialized = [apiVC.model_to_dict(r) for r in res]
    return apiVC.ok_json(serialized)


def __fetch_feedback_form(qry_type, qry_param):
    form = None
    if qry_type == "BY_FORM_ID":
        form = DB.FeedbackForm.get_by_id(qry_param)
    elif qry_type == "BY_FORM_TYPE":
        obj = DB.FeedbackForm.select().where(
            (DB.FeedbackForm.is_active == True) &
            (DB.FeedbackForm.form_type == qry_param)
        )
        form = obj[0] if obj.exists() else None
    else:
        raise C.AcadStackException("Failed to locate feedback form. "
                              f"Invalid query type {qry_type}")

    if not form:
        raise C.AcadStackException("Requested feedback form not found!")

    qlist = DB.FeedbackQuestion.select().where(
        DB.FeedbackQuestion.form == form).order_by(DB.FeedbackQuestion.id)
    res = apiVC.model_to_dict(form, exclude=[DB.FeedbackForm.upd_ts, DB.FeedbackForm.ins_ts,
                            DB.FeedbackForm.txn_no, DB.FeedbackForm.txn_login_id])
    res["form_questions"] = [apiVC.model_to_dict(q,
                                exclude=[DB.FeedbackQuestion.form,
                                DB.FeedbackQuestion.upd_ts,
                                DB.FeedbackQuestion.ins_ts,
                                DB.FeedbackQuestion.txn_login_id,
                                DB.FeedbackQuestion.txn_no])
                                for q in qlist]
    return res


@C.rbac
def load_feedback_form(form_id):
    return apiVC.ok_json(__fetch_feedback_form("BY_FORM_ID", form_id))


@C.rbac
def get_active_feedback_form(form_type):
    return apiVC.ok_json(__fetch_feedback_form("BY_FORM_TYPE", form_type))


@C.rbac
def student_enrolments_for_fb(form_type):
    stu = apiVC.current_login_id()
    cas = apiVC.current_acad_session_list(False)
    qry = C.sql_by_id("student_enrolments_for_fb")
    cas_list = [",".join(map(str, cas))]
    cursor = DB.db.execute_sql(qry, [stu, cas_list, form_type])
    res = []
    for row in cursor.fetchall():
        # id, title, code, first_name, last_name
        res.append({"enrolment_id": row[0],
                    "course_instructor_id": row[1],
                    "label": "{0} ({1}) -- {2} {3}".format(
                        row[2], row[3], row[4], row[5])})
    return apiVC.ok_json(res)


@C.rbac
async def save_course_instructor_feedback():
    if not apiVC.has_permission("feedback.submit"):
        msg = "Non-student user ({0}) attempted to submit course feedback.".format(apiVC.current_login_id())
        logging.error(msg)
        send_access_violation_alert(msg)
        return apiVC.error_json(
            "Only students can submit the feedback! Your attempt to submit feedback will be reported.")

    fd = await request.get_json(force=True)
    ff_id = int(fd["form"]["id"])
    fform = DB.FeedbackForm.get_or_none(ff_id)
    if not fform:
        return apiVC.error_json("Feedback form definition not found!")

    logging.debug("Saving course instructor feedback: {}".format(fd))
    with DB.db.atomic() as txn:
        if "enrolment_id" in fd and int(fd["enrolment_id"]) > 0 \
                and "ci_id" in fd and int(fd["ci_id"]) > 0:

            enrl_id = int(fd["enrolment_id"])
            ce = DB.CourseEnrollment.get_or_none(enrl_id)
            if not ce:
                return apiVC.error_json("Enrollment record not found!")

            acad_sess = ce.course_offering.acad_session
            if not is_feedback_open(acad_sess, fform.form_type):
                return apiVC.error_json("Feedback {0} not open for {1}."
                                    .format(fform.form_type, acad_sess))

            if ce and ce.student != apiVC.logged_in_user():
                msg = "User ({0}) attempted to submit course feedback for user ({1}) in course {2}.".format(
                        apiVC.current_login_id(), ce.student.login_id,
                        ce.course_offering.course.code)
                logging.error(msg)
                send_access_violation_alert(msg)
                return apiVC.error_json("Cannot submit feedback for others! Your attempt to do so has been reported!")

            cif_list = []
            qry = DB.StudentFeedbackStatus.select().where(
                (DB.StudentFeedbackStatus.student == apiVC.logged_in_user()) &
                (DB.StudentFeedbackStatus.feedback_form == int(fd["form"]["id"])) &
                (DB.StudentFeedbackStatus.course_instructor == int(fd["ci_id"])) &
                (DB.StudentFeedbackStatus.is_submitted == True)
            )

            if qry.exists():
                return apiVC.error_json("You have already submitted feedback for this course and instructor.")
            submission_id = str(uuid.uuid4())
            for qq in fd["form"]["form_questions"]:
                cif = DB.CourseInstructorFeedback()
                cif.acad_session = acad_sess
                cif.submission_id = submission_id
                cif.instructor = int(fd["ci_id"])
                cif.question = int(qq["id"])
                if not qq["is_optional"] and "answer" not in qq:
                    txn.rollback()
                    return apiVC.error_json("Please answer all mandatory questions!")

                cif.feedback = str(qq["answer"]).strip() if "answer" in qq else ""
                cif_list.append(cif)

            # Issue a bulk insert for feedback responses
            DB.CourseInstructorFeedback.bulk_create(cif_list)

            sfs = DB.StudentFeedbackStatus()
            sfs.feedback_form = int(fd["form"]["id"])
            sfs.course_instructor = int(fd["ci_id"])
            sfs.student = apiVC.logged_in_user().id
            sfs.is_submitted = True
            apiVC.save_entity(sfs)
        else:
            return apiVC.error_json("Please select a valid course instructor and enrolment.")

        txn.commit()

    return apiVC.ok_json("Feedback successfully submitted!")


def _compute_fbq_score(pct_votes, fbs):
    fb_pts = {"stronglyagree": 5, "agree": 4,
                "neitheragreenordisagree": 3, "disagree": 2,
                "stronglydisagree": 1}
    score = 0
    for i, fb in enumerate(fbs):
        fb = fb.replace(' ', '').lower()
        pts = fb_pts.get(fb, 0)
        score += pts*pct_votes[i]/100

    return round(score, 2)


@C.rbac(permissions=["feedback.view_instructor_feedback"])
async def get_instructor_feedback(co_id, user_id, fb_type):
    is_current_user_in_role_and_id("FAC", "user_id", user_id, "Instructor attempted to access other's feedback.")
    # if VC.is_user_in_role("HOD") and not is_hod_for_course_offering(
    #     co_id, VC.logged_in_user().id):
    #     logging.error("HOD {0} attempted to access other's feedback. CO_ID={1}".format(VC.current_login_id(), co_id))
    #     return VC.error_json("You cannot access feedback of faculty from other department! This attempt has been reported.")

    co = DB.CourseOffering.get_or_none(int(co_id))
    if not co:
        return apiVC.error_json("Course offering not found!")

    fb_open_dt = None
    if fb_type == "MID_SEM_FB":
        fb_open_dt = get_event_date("SHOW_MIDSEM_FB_S", co.acad_session)
    elif fb_type == "END_SEM_FB":
        fb_open_dt = get_event_date("SHOW_ENDSEM_FB_S", co.acad_session)

    if not fb_open_dt:
        return apiVC.error_json("Feedback viewing date not setup for {}!".format(co.acad_session))

    if fb_open_dt > C.current_dt_str():
        return apiVC.error_json("Feedback viewing is not yet opened!")

    ci = co.instructors.where(DB.CourseInstructor.instructor == user_id)
    if not ci.exists():
        if apiVC.is_user_in_role("FAC"):
            return apiVC.error_json("Cannot access other course's feedback! This incident will be reported.")
        else:
            return apiVC.error_json("Course instructor not found!")

    cif_qry = ci[0].instructor_feedbacks.join(DB.FeedbackQuestion) \
        .join(DB.FeedbackForm).where(
        (DB.CourseInstructorFeedback.question.form.form_type
         == fb_type))

    if not cif_qry.exists():
        return apiVC.error_json("No feedback found for the instructor.")

    sql_qry = C.sql_by_id("get_instructor_feedback")
    cursor = DB.db.execute_sql(sql_qry, [ci[0].id, fb_type])
    questions_data = []
    scores = []
    for row in cursor.fetchall():
        ques, votes, feedbacks = row[0], row[1], row[2]
        v_arr = json.loads(votes)
        fb_arr = json.loads(feedbacks)
        total = sum(v_arr)
        pct_votes = [round(100 * p / total, 2) for p in v_arr]
        q_score = _compute_fbq_score(pct_votes, fb_arr)
        # We consider only those question which have the 1 - 5 scale points
        if total > 0 and q_score != 0:
            scores.append(q_score)
            # Append score to the question text
            ques = "{0} (Score: {1})".format(ques, q_score)

        item = {
            "question": ques,
            "chartdata": {
                "labels": fb_arr,
                "datasets": [
                    {
                        "label": "Responses in %",
                        "data": pct_votes
                    }
                ]
            }
        }
        questions_data.append(item)

    txtQuesData = cif_qry.where(DB.CourseInstructorFeedback.question.is_text == True)
    text_data = {}
    for obj in txtQuesData:
        if obj.feedback.strip():
            fq = obj.question.question
            if fq not in text_data:
                text_data[fq] = []

            text_data[fq].append(obj.feedback)

    avg_score = round(sum(scores)/len(scores), 2)
    score_exp = "Avg({0}) = {1} (out of 5)".format(" + ".join([str(x) for x in scores]), avg_score)
    res = {"course": co.course.title,
           "acad_session": co.acad_session,
           "questions_data": questions_data,
           "text_data": text_data,
           "score": score_exp}

    return apiVC.ok_json(res)


@C.rbac(permissions=["feedback.view_reports"])
async def download_feedback_stats(form_type, acad_session):
    if form_type == "-":
        form_type = ""
    if acad_session == "-":
        acad_session = ""

    cursor = DB.db.execute_sql(C.sql_by_id("generate_feedback_stats"),
                            [str(acad_session), str(acad_session), str(form_type)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="feedback_stats.csv",
                     as_attachment=True)


@C.rbac(permissions=["feedback.view_reports"])
async def download_course_wise_faculty_score(form_type, acad_session):
    if form_type == "-":
        form_type = ""
    if acad_session == "-":
        acad_session = ""

    cursor = DB.db.execute_sql(C.sql_by_id("course_wise_faculty_score"),
                            [str(form_type), str(acad_session)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="download_course_wise_faculty_score.csv",
                     as_attachment=True)


@C.rbac(permissions=["feedback.view_reports"])
async def download_quewise_facfeedbk_score(form_type, acad_session):
    if form_type == "-":
        form_type = ""
    if acad_session == "-":
        acad_session = ""

    cursor = DB.db.execute_sql(C.sql_by_id("que_wise_facfeedbk_score"),
                            [str(form_type), str(acad_session)])

    fp = apiVC.db_result_to_excel(cursor)
    return await send_file(fp,
                     attachment_filename="download_quewise_faculty_feedbk_score.csv",
                     as_attachment=True)
