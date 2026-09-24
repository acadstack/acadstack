"""Attendance figures derived from enrolment records.

The minimum-attendance requirement (models.py's AcademicCalendar
docstring names it MIN_ATTEND_REQD) lives in settings_store's
"attendance.min_percent_required", not here and not as versioned policy.
It is purely informational today -- nothing reads it to block grading,
registration or any other workflow, it only shades the percentage
red wherever the frontend already displays it (StudentAcademics.vue,
EnrolledStudents.vue), via static_data_dict()'s
MinAttendancePercentRequired. It is a settings_store value rather than a
policy_store version because, under that flag-only scope, changing it
does not need to change anything about an already-issued document -- see
policy_store.py's module docstring for that test. If a future phase
makes it gate an actual decision (blocking grade entry, say), that
decision would need to be evaluated under the threshold in force for the
relevant session, which is exactly when this should move to policy_store
instead.
"""


def percent_for_enrolment(enrolment):
    """Percentage of classes the student was present for, over all
    attendance rows of ``enrolment``.

    Returns the integer ``0`` when no attendance has been recorded and a
    two-decimal *string* otherwise -- the mixed return type is what the
    frontend has always been served, so it is preserved here rather than
    normalised.
    """
    present_count = 0
    total = 0
    for row in enrolment.attendance:
        if row.attend == 'P':
            present_count = present_count + 1
        total = total + 1
    if total == 0:
        return 0
    percent = float(present_count) / float(total)
    return '%.2f' % round(percent * 100, 2)
