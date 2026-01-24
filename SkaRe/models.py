from django.db import models


class Unit(models.Model):
    """
    Model representing a Unit in the system.
    """
    unit_name = models.CharField(max_length=200, help_text="Name of the unit")
    unit_evidence_id = models.CharField(max_length=50, help_text="Unit evidence ID (e.g., 523.10, 816.08.001)")
    contact_person_name = models.CharField(max_length=200, help_text="Name of the contact person")
    contact_email = models.EmailField(help_text="Contact email address")
    contact_phone = models.CharField(max_length=20, help_text="Contact phone number")
    backup_contact_phone = models.CharField(max_length=20, blank=True, help_text="Optional backup contact phone")
    relevant_information = models.TextField(blank=True, help_text="Any relevant information about the unit")
    
    # Event logistics fields
    expected_arrival = models.DateTimeField(null=True, blank=True, help_text="Expected date and time of arrival")
    expected_departure = models.DateTimeField(null=True, blank=True, help_text="Expected date and time of departure")
    home_town = models.CharField(max_length=200, blank=True, help_text="Home town of the unit")
    
    # Boat estimates
    boats_p550 = models.PositiveIntegerField(default=0, help_text="Estimated number of P550 boats")
    boats_sail = models.PositiveIntegerField(default=0, help_text="Estimated number of other sail-boats")
    boats_paddle = models.PositiveIntegerField(default=0, help_text="Estimated number of paddle-powered boats")
    boats_motor = models.PositiveIntegerField(default=0, help_text="Estimated number of motor-powered boats")
    
    # Accommodation fields
    accommodation_expectations = models.TextField(blank=True, help_text="Accommodation expectations")
    estimated_accommodation_area = models.CharField(max_length=100, blank=True, help_text="Estimated needed area for accommodation")
    wishes_notes = models.TextField(blank=True, help_text="Wishes, notes, etc.")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.unit_name} ({self.unit_evidence_id})"

    class Meta:
        ordering = ['unit_name']


class Participant(models.Model):
    """
    Model representing a Participant in the system.
    """
    class ScoutCategory(models.TextChoices):
        ADULT = 'ADULT', 'Adult'
        ROVER = 'ROVER', 'Rover'
        SCOUT = 'SCOUT', 'Scout'
        CUB = 'CUB', 'Cub'
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True, help_text="Optional nickname")
    date_of_birth = models.DateField(help_text="Date of birth")
    category = models.CharField(
        max_length=20,
        choices=ScoutCategory.choices,
        default=ScoutCategory.SCOUT,
        help_text="Scout category"
    )
    health_restrictions = models.TextField(blank=True, help_text="Any health restrictions or medical conditions")
    dietary_restrictions = models.TextField(blank=True, help_text="Any dietary restrictions or preferences")
    relevant_information = models.TextField(blank=True, help_text="Any relevant information about the participant")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='participants')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.nickname:
            return f"{self.first_name} '{self.nickname}' {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']
