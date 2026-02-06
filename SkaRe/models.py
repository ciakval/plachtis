from datetime import datetime
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from solo.models import SingletonModel


class EventSettings(SingletonModel):
    """
    Model for event settings, including registration deadlines.
    Only one instance should exist.

    By default, set the deadline one year from now.
    """

    registration_deadline = models.DateTimeField(
        help_text=_("Deadline for creating new Units and Participants"),
        default=datetime(2026, 4, 1, 23, 59, 59, tzinfo=timezone.get_current_timezone()),
    )

    def __str__(self):
        return "Event Settings"

    class Meta:
        verbose_name = _("Event Settings")
        verbose_name_plural = _("Event Settings")

    @classmethod
    def is_registration_open(cls):
        """Check if registration is still open"""
        try:
            settings = cls.get_solo()
            if settings:
                return timezone.now() < settings.registration_deadline
            return True  # If no settings exist, allow registration
        except Exception:
            return True

    @classmethod
    def get_deadline(cls):
        """Get the registration deadline"""
        try:
            settings = cls.get_solo()
            return settings.registration_deadline if settings else None
        except Exception:
            return None


class Person(models.Model):
    """Represents a person in the system.
    """
    
    first_name = models.CharField(max_length=100, verbose_name=_("First name"))
    last_name = models.CharField(max_length=100, verbose_name=_("Last name"))
    nickname = models.CharField(
        max_length=100, blank=True, help_text=_("Optional nickname"), verbose_name=_("Nickname")
    )
    date_of_birth = models.DateField(help_text=_("Date of birth"), verbose_name=_("Date of birth"))
    
    class ScoutCategory(models.TextChoices):
        ADULT = "ADULT", _("Adult")
        ROVER = "ROVER", _("Rover")
        SCOUT = "SCOUT", _("Scout")
        CUB = "CUB", _("Cub")
        
    category = models.CharField(
        max_length=20,
        choices=ScoutCategory.choices,
        default=None,
        help_text=_("Scout category"),
        verbose_name=_("Category"),
        null=True, blank=True
    )
    
    health_restrictions = models.TextField(
        blank=True, help_text=_("Any health restrictions or medical conditions"),
        verbose_name=_("Health restrictions")
    )
    dietary_restrictions = models.TextField(
        blank=True, help_text=_("Any dietary restrictions or preferences"),
        verbose_name=_("Dietary restrictions")
    )
    relevant_information = models.TextField(
        blank=True, help_text=_("Any relevant information about the person"),
        verbose_name=_("Relevant information")
    )
    
    def __str__(self):
        if self.nickname:
            return f"{self.first_name} {self.last_name} ({self.nickname})"
        return f"{self.first_name} {self.last_name}"
    
