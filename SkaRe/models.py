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


class Person(models.Model):
    """Represents a person in the system.
    """
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(
        max_length=100, blank=True, help_text="Optional nickname"
    )
    date_of_birth = models.DateField(help_text="Date of birth")
    
    class ScoutCategory(models.TextChoices):
        ADULT = "ADULT", "Adult"
        ROVER = "ROVER", "Rover"
        SCOUT = "SCOUT", "Scout"
        CUB = "CUB", "Cub"
        
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
        blank=True, help_text="Any relevant information about the person"
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
        help_text="User who created this entry",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    unlocked_for_editing = models.BooleanField(
        default=False,
        help_text="Whether this unit is unlocked for editing after the deadline (set by privileged users only)",
    )
    
    scout_unit_name = models.CharField(
        max_length=200,
        help_text="Name of the scout unit",
        blank=True,
    )
    scout_unit_evidence_id = models.CharField(
        max_length=50,
        help_text="Unit evidence ID (e.g., 523.10, 816.08.001)",
        blank=True,
    )
    
    contact_email = models.EmailField(help_text="Contact email address")
    contact_phone = models.CharField(max_length=20, help_text="Contact phone number")

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

class Unit(models.Model):
    """
    Represents a registered unit (scout troop, oddil, stredisko) in the system.
    """
    
    entity = models.OneToOneField(
        Entity,
        on_delete=models.CASCADE,
        related_name="unit_profile",
        help_text="The registration entity associated with this unit",
    )
    
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
        blank=True, help_text="Accommodation expectations (small tents, large tent, caravan, ...)"
    )
    estimated_accommodation_area = models.CharField(
        max_length=100, blank=True, help_text="Estimated needed area for accommodation"
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
        help_text="The unit this participant belongs to",
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
        help_text="The registration entity associated with this individual participant",
    )
    
    

class Organizer(Person):
    """
    Model representing an Organizer in the system.
    
    The Organizer is a special type of participant with additional fields
    related to their role in the event organization.
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
        CARAVAN = "CARAVAN", "Caravan"
        NEED_TENT = "NEED_TENT", "Need Tent"
        INSIDE_BUILDING = "INSIDE_BUILDING", "Inside Building"
    
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
        person_name = super().__str__()
        return f"Organizer {person_name} ({self.division})"
    
