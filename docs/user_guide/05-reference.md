# 5. Reference

Roles and what they can see, approval chains, a glossary and troubleshooting.

## Contents

1. [Roles and what they can see](#roles-and-what-they-can-see)
2. [Approval chains](#approval-chains)
3. [Dates that open and close things](#dates-that-open-and-close-things)
4. [Glossary](#glossary)
5. [Troubleshooting](#troubleshooting)

## Roles and what they can see

Every user has one role. A role is a set of permissions, and the menu bar shows only the items that the permissions allow (see [chapter 1](01-getting-started.md#the-home-page-and-the-menu-bar)).

The table shows the roles of a **new installation**. Your university can change what a role may do, or add roles, so what you see may differ. If an item is missing for you, ask the academic office whether your role should have it.

| Role | Who | Menus and notable items |
|---|---|---|
| Student (STU) | Students | *Student Record*; *Courses* (offered courses, slotwise, catalogue, course feedback); *Fees*; *University → Academic Events*; *Users → Profile Photo*; *PhD* for doctoral students. Everything is about their own records. |
| Faculty (FAC) | Instructors | *Courses* (offer, create, upload grades, view and mark attendance); *My Work* (courses offered, courses created, action pending); *PhD* (doctoral committees and progress reports); some *Reports*; *Users → Find User, Find Students*. |
| Advisor (ADV) | Batch advisors with an advisor role | *My Work → Pending Tasks*; *Courses* (view only, with attendance); *PhD*; some *Reports*; *Users* lookups. |
| Head of Dept. (HOD) | Heads of department | Faculty items for the department's courses, with *Pending Tasks*: enrolments for advisor, courses to forward, offerings to move to Enrolling. |
| Dean of Academics (DEA) | The dean | Everything the academic section has, except *Mark Attendance*, *New User*, *Add Users* and *Upload User Faces*. Approves courses and doctoral committees. |
| Academic Section (ACA) | Academic office staff | All *Users* items, all *Courses* items including feedback forms and statistics, all *Reports*, and the *University* items for dates, slots and credits data. |
| Research Section (RES) | Research office | Look-ups, *Courses* (view, create), *Reports*, *PhD*. |
| Placement Cell (PLA) | Placement office | Look-ups, course lists, *Reports* on credits and enrolments. |
| Guest (GUE) | Visitors | Look-ups, course lists, attendance view, some *Reports*. |
| Superuser (SUP) | The administrator | Set-up items: *University → Lists, Settings, Roles & Permissions, Grading Scheme*, and *Users* and *Courses* items to load data. See [Setting up AcadStack for your university](../university_setup.md). |

The administrator can see and change exactly what each role may do in *University → Roles & Permissions*.

## Approval chains

### Course enrolment

| Step | Status shown | Done by |
|---|---|---|
| Student requests | Pending Instructor Approval | The student |
| Instructor approves | Pending Advisor Approval | Instructor of the offering |
| Batch advisor approves | Enrolled | Batch advisor of the student's batch |

Possible outcomes: **Instructor Rejected**, **Advisor Rejected**, **Academic section Rejected**, **Dropped by Student**, **Withdrawn by Student**. The academic section can set any status directly.

### Course (the catalogue entry)

Draft → *Submit* by the author → **HoD Approval Pending** → *Forward* by the head of department → **Council Approval Pending** → *Approve* by the dean or academic section → **Approved**. Returned at the HoD step: **HoD Rejected**. Returned at the dean step: **Council Rejected**. A rejected course goes back to its author.

### Course offering

**Proposed** by the instructor → **Enrolling** (head of department or academic section) → **Running** (academic section). Finished offerings are shown as **Completed**. Returned offerings are **Declined**. An offering can be **Canceled**.

### Doctoral committee

**Draft** → *Submit to HoD* by the supervisor → **Submitted to HoD** → *Forward to Dean* by the head of department → **Forwarded to Dean** → *Approve* by the dean or academic section → **Approved**. Returns: **Returned to Supervisor**, **Returned to HoD**.

### PhD progress report

**Draft** → *Submit to DC Chair* by a committee member → **Submitted to DC Chair** → *Approve as DC Chair* by the chair → **Approved**. The academic office can also return a report to the member (**Returned to DC Member**).

## Dates that open and close things

All of these are set per session in *University → Academic Events*.

| Date range | What it allows |
|---|---|
| Course pre-registration, Course add/drop | Students requesting enrolment for credit, and dropping a course. |
| Course withdrawal | Students withdrawing from a course, and enrolling for audit. |
| Midsem course feedback, Course feedback | Students submitting mid-semester and end-semester feedback. |
| Grades submission | Faculty uploading grades. |
| Show feedback (midsem), Show feedback (endsem) | Faculty seeing their feedback results. |

## Glossary

| Term | Meaning |
|---|---|
| Academic session | A semester or term, for example `2026-I`. |
| Course | A catalogue entry: code, title, L-T-P, content, evaluation plan. Offered many times. |
| Course offering | A course offered in one session, with a section, a slot, instructors and a crediting categorisation. |
| Section | A group of students taking the same offering together. |
| Slot | A named block of the weekly timetable. Two courses in clashing slots cannot both be taken. |
| L-T-P, L-T-P-S-C | Lecture, tutorial and practical hours per week. With self-study hours and credits added for the longer form. |
| Crediting categorisation | The rule that says in which category an offering counts for a given programme, department and entry year. |
| Enrolment type | **Credit**, **Audit**, **Credit for Minor** or **Credit for Concent.** |
| Coordinator | The instructor of an offering who may upload its grades and attendance. |
| Batch, batch advisor | Students of one programme and department who joined in one year, and the faculty member who approves their enrolments. |
| SGPA, CGPA | Grade point average of a session, and cumulative. |
| Earned credits | Credits of courses passed. |
| DC | Doctoral committee. |
| PPR | PhD progress report. |
| TKP | Targeted Knowledge Profile: the knowledge areas a course targets. A course needs at least two ticked. |
| TGAP | Targeted Graduate Attribute Profile: the graduate attributes a course targets. A course needs at least two ticked. |
| Org. ID | A person's roll number or employee number. |

## Troubleshooting

| What you see | Why, and what to do |
|---|---|
| A menu or item is missing | Your role does not include it. Ask the academic office. |
| "You do not have required permissions to access." | The same, for a screen you opened directly. |
| "User is locked! Please contact admin." | Your account is locked. Contact the academic office. |
| "Invalid or expired reset key." | The key is older than 30 minutes, was mistyped, or you tried too often. Request a new one. |
| "Semester registration fees payment details/proof are required..." | Save your fee payment details first (*Fees → Fees Payment Record*). |
| "Course enrolment/add not open for ..." | The enrolment dates of the session have not started or have ended. See *University → Academic Events*. |
| "Slot timing not setup for slot ..." | The academic office must enter the slot's times (*University → Course Slot Timings*). |
| "Course ... is not offered for ... Kindly check the Crediting Categorization" | The offering has no categorisation for your programme, department and entry year. Contact the instructor or the academic office. |
| "Max. 24 credits allowed! ..." | You asked for more credits than the session allows. Drop something first. |
| "Grade uploading for ... is not open at this time." | The **Grades submission** dates have not started or have ended. |
| "Invalid header row in CSV" | Use the file you get from **Download Enrolled Students List**. Do not change its first row. |
| "Insufficient privileges. Only the course coordinator can upload attendance." | Only an instructor marked **Is Coord.** on the offering can do that. |
| "None of the enrolled students have their photos in the database!" | No enrolled student has a profile photo, so faces cannot be matched. |
| "Photo not found!" | You have not uploaded a profile photo yet. Harmless. |
| "Error when bulk enrolling students." | Someone matched is already enrolled in the offering. See [Bulk enrolling students in a course](04-academic-office-hod-dean.md#bulk-enrolling-students-in-a-course). |
| "Cannot change others' enrolment. Your attempt to do so has been reported." | You tried to change another person's record. The attempt is reported to the administrators. Do not edit addresses or requests by hand. |
| A grade or number looks wrong | Records confirmed by the academic section take precedence over what the screen shows. Ask the academic section. |

If none of this helps, use the email address on the **Help** page and say what you did, what you saw, and the exact message.