class Entity(models.Model):
    """
    Represents a registration entity in the system.
    
    Registration entity is anything that can be registered:
    - Unit
    - Individual Participant
    - Organizer
    """

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        help_text=_("User who created this entry"),
        verbose_name=_("Created by"),
    )
    editors = models.ManyToManyField(
        User,
        related_name="editable_entities",
        blank=True,
        help_text=_("Users who can edit this entry (in addition to the creator)"),
        verbose_name=_("Editors"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unlocked_for_editing = models.BooleanField(
        default=False,
        help_text=_("Whether this unit is unlocked for editing after the deadline (set by privileged users only)"),
        verbose_name=_("Unlocked for editing"),
    )
    
    scout_unit_name = models.CharField(
        max_length=200,
        help_text=_("Name of the scout unit"),
        verbose_name=_("Scout unit name"),
        blank=True,
    )
    scout_unit_evidence_id = models.CharField(
        max_length=50,
        help_text=_("Unit evidence ID (e.g., 523.10, 816.08.001)"),
        verbose_name=_("Evidence ID"),
        blank=True,
    )
    
    contact_email = models.EmailField(
        help_text=_("Contact email address"),
        verbose_name=_("Contact email")
    )
    contact_phone = models.CharField(
        max_length=20,
        help_text=_("Contact phone number"),
        verbose_name=_("Contact phone")
    )

    # Event logistics fields
    expected_arrival = models.DateTimeField(
        null=True, blank=True,
        help_text=_("Expected date and time of arrival"),
        verbose_name=_("Expected arrival")
    )
    expected_departure = models.DateTimeField(
        null=True, blank=True,
        help_text=_("Expected date and time of departure"),
        verbose_name=_("Expected departure")
    )
    home_town = models.CharField(
        max_length=200, blank=True,
        help_text=_("Home town of the unit"),
        verbose_name=_("Home town")
    )
    
    def can_be_edited(self, user):
        """Check if this entity can be edited by the given user"""
        # User must be the owner or an editor
        is_owner = self.created_by == user
        is_editor = self.editors.filter(id=user.id).exists()
        
        if not (is_owner or is_editor):
            return False

        # If registration is still open, allow editing
        if EventSettings.is_registration_open():
            return True

        # After deadline, only allow if entity is unlocked
        return self.unlocked_for_editing
    
    def is_owner(self, user):
        """Check if the user is the owner (creator) of this entity"""
        return self.created_by == user
    
    def can_manage_editors(self, user):
        """Check if the user can add/remove editors (only owner can)"""
        return self.created_by == user

class Unit(models.Model):
    """
    Represents a registered unit (scout troop, oddil, stredisko) in the system.
    """
    
    entity = models.OneToOneField(
        Entity,
        on_delete=models.CASCADE,
        related_name="unit_profile",
        help_text=_("The registration entity associated with this unit"),
        verbose_name=_("Entity"),
    )
    
    contact_person_name = models.CharField(
        max_length=200,
        help_text=_("Name of the contact person"),
        verbose_name=_("Contact person name")
    )

    backup_contact_phone = models.CharField(
        max_length=20, blank=True,
        help_text=_("Optional backup contact phone"),
        verbose_name=_("Backup contact phone")
    )

    # Boat estimates
    boats_p550 = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of P550 boats"),
        verbose_name=_("P550 boats")
    )
    boats_sail = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of other sail-boats"),
        verbose_name=_("Sail boats")
    )
    boats_paddle = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of paddle-powered boats"),
        verbose_name=_("Paddle boats")
    )
    boats_motor = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of motor-powered boats"),
        verbose_name=_("Motor boats")
    )
    # Scarf field
    scarf_count = models.PositiveBigIntegerField(
        default=0,
        help_text=_("Number of scarves"),
        verbose_name=_("Scarf count")
    )
    # Hat field
    hat_count = models.PositiveBigIntegerField(
        default=0,
        help_text=_("Number of hats"),
        verbose_name=_("Hat count")
    )

    # Accommodation fields
    accommodation_expectations = models.TextField(
        blank=True,
        help_text=_("Accommodation expectations (small tents, large tent, caravan, ...)"),
        verbose_name=_("Accommodation expectations")
    )
    estimated_accommodation_area = models.CharField(
        max_length=100, blank=True,
        help_text=_("Estimated needed area for accommodation"),
        verbose_name=_("Estimated accommodation area")
    )

class RegularParticipant(Person):
    """
    Model representing a regular Participant in the system.
    
    Regular participant is a member of a specific Unit.
    """
    unit = models.ForeignKey(
        Unit,
        on_delete=models.RESTRICT,
        related_name="regular_participants",
        help_text=_("The unit this participant belongs to"),
        verbose_name=_("Unit"),
    )
    
