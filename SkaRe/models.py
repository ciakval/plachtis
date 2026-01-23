from django.db import models


class Group(models.Model):
    """
    Model representing a Group in the system.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Participant(models.Model):
    """
    Model representing a Participant in the system.
    """
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    nickname = models.CharField(max_length=100, blank=True, help_text="Optional nickname")
    date_of_birth = models.DateField(help_text="Date of birth")
    health_restrictions = models.TextField(blank=True, help_text="Any health restrictions or medical conditions")
    dietary_restrictions = models.TextField(blank=True, help_text="Any dietary restrictions or preferences")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='participants')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.nickname:
            return f"{self.first_name} '{self.nickname}' {self.last_name}"
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['last_name', 'first_name']
