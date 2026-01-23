from django.db import models


# Create your models here.
class HelloWorld(models.Model):
    """A simple hello world model."""
    message = models.CharField(max_length=200, default='Hello, World!')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.message
    
    class Meta:
        verbose_name = 'Hello World Message'
        verbose_name_plural = 'Hello World Messages'

