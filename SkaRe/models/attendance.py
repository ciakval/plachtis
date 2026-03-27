from django.db import models
from django.contrib.auth.models import User
from .registration import Person


class AttendanceLog(models.Model):
    """Records each change to a person's attendance status."""

    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='attendance_logs',
    )
    status = models.CharField(
        max_length=20,
        choices=Person.AttendanceStatus.choices,
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.person} → {self.status} at {self.changed_at}'