class IndividualParticipant(Person):
    """
    Model representing an Individual Participant in the system.
    
    Individual Participants are those who register independently,
    not as part of a Unit.
    Therefore, they are an Entity on their own.
    """
    entity = models.OneToOneField(
        Entity,
        on_delete=models.CASCADE,
        related_name="individual_participant_profile",
        help_text=_("The registration entity associated with this individual participant"),
        verbose_name=_("Entity"),
    )

    # Boat estimates
    boats_p550 = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of P550 boats"),
        verbose_name=_("P550 boats")
    )
    boats_sail = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of other sail-boats"),
        verbose_name=_("Sail boats")
    )
    boats_paddle = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of paddle-powered boats"),
        verbose_name=_("Paddle boats")
    )
    boats_motor = models.PositiveIntegerField(
        default=0,
        help_text=_("Estimated number of motor-powered boats"),
        verbose_name=_("Motor boats")
    )
    # Scarf field
    scarf_count = models.PositiveBigIntegerField(
        default=0,
        help_text=_("Number of scarves"),
        verbose_name=_("Scarf count")
    )
    # Hat field
    hat_count = models.PositiveBigIntegerField(
        default=0,
        help_text=_("Number of hats"),
        verbose_name=_("Hat count")
    )

    # Accommodation fields
    accommodation_expectations = models.TextField(
        blank=True,
        help_text=_("Accommodation expectations (small tents, large tent, caravan, ...)"),
        verbose_name=_("Accommodation expectations")
    )
    estimated_accommodation_area = models.CharField(
        max_length=100, blank=True,
        help_text=_("Estimated needed area for accommodation"),
        verbose_name=_("Estimated accommodation area")
    )
    
    

class Organizer(Person):
    """
    Model representing an Organizer in the system.
    
    The Organizer is a special type of participant with additional fields
    related to their role in the event organization.
    """
    
    entity = models.OneToOneField(
        Entity,
        on_delete=models.CASCADE,
        related_name="organizer_profile",
        help_text=_("The registration entity associated with this organizer"),
        verbose_name=_("Entity"),
    )
    
    class Division(models.TextChoices):
        MANAGEMENT = "MANAGEMENT", _("Management")
        RACING = "RACING", _("Racing")
        RESCUE = "RESCUE", _("Rescue")
        CRISIS = "CRISIS", _("Crisis")
        INFORMATION = "INFORMATION", _("Information")
        MATERIAL = "MATERIAL", _("Material")
        FOOD = "FOOD", _("Food")
        PROGRAM = "PROGRAM", _("Program")
        OTHERS = "OTHERS", _("Others")
        
    division = models.CharField(
        max_length=20,
        choices=Division.choices,
        default=Division.OTHERS,
        help_text=_("Division the organizer belongs to"),
        verbose_name=_("Division"),
    )
    
    class TransportOptions(models.TextChoices):
        PUBLIC = "PUBLIC", _("Public Transport")
        CAR = "CAR", _("Car")
        CAR_WITH_TRAILER = "CAR_WITH_TRAILER", _("Car with Trailer")
        
    transport = models.CharField(
        max_length=20,
        choices=TransportOptions.choices,
        default=TransportOptions.PUBLIC,
        help_text=_("Transport method to the event"),
        verbose_name=_("Transport"),
    )
    
    need_lift = models.BooleanField(
        default=False,
        help_text=_("Whether the organizer needs a lift from the nearest transport hub"),
        verbose_name=_("Need lift"),
    )
    
    want_travel_order = models.BooleanField(
        default=False,
        help_text=_("Whether the organizer wants a travel order for reimbursement"),
        verbose_name=_("Want travel order"),
    )
    
    class AccomodationOptions(models.TextChoices):
        WITH_UNIT = "WITH_UNIT", _("With Unit")
        OWN_TENT = "OWN_TENT", _("Own Tent")
        CARAVAN = "CARAVAN", _("Caravan")
        NEED_TENT = "NEED_TENT", _("Need Tent")
        INSIDE_BUILDING = "INSIDE_BUILDING", _("Inside Building")
    
    accommodation = models.CharField(
        max_length=20,
        choices=AccomodationOptions.choices,
        default=AccomodationOptions.OWN_TENT,
        help_text=_("Accommodation preference of the organizer"),
        verbose_name=_("Accommodation"),
    )
    
    codex_agreement = models.BooleanField(
        default=False,
        help_text=_("Whether the organizer agrees to follow the event codex"),
        verbose_name=_("Codex agreement"),
    )

    def __str__(self):
        person_name = super().__str__()
        return f"Organizer {person_name} ({self.division})"
    
