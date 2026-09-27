# Dept wise average scores for the question
with fb_data(login_id, course_code, dept_name,
	acad_session, question, q_score, total_votes)
as (
	SELECT u.login_id, x.code as course_code,
    p.dept_name, x.acad_session, x.question,
	sum(x.fbq_pts)/sum(x.votes) q_score,
	sum(x.votes) total_votes
    
	FROM (SELECT COUNT(*) votes, 
			COUNT(*) * case 
				when cif.feedback='strongly agree' then 5
				when cif.feedback='agree' then 4
				when cif.feedback='neither agree nor disagree' then 3
				when cif.feedback='disagree' then 2
				when cif.feedback='strongly disagree' then 1
				else 0
			end as fbq_pts,
			ci.instructor_id as user_id,
			ff.form_type, fq.question, cif.feedback,
			cif.acad_session, c.title, c.code
		FROM acadstack_db.courseinstructorfeedback cif
		JOIN acadstack_db.feedbackquestion fq ON fq.id = cif.question_id
		JOIN acadstack_db.feedbackform ff ON ff.id = fq.form_id
		JOIN acadstack_db.courseinstructor ci ON ci.id = cif.instructor_id
		JOIN acadstack_db.courseoffering co ON co.id = ci.offering_id
		JOIN acadstack_db.course c ON c.id = co.course_id
		WHERE fq.is_text = FALSE
			AND ff.form_type = 'END_SEM_FB'
		GROUP BY ci.instructor_id,
			ff.form_type , fq.question , cif.feedback , 
			cif.acad_session , c.title , c.code
		ORDER BY fq.question) x

	join acadstack_db.user u on u.id=x.user_id
	join acadstack_db.person p on p.id=u.person_id
	GROUP BY x.question, x.user_id, x.code, x.acad_session
	having q_score > 0
	ORDER BY x.question, dept_name, q_score
	)

select dept_name, acad_session, question, 
		avg(q_score) as avg_score
from fb_data
group by dept_name, acad_session, question
order by question, avg_score;


# Course-wise faculty scores
with fb_data(login_id, course_code, dept_name,
	acad_session, question, q_score, total_votes)
as (
	SELECT u.login_id, x.code as course_code,
    p.dept_name, x.acad_session, x.question,
	sum(x.fbq_pts)/sum(x.votes) q_score,
	sum(x.votes) total_votes
    
	FROM (SELECT COUNT(*) votes, 
			COUNT(*) * case 
				when cif.feedback='strongly agree' then 5
				when cif.feedback='agree' then 4
				when cif.feedback='neither agree nor disagree' then 3
				when cif.feedback='disagree' then 2
				when cif.feedback='strongly disagree' then 1
				else 0
			end as fbq_pts,
			ci.instructor_id as user_id,
			ff.form_type, fq.question, cif.feedback,
			cif.acad_session, c.title, c.code
		FROM acadstack_db.courseinstructorfeedback cif
		JOIN acadstack_db.feedbackquestion fq ON fq.id = cif.question_id
		JOIN acadstack_db.feedbackform ff ON ff.id = fq.form_id
		JOIN acadstack_db.courseinstructor ci ON ci.id = cif.instructor_id
		JOIN acadstack_db.courseoffering co ON co.id = ci.offering_id
		JOIN acadstack_db.course c ON c.id = co.course_id
		WHERE fq.is_text = FALSE
			AND ff.form_type = 'END_SEM_FB'
		GROUP BY ci.instructor_id,
			ff.form_type , fq.question , cif.feedback , 
			cif.acad_session , c.title , c.code
		ORDER BY fq.question) x

	join acadstack_db.user u on u.id=x.user_id
	join acadstack_db.person p on p.id=u.person_id
	GROUP BY x.question, x.user_id, x.code, x.acad_session
	having q_score > 0
	ORDER BY x.question, dept_name, q_score
	)

select login_id, acad_session, course_code, 
		avg(q_score) as faculty_score, total_votes
from fb_data
group by login_id, acad_session, course_code, total_votes
order by faculty_score