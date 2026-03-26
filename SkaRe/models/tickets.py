from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .boats import Boat


class SailTicket(models.Model):
    """A physical sail ticket assigned to a boat for on-water tracking."""

    class Color(models.TextChoices):
        P550  = 'p550',  _('P550')
        SAIL  = 'sail',  _('Sailboat')
        OTHER = 'other', _('Other boat')
        SPARE = 'spare', _('Spare')

    class Status(models.TextChoices):
        ASHORE   = 'ashore',   _('Ashore')
        ON_WATER = 'on_water', _('On water')
        LOST     = 'lost',     _('Lost')

    code = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=10, choices=Color.choices)
    rfid_uid = models.CharField(max_length=100, blank=True, db_index=True)
    boat = models.ForeignKey(
        Boat,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sail_tickets',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASHORE,
    )
    pending_pairing = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} ({self.color})'


class SailTicketLog(models.Model):
    """Immutable log of every status change for a SailTicket."""

    ticket = models.ForeignKey(
        SailTicket,
        on_delete=models.CASCADE,
        related_name='logs',
    )
    status = models.CharField(max_length=20, choices=SailTicket.Status.choices)
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
        return f'{self.ticket.code} → {self.status} at {self.changed_at}'
