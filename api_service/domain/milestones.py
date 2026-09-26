"""Academic milestones: the configured sequence, and recording one.

The sequence is the "milestones" controlled vocabulary (items carrying
``code``/``label``/``sequence``/``applies_to``; see vocab_defaults.py), so
it is edited in the admin vocabulary editor and exported with the rest of
the configuration. An ``AcademicMilestone`` stores one of its codes, and
recording an unknown code is refused. config_integrity refuses to remove a
code a student has reached or a workflow still records.
"""

import logging
from typing import List

import models as M
import settings_store as ST
from domain import persistence
from domain.context import Actor
from domain.errors import PolicyViolation

VOCAB = "milestones"

DC_PROPOSED = "DC_PROPOSED"
DC_APPROVED = "DC_APPROVED"


def definitions() -> List[dict]:
    """The milestone items in sequence order."""
    return sorted(ST.vocab(VOCAB), key=lambda d: d["sequence"])


def codes() -> List[str]:
    return [d["code"] for d in definitions()]


def record(actor: Actor, dc_id, student_id, code) -> M.AcademicMilestone:
    """Records that ``student_id`` reached milestone ``code``.

    Idempotent: a DC approved, returned and approved again has reached
    DC_APPROVED once, and the (dc, student, milestone) unique index
    would otherwise fail the second approval.
    """
    if code not in codes():
        raise PolicyViolation(f"Unknown academic milestone: {code}")
    existing = M.AcademicMilestone.get_or_none(
        (M.AcademicMilestone.dc == dc_id) &
        (M.AcademicMilestone.student == student_id) &
        (M.AcademicMilestone.milestone == code))
    if existing:
        return existing
    amo = M.AcademicMilestone(dc=dc_id, student=student_id, milestone=code)
    persistence.save(amo, actor)
    logging.debug(f"Recorded milestone {code} for student {student_id}.")
    return amo
