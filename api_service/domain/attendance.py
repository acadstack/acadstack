"""Attendance figures derived from enrolment records."""


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
