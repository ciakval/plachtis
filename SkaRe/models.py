from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from solo.models import SingletonModel


class EventSettings(SingletonModel):
    """
    Model for event settings, including registration deadlines.
    Only one instance should exist.

    By default, set the deadline one year from now.
    """

    registration_deadline = models.DateTimeField(
        help_text="Deadline for creating new Units and Participants",
        default=timezone.now() + timezone.timedelta(days=365),
    )

    def __str__(self):
        return "Event Settings"

    class Meta:
        verbose_name = "Event Settings"
        verbose_name_plural = "Event Settings"

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


class ScoutUnit(models.Model):
    """
    Represents a scout unit the participants are a part of.

    When registering, users either choose an existing unit or create a new one.
    """

    name = models.CharField(max_length=200, help_text="Name of the scout unit")
    evidence_id = models.CharField(
        max_length=50, help_text="Unit evidence ID (e.g., 523.10, 816.08.001)"
    )

    def __str__(self):
        return f"{self.name} ({self.evidence_id})"

    class Meta:
        ordering = ["name"]


class Participant(models.Model):
    """
    Model representing a Participant in the system.
    """

    class ScoutCategory(models.TextChoices):
        ADULT = "ADULT", "Adult"
        ROVER = "ROVER", "Rover"
        SCOUT = "SCOUT", "Scout"
        CUB = "CUB", "Cub"

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(
        max_length=100, blank=True, help_text="Optional nickname"
    )
    date_of_birth = models.DateField(help_text="Date of birth")
    category = models.CharField(
        max_length=20,
        choices=ScoutCategory.choices,
        default=ScoutCategory.SCOUT,
        help_text="Scout category",
    )
    health_restrictions = models.TextField(
        blank=True, help_text="Any health restrictions or medical conditions"
    )
    dietary_restrictions = models.TextField(
        blank=True, help_text="Any dietary restrictions or preferences"
    )
    relevant_information = models.TextField(
        blank=True, help_text="Any relevant information about the participant"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="participants",
        help_text="User who created this participant",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.nickname:
            return f"{self.first_name} {self.last_name} ({self.nickname})"
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ["last_name", "first_name"]


class RegistrationBase(models.Model):
    """
    Abstract base model for registration entities.
    """

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        help_text="User who created this entry",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unlocked_for_editing = models.BooleanField(
        default=False,
        help_text="Whether this unit is unlocked for editing after the deadline (set by privileged users only)",
    )
    
    unit = models.ForeignKey(
        'ScoutUnit',
        on_delete=models.RESTRICT,
        related_name="%(class)ss",
        help_text="The scout unit this entry belongs to",
    )
    
    contact_email = models.EmailField(help_text="Contact email address")
    contact_phone = models.CharField(max_length=20, help_text="Contact phone number")

    relevant_information = models.TextField(
        blank=True, help_text="Any relevant information about the unit"
    )

    wishes_notes = models.TextField(
        blank=True, help_text="Wishes, notes for organizers, etc."
    )

    # Event logistics fields
    expected_arrival = models.DateTimeField(
        null=True, blank=True, help_text="Expected date and time of arrival"
    )
    expected_departure = models.DateTimeField(
        null=True, blank=True, help_text="Expected date and time of departure"
    )
    home_town = models.CharField(
        max_length=200, blank=True, help_text="Home town of the unit"
    )
    
    def can_be_edited(self, user):
        """Check if this unit can be edited by the given user"""
        # User must be the owner
        if self.created_by != user:
            return False

        # If registration is still open, allow editing
        if EventSettings.is_registration_open():
            return True

        # After deadline, only allow if unit is unlocked
        return self.unlocked_for_editing

    class Meta:
        abstract = True


class Unit(RegistrationBase):
    """
    Model representing a Unit in the system.
    """

    contact_person_name = models.CharField(
        max_length=200, help_text="Name of the contact person"
    )

    backup_contact_phone = models.CharField(
        max_length=20, blank=True, help_text="Optional backup contact phone"
    )

    # Boat estimates
    boats_p550 = models.PositiveIntegerField(
        default=0, help_text="Estimated number of P550 boats"
    )
    boats_sail = models.PositiveIntegerField(
        default=0, help_text="Estimated number of other sail-boats"
    )
    boats_paddle = models.PositiveIntegerField(
        default=0, help_text="Estimated number of paddle-powered boats"
    )
    boats_motor = models.PositiveIntegerField(
        default=0, help_text="Estimated number of motor-powered boats"
    )

    # Accommodation fields
    accommodation_expectations = models.TextField(
        blank=True, help_text="Accommodation expectations"
    )
    estimated_accommodation_area = models.CharField(
        max_length=100, blank=True, help_text="Estimated needed area for accommodation"
    )

    def __str__(self):
        return f"{self.unit.name} ({self.unit.evidence_id})"

    class Meta(RegistrationBase.Meta):
        ordering = ["unit_name"]

class Organizer(RegistrationBase, Participant):
    """
    Model representing an Organizer in the system.
    """
    
    class Division(models.TextChoices):
        MANAGEMENT = "MANAGEMENT", "Management"
        RACING = "RACING", "Racing"
        RESCUE = "RESCUE", "Rescue"
        CRISIS = "CRISIS", "Crisis"
        INFORMATION = "INFORMATION", "Information"
        MATERIAL = "MATERIAL", "Material"
        FOOD = "FOOD", "Food"
        PROGRAM = "PROGRAM", "Program"
        OTHERS = "OTHERS", "Others"
        
    division = models.CharField(
        max_length=20,
        choices=Division.choices,
        default=Division.OTHERS,
        help_text="Division the organizer belongs to",
    )
    
    class TransportOptions(models.TextChoices):
        PUBLIC = "PUBLIC", "Public Transport"
        CAR = "CAR", "Car"
        CAR_WITH_TRAILER = "CAR_WITH_TRAILER", "Car with Trailer"
        
    transport = models.CharField(
        max_length=20,
        choices=TransportOptions.choices,
        default=TransportOptions.PUBLIC,
        help_text="Transport method to the event",
    )
    
    need_lift = models.BooleanField(
        default=False,
        help_text="Whether the organizer needs a lift from the nearest transport hub",
    )
    
    want_travel_order = models.BooleanField(
        default=False,
        help_text="Whether the organizer wants a travel order for reimbursement",
    )
    
    class AccomodationOptions(models.TextChoices):
        WITH_UNIT = "WITH_UNIT", "With Unit"
        OWN_TENT = "OWN_TENT", "Own Tent"
        NEED_TENT = "NEED_TENT", "Need Tent"
    
    accommodation = models.CharField(
        max_length=20,
        choices=AccomodationOptions.choices,
        default=AccomodationOptions.OWN_TENT,
        help_text="Accommodation preference of the organizer",
    )
    
    codex_agreement = models.BooleanField(
        default=False,
        help_text="Whether the organizer agrees to follow the event codex",
    )

    def __str__(self):
        return f"Organizer {Participant.__str__(self)} ({self.division})"
