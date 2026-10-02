# Setting up AcadStack for your university

This guide is for the academic office staff who set AcadStack up for a university. You do everything on screen, from the **University Setup** menu. You do not need to edit files, run SQL or change code.

Setting up means telling AcadStack about your university:

- your departments and programs, and the other lists the screens offer;
- the roles your staff and students have, and what each role may do;
- your academic sessions and their dates;
- your grading scheme;
- your course slot timings;
- your courses and users;
- the batch advisors.

The sections below follow the menu, top to bottom. Read **First login** and **Roles & Permissions** first, because a new administrator account cannot yet open every screen.

## Contents

1. [First login](#1-first-login)
2. [Roles & Permissions](#2-roles--permissions)
3. [Lists](#3-lists)
4. [Settings](#4-settings)
5. [Academic Events](#5-academic-events)
6. [Grading Scheme](#6-grading-scheme)
7. [Course Slot Timings](#7-course-slot-timings)
8. [Add Users](#8-add-users)
9. [Bulk Create Courses](#9-bulk-create-courses)
10. [Manage Batch Advisors](#10-manage-batch-advisors)
11. [A suggested order, and a final check](#11-a-suggested-order-and-a-final-check)

Screens save the row you edit when you press its save button, and show a short message at the top of the page. A message that does not start with "Saved" tells you what to fix.

## 1. First login

A new installation has one user: `admin`, with the role **Superuser**. The person who installed AcadStack gets its password from the server's startup output, where it is printed once.

1. Open the application's address and log in as `admin`.
2. Click the key icon at the top right and change the password.
3. Open **Manage Users → Find User**, open `admin`, and replace the email address `admin@localhost` with a real one. Save. Password reset emails go to this address.
4. Do **Roles & Permissions** (section 2) before anything else.

Other people log in with the login id you give them. A user created from a file has a random password nobody knows, and AcadStack sends no email. Each person sets their own password in one of two ways:

- On the login page they click **Password Reset**, enter their login id and the email address you registered for them, and follow the emailed key. This needs the server's email settings to be working.
- Or you open the user (**Manage Users → Find User**), press **Generate Password Reset Key**, and give the key to the person. It is valid for 30 minutes. They click **Password Reset** on the login page, enter their login id and email, press **Request Reset**, then enter a new password and the key.

## 2. Roles & Permissions

*University Setup → Roles & Permissions*

A **role** is a kind of user, such as Student, Faculty or Academic Section. A **permission** is one thing a role may do. Everything a user can see or do comes from the permissions of their role. Each user has one role.

A new installation comes with ten roles: Student, Academic Section, Faculty, Head of Dept., Dean of Academics, Superuser, Guest, Placement Cell, Advisor and Research Section. You can change their permissions, rename them, and add your own.

The Superuser role holds every permission the setup screens need. If your office staff will do the setup, you can instead give them users with the **Academic Section** role, which holds them too.

### Change a role or add one

- To change a role, click it, tick or untick permissions, and press **Save**. The role's code cannot change; its label can.
- To add a role, press **New role**, enter a code of up to 4 characters and a label, tick its permissions, and press **Save**. Always tick `app.access`, which lets the role use the application at all.
- A permission such as `courses.edit` comes in several versions, for example `:own` (only the user's own records) and `:any` (every record). Tick the version you mean.

### The three "roster" permissions

Some screens need to find *a kind of person*, for example "the instructors" or "the students". AcadStack does not guess this from a role's name. It asks which roles hold one of these permissions:

| Permission | Tick it for roles whose users count as… | What it controls |
|---|---|---|
| `roster.student` | students | The student lookup by entry number, bulk enrolment, grade sheets and student lists find these users. |
| `roster.instructor` | instructors | These users are offered wherever you choose an instructor: course offerings, batch advisors and the supervisor of a doctoral committee. |
| `roster.acad_section` | the academic section | These users receive the emails about grade submission. |

Examples:

- You add a role "Visiting Faculty" and want visiting faculty to be chosen as instructors. Tick `roster.instructor` on it.
- Heads of departments who also teach need `roster.instructor` on the Head of Dept. role. A new installation does not give it to them.

The student lookup and bulk enrolment find only students marked **Registered**; see [Add Users](#8-add-users).

## 3. Lists

*University Setup → Lists*

The drop-down lists on the screens differ between universities, so you define them here. A new installation has almost none. Fill them in before you add users or courses, because those use them.

The screen has two tabs: **University lists** (this section) and **Workflow labels** (described at the end).

### Working with a list

1. Choose a list in the **List** box.
2. To add an item, press **Add item**, fill in the new row and press its save button.
3. To change an item, edit its label, order or attributes and press its save button.
4. To stop offering an item, tick **Hidden** and save. Hidden items disappear from the drop-downs. Items cannot be deleted.

Each item has:

- a **code**, which is what AcadStack stores. It cannot be changed after saving, and it must be unique within the list. The longest code allowed differs by list (see the table below);
- a **label**, which people see (up to 200 characters);
- an **order**, which sorts the item within the list (new items go last);
- for some lists, **attributes** (see below).

### The lists

| List | What it is | Longest code | Attributes |
|---|---|---|---|
| Departments | Departments and sections. `ALL` ("All Departments") is built in and cannot be hidden. | 4 | none |
| Degrees | Your programs, such as B.Sc., M.Sc., PhD. | 20 | `level`, `printed_name`, `specialisation` |
| CourseSlots | The names of your timetable slots, such as A, B, C. | 10 | none |
| CourseTypes | Kinds of course, such as core, elective, project. | 4 | `group` |
| MinorConcSpecialization | Minors, concentrations and specialisations a student can take. | 10 | none |
| PersonCategories | The category recorded for a person, such as General or SC. | 10 | none |
| DegreeType | The type of a student's degree, such as Regular or Honors. | 10 | none |
| CourseFreqs | How often a course runs, such as Odd semester or Any semester. | 1 | none |
| CalendarEvents | Extra dated events you want on *Academic Events*, such as Orientation week. | 20 | none |

Some details:

- **Degrees.**
  - `level` is `UG`, `PG` or `PHD`. It decides which grading scheme applies to the program's students, and a student sees the PhD menu only if the program's level is `PHD`. Give every program a level.
  - `printed_name` is the program's name as printed on grade sheets and degree certificates, for example "Bachelor of Science". If you leave it blank, the label is printed.
  - `specialisation` is an extra line printed under the degree name on the certificate. Leave it blank if you have none.
- **CourseTypes.** `group` is `CORE` or `ELECTIVE`. Reports that count core and elective credits use it. A type with no group is counted as neither.
- **CourseFreqs.** A course created from a file gets the frequency `A`. Add an item with the code `A` (for example "Any semester") so that these courses show a label.
- **CalendarEvents.** An event's code must not clash with a built-in event or with another event. For example, `CLASSES` is refused. Events you add here show on *Academic Events* as extra rows with optional start and end dates.

Messages you may meet:

- "A Departments code must be 1 to 4 characters." The code is too long for that list.
- "Departments already has the code MTH." Codes are unique within a list.
- "The list and code of a saved item can't change." Hide the item and add a new one.

### Workflow labels

The second tab, **Workflow labels**, is for the words the application itself uses: course statuses, enrolment statuses, attendance codes, calendar event names and so on. AcadStack's logic depends on these codes, so you cannot add or remove one. You can change the label people see.

1. Click **Workflow labels**.
2. Edit the text next to a code, for example change "Credit for Minor" to "Credit towards Minor".
3. Press **Save** at the top. A label you changed gets a **Use default** button that puts the original back.

Under **EnrolTypes** you can also tick **Hidden** for an enrolment type your university does not use. Hidden types are not offered when students enrol. Credit (`C`) cannot be hidden.

## 4. Settings

*University Setup → Settings*

Each setting is one row with its own save button. Press the button on the row you changed. A value that is not acceptable is refused with a message such as "Invalid value for help_email".

| Setting | What it does | Default |
|---|---|---|
| `max_credits` | The most credits a student may enrol for in one session (1 to 100). | 24 |
| `face_match_tolerance` | How strictly photo attendance matches faces (above 0, up to 1). Lower is stricter. | 0.45 |
| `lockout_limit` | How many wrong password-reset keys, and how many keys issued, are allowed for a login before it is locked out (1 to 100). | 5 |
| `page_size` | Rows per page in search results (1 to 500). | 25 |
| `fees_check_enabled` | When on, students must submit their fee payment details before they can enrol. | on |
| `institute_name` | Your institute's name. Printed on grade sheets and certificates. | blank |
| `institute_place` | Your institute's place. Printed on certificates ("Given at …"). | blank |
| `app_url` | The web address of this application, starting with `http://` or `https://`. Given to users in emails. | blank |
| `help_email` | The address for help requests. It is also shown to users on the Help page and the login page, and receives access-violation alerts. | blank |
| `broadcast_emails` | Addresses that receive the academic calendar alerts. Enter one address per line. | none |

Something printed or sent with a blank value leaves that part out. Set the institute name and place before you print any certificate.

A newly saved `help_email` appears on the Help page the next time a user logs in.

## 5. Academic Events

*University Setup → Academic Events*

An **academic session** is a term, such as "Fall2026", with its calendar. Sessions are created here, by entering their dates. There is no separate "add session" screen.

### Creating a session

1. In **Event dates for academic session**, type the session's name (up to 10 characters, any text, for example `Fall2026` or `2026-I`).
2. Tick **Additional session** if the term runs alongside the regular ones, such as a summer term. Leave it unticked for regular sessions.
3. Enter a start and end date for each event in the list (below). Every event except the optional ones must have its dates.
4. Press **Save** and confirm.

Rules the screen enforces:

- A new session needs its **Academic session** start and end dates, because the application orders sessions and chooses the current one by them.
- Every other date must fall between the session's start and end dates. The exception is **Result declaration**, which may be later. Otherwise you get "Please ensure that all dates are within the academic session start and end dates!"
- The session name is permanent, and at most 10 characters.

To change a session later, choose it in **Load for session** at the top, edit the dates and save. The pickers elsewhere in the application offer the current session and the next two; to load an older one, tick **Other** and type its name.

### What each event does

The event names can be relabelled on the **Workflow labels** tab of *Lists*. Their meaning stays the same.

| Event | What it does |
|---|---|
| Academic session | Start and end of the term. |
| Course pre-registration | Students can add and drop courses between these dates. |
| Classes | On the start date, offerings that are still "Enrolling" become "Running". |
| Course add/drop | A second window in which students can add or drop courses. |
| Midsem course feedback | Students can submit mid-semester feedback between these dates. |
| Mid sem exams | Shown on the calendar. Nothing acts on these dates. |
| Course withdrawal | Students can withdraw from a course between these dates. |
| End sem exams | Shown on the calendar. Nothing acts on these dates. |
| Course feedback | Students can submit end-of-term feedback between these dates. |
| Grades submission | Instructors can submit grades between these dates. After the end date, running offerings become "Completed". |
| Show feedback (midsem), Show feedback (endsem) | The date from which the feedback results can be seen. |
| Result declaration | A single date. Students see their grades only from this date. |
| Session closed | Set only by closing the session (below). |

Any events you added under *Lists → CalendarEvents* appear below these as optional rows, with the same date-range rule.

### Closing a session

When a session is over and all its grades are in, press **Close session**. This freezes the credits of its enrolments, so that later changes to courses do not change transcripts. After that, a grade change needs a reason, and the grading scheme cannot be changed in a way that alters the session's results (see [Grading Scheme](#6-grading-scheme)). **It cannot be undone.**

A session cannot be closed while an offering is still enrolling or running, or while grades are pending. The message names the courses. You need the `sessions.close` permission.

## 6. Grading Scheme

*University Setup → Grading Scheme*

A grading scheme says which grades exist and how each one counts. A new installation has one 10-point scheme for each program level (UG, PG, PHD): A is 10 points, A- 9, B 8, B- 7, C 6, C- 5, D 4, E 2, F 0, plus NP, NF, I, W, S and U, which carry no points. Change these to match your university.

NA ("not graded yet") is built in. Do not add it.

### The screen

Choose a scheme in the **Scheme** box. For the chosen scheme you can set:

- **Name**, for your own reference.
- **Program level**: `UG`, `PG` or `PHD`. A program uses the schemes of its level (the `level` you set on the program in *Lists → Degrees*).
- **From session** and **Until session**: the sessions the scheme applies to. Leave **From** blank for "from the start" and **Until** blank for "no end". The names must be sessions that exist (see [Academic Events](#5-academic-events)); only the current and next two are suggested, so type the name of an earlier session.
- The **grade table**. For each grade:
  - **Grade**: 1 or 2 characters, in capitals.
  - **Points**: its grade points, or blank for a grade with none.
  - **Earns credit**: the student earns the course's credits.
  - **In CGPA**: counted in SGPA and CGPA. A grade in the CGPA needs points and must earn credit.
  - **Credit, no GPA**: the credits are kept out of the SGPA. Whether credit is earned is still set by **Earns credit**.
  - **Left out of GPA**: the credits are left out of the GPA altogether (for example I or W). A grade with either of these two boxes ticked has no points.
  - **Audit allowed**: the grade can be given to a student auditing the course.

Buttons: **Add grade**, **Copy scheme**, **Delete scheme** and, at the top, **Save**. Nothing is stored until you press **Save**.

### Common changes

- **Change the grades for good from a session onward.** Press **Copy scheme**, name the copy, set **From session** to the first session it applies to, and change the grades. Then open the old scheme and set its **Until session** to the session before.
- **A one-off change in a single session.** Copy the scheme, and set both **From** and **Until** to that session.

If more than one scheme of a level covers a session, the one with the **narrowest** range applies. For that reason, two schemes of the same level must either not overlap, or one's range must lie wholly inside the other's. Otherwise the save is refused, for example: "Schemes UG Fall2026 only and UG Fall2026 only (copy) overlap; for the same level, one range must lie inside the other."

Every level needs at least one scheme. The screen refuses a save that leaves one without.

### Closed sessions are protected

A save is refused if it would change the grading rules that apply to a session that has been closed. For example: "Session Fall2026 is closed, and this change alters the grading rules of its UG students." Adding rules for a period that is still open is fine.

## 7. Course Slot Timings

*University Setup → Course Slot Timings*

A **slot** is a named block of the weekly timetable. When you offer a course you choose a slot, and AcadStack uses the slot's times to warn a student whose courses clash. **A course offered in a slot that has no timings cannot be enrolled in**, so enter the timings of every slot you use.

The slot names come from *Lists → CourseSlots*; add them there first.

1. Press **Add**. A new row appears.
2. Choose the **Slot** and the **Week day**.
3. Enter the **Start time** and **End time** as four-digit 24-hour numbers without a colon: `900` for 9:00 and `1450` for 2:50 pm.
4. Press the green save button on the row and confirm.

A slot with classes on several days has one row per day. Use the red button to delete a row.

Messages you may meet:

- "Start time should be before the end time!"
- "Cannot save duplicate record. Please make sure the slot data is unique." The same slot, day and start time already exists.

The times are not checked as clock times, so `975` would be accepted. Check what you type.

## 8. Add Users

*University Setup → Add Users*

Use this to create many users, students and staff, from a spreadsheet. For one user, use **Manage Users → New User** instead.

Before you start, set up the lists the file refers to: departments and programs (section 3), and the roles (section 2).

### The file

Save the spreadsheet as **CSV** (comma separated values, UTF-8). The first row must be the column names below, spelled exactly. Use one row per person.

```
org_id,login_id,first_name,last_name,role,department,degree,year_of_entry,email
E101,asha.rao,Asha,Rao,FAC,PHY,,,asha.rao@riverside.example
S2601,s2601,Meera,Nair,STU,PHY,BSC,2026,meera.nair@riverside.example
```

| Column | What to enter |
|---|---|
| `org_id` | The person's roll number or employee number. Unique, up to 40 characters. |
| `login_id` | The id they log in with. Unique, up to 40 characters. |
| `first_name`, `last_name` | The name (up to 100 characters each). |
| `role` | A role code from **Roles & Permissions**, in capitals, such as `STU` or `FAC`. Required. |
| `department` | A department code from **Lists → Departments**. |
| `degree` | A program code from **Lists → Degrees**. Leave empty for staff. |
| `year_of_entry` | The four-digit year the student joined, such as `2026`. Leave empty for staff. |
| `email` | The person's email address. Unique, up to 150 characters. |

### Upload

1. Press **Choose file** and select the file. The screen shows a preview. The preview reads the columns by their position, so keep them in the order above for it to look right; the upload itself goes by the column names.
2. Press **Upload** and confirm.

AcadStack answers with a count, for example: "Created 5 new users. Updated 0 users: []. Failed 0 records: []".

### What to know

- **Wrong rows are skipped; the others are saved.** The message lists each skipped row by its line number in the file, with the reason: an unknown role, department or degree code, a year that is not four digits, or an `org_id`, `login_id` or email address already used by someone else. Fix those rows and upload the file again; the rows already saved are then updated, not duplicated.
- **A missing column refuses the whole file.** The message names the column.
- **A second upload updates.** A row whose `org_id` or `login_id` already exists updates that person's details and does not change their password. The message lists them under "Updated".
- **New students are marked Registered.** A new user whose role holds `roster.student` gets the status **Registered**, so the student lookup and bulk enrolment find them. An upload that updates an existing person leaves their status as it is.
- **Passwords.** Users start without a usable password; see [First login](#1-first-login) for how they set one.

## 9. Bulk Create Courses

*University Setup → Bulk Create Courses*

Use this to create your catalogue of courses from a spreadsheet. For a single course, use **Courses → Create New Course**.

### The file

Save as **CSV** (UTF-8), with this first row:

```
code,title,ltp,level
PHY101,Mechanics,3-1-0-4-4,UG
PHY102,Optics Lab,0-0-3-3-1.5,UG
MTH501,Real Analysis,3-0-0-6-3,PG
GEN100,Writing Skills,2-0-0-2-2,ALL
```

| Column | What to enter |
|---|---|
| `code` | The course code, in whatever format your university uses. Unique, up to 20 characters. |
| `title` | The course title, up to 200 characters. |
| `ltp` | The credit structure as five numbers joined by dashes: **L-T-P-S-C**. Lecture, tutorial and practical hours, then self-study hours, then credits. For example `3-0-2-6-4`. A number may have decimals, such as `1.5`. All five parts are required. |
| `level` | Who may take the course: `UG`, `PG` or `ALL` (open to all levels). Capitals or lower case both work. |

AcadStack does not work out S or C for you; it stores what you give.

### Upload

1. Press **Choose File** and select the file. The screen previews the rows.
2. Press **Upload** and confirm. You get "Created new courses successfully!"

### What to know

- **The whole file is accepted or refused.** If one row is wrong, no course is created, and the message names the first problem, such as "Course PHY104: ltp must be in the L-T-P-S-C format, e.g. 3-0-2-6-4." or "Course PHY103: level must be one of UG, PG, ALL."
- **A course code that already exists refuses the file.** The message lists the codes. Remove those rows and upload again. To change an existing course, edit it under **Courses**.
- **New courses are created as Approved**, with the frequency `A` ("any semester"; see *Lists → CourseFreqs*).
- The level also decides who may edit the course: a user with `courses.edit:pg` edits `PG` and `ALL` courses.

## 10. Manage Batch Advisors

*University Setup → Manage Batch Advisors*

A **batch** is the students who joined a program in one year. Its **batch advisor** is the faculty member who approves those students' course enrolments. You assign one advisor per entry year, program and department.

The faculty member must belong to a role that holds `roster.instructor` (see section 2). For a new installation, that is the Faculty role.

1. Enter the **Entry Year**, for example `2026`.
2. Choose the **Dept.** This is the department of the faculty member who will be the advisor.
3. Choose the **Degree**, which is the program.
4. Press **Find**. The screen shows the current advisor, or "No advisor found for BSC PHY 2026".
5. To assign or replace the advisor, start typing the faculty member's name (at least three letters) in the box, pick them from the list that appears, and press **Assign**. Confirm.

Because the department you choose is the advisor's own, pick the same department that the advisor is recorded under; otherwise a later **Find** will not show them.

## 11. A suggested order, and a final check

A workable order for a new university:

1. First login and **Roles & Permissions**: add any roles of your own, with their roster permissions.
2. **Lists**: departments, programs (with their level and printed name), course types, slots, and the other lists. Add `A` to course frequencies.
3. **Settings**: institute name and place, web address, help email.
4. **Academic Events**: the current session, and the next one.
5. **Grading Scheme**: check the grades, and adjust them.
6. **Course Slot Timings**: the times of every slot.
7. **Add Users**: staff first, then students.
8. **Bulk Create Courses**.
9. **Manage Batch Advisors**.

To check that it all hangs together, offer a course for enrolment under **Courses → Offer a Course For Enrolment** and see that:

- the session, department and slot you set up appear in the drop-downs;
- the instructor you search for can be chosen;
- when you enrol a test student, they are found by their roll number.

If something you set up does not appear, the usual causes are a hidden list item, a student who is not marked Registered, a role without the matching roster permission, or a slot with no timings.
