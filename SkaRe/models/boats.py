from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .registration import Person


class BoatClass(models.Model):
    class Category(models.TextChoices):
        SAIL = "SAIL", _("Sail")
        OTHER = "OTHER", _("Other")

    name = models.CharField(max_length=100, verbose_name=_("Name"))
    category = models.CharField(
        max_length=10,
        choices=Category.choices,
        verbose_name=_("Category"),
    )
    is_other = models.BooleanField(
        default=False,
        help_text=_("Marks the catch-all 'Other' entry for this category. Convention only — no DB constraint."),
        verbose_name=_("Is other"),
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text=_("Controls display order in dropdowns."),
        verbose_name=_("Order"),
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name = _("Boat class")
        verbose_name_plural = _("Boat classes")

    def __str__(self):
        return self.name


class Boat(models.Model):
    """
    A boat registered for the event.
    Owner (created_by) or InfoDesk group members can edit.
    Only the creator can delete.
    No editing deadline in Phase 1.
    """
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='boats',
        help_text=_("Deleting the user also deletes their boats — consistent with Entity.created_by."),
        verbose_name=_("Created by"),
    )
    boat_class = models.ForeignKey(
        BoatClass,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('boat class'),
    )
    class_supplement = models.CharField(
        verbose_name=_('class supplement'),
        max_length=200, blank=True,
    )
    sail_number = models.CharField(verbose_name=_('sail number'), max_length=50, blank=True)
    name = models.CharField(verbose_name=_('Boat name'), max_length=200)
    description = models.TextField(verbose_name=_('description'), blank=True)
    sail_area = models.DecimalField(
        verbose_name=_('sail area'),
        max_digits=8, decimal_places=2, null=True, blank=True,
    )
    hull_color             = models.CharField(verbose_name=_('hull color'), max_length=50)
    # Not all boats have sails, make it optional
    sail_color             = models.CharField(verbose_name=_('sail color'), max_length=50, blank=True, null=True)
    harbor_number = models.CharField(verbose_name=_('harbor number'), max_length=100, blank=True)
    harbor_name = models.CharField(verbose_name=_('harbor name'), max_length=200, blank=True)
    contact_person = models.CharField(verbose_name=_('contact person'), max_length=200)
    contact_phone = models.CharField(verbose_name=_('contact phone'), max_length=50)
    vessel_registry_number = models.CharField(verbose_name=_('vessel registry number'), max_length=50, blank=True)
    engine_power_hp        = models.PositiveSmallIntegerField(verbose_name=_('engine power (hp)'), null=True, blank=True)
    willing_to_lend = models.BooleanField(
        default=False,
        verbose_name=_('willing to lend'),
        help_text=_('Check if you are willing to lend this boat for the race'),
    )
    visible_to = models.ManyToManyField(
        User,
        blank=True,
        related_name='borrowed_boats',
        verbose_name=_('visible to'),
        help_text=_('Users who can see and select this boat when registering a crew'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Boat")
        verbose_name_plural = _("Boats")

    def __str__(self):
        if self.sail_number:
            return f"{self.sail_number} {self.name}"
        return self.name

    def can_be_edited(self, user):
        """Creator or InfoDesk group member can edit. No deadline check in Phase 1."""
        return self.created_by == user or user.groups.filter(name='InfoDesk').exists()


class Crew(models.Model):
    CATEGORY_Q  = 'Q'
    CATEGORY_S  = 'S'
    CATEGORY_R  = 'R'
    CATEGORY_D  = 'D'
    CATEGORY_SN = 'SN'
    CATEGORY_DN = 'DN'
    CATEGORY_OZ = 'OZ'
    CATEGORY_OD = 'OD'
    CATEGORY_MS = 'MS'

    CATEGORY_CHOICES = [
        (CATEGORY_Q,  _('Q – Žabičky a vlčata')),
        (CATEGORY_S,  _('S – Skautky a skauti')),
        (CATEGORY_R,  _('R – Rangers a roveři')),
        (CATEGORY_D,  _('D – Dospělí')),
        (CATEGORY_SN, _('SN – Skautští námořníci')),
        (CATEGORY_DN, _('DN – Dospělí námořníci')),
        (CATEGORY_OZ, _('OŽ – Open Žáci')),
        (CATEGORY_OD, _('OD – Open Dospělí')),
        (CATEGORY_MS, _('MS – Modrá stuha')),
    ]

    boat = models.ForeignKey(
        Boat,
        on_delete=models.PROTECT,
        verbose_name=_('boat'),
    )
    category = models.CharField(
        max_length=3,
        choices=CATEGORY_CHOICES,
        verbose_name=_('category'),
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('created by'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('boat', 'category')
        verbose_name = _('crew')
        verbose_name_plural = _('crews')

    def __str__(self):
        return f"{self.boat} – {self.get_category_display()}"

    def can_be_edited(self, user):
        """Creator or InfoDesk group member can edit. No deadline check in Phase 1."""
        return self.created_by == user or user.groups.filter(name='InfoDesk').exists()


class CrewMember(models.Model):
    ROLE_HELMSMAN = 'helmsman'
    ROLE_CREW     = 'crew'
    ROLE_CHOICES  = [
        (ROLE_HELMSMAN, _('Kormidelník')),
        (ROLE_CREW,     _('Člen posádky')),
    ]

    crew = models.ForeignKey(
        Crew,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name=_('crew'),
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name=_('role'),
    )
    participant = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        verbose_name=_('participant'),
    )

    class Meta:
        verbose_name = _('crew member')
        verbose_name_plural = _('crew members')

    def __str__(self):
        return f"{self.get_role_display()}: {self.participant}"
