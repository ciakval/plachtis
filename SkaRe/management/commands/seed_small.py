"""
Seed database with a small amount of test data (up to 10 participants).

Usage: python manage.py seed_small
"""
from django.core.management.base import BaseCommand
from ._seeder import (
    get_or_create_test_user, create_unit, create_individual_participant, create_organizer
)


class Command(BaseCommand):
    help = 'Seed database with small test data (up to 10 participants)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before seeding',
        )

    def handle(self, *args, **options):
        from SkaRe.models import Entity, Unit, RegularParticipant, IndividualParticipant, Organizer
        
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            RegularParticipant.objects.all().delete()
            IndividualParticipant.objects.all().delete()
            Organizer.objects.all().delete()
            Unit.objects.all().delete()
            Entity.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Cleared all existing data.'))
        
        self.stdout.write('Creating small test dataset...')
        
        user = get_or_create_test_user('testuser_small')
        
        # Create 1 unit with 5 participants
        unit = create_unit(user, "1. oddíl Testovací", num_participants=5)
        self.stdout.write(f'  Created unit: {unit.entity.scout_unit_name} with 5 participants')
        
        # Create 2 individual participants
        for i in range(2):
            participant = create_individual_participant(user)
            self.stdout.write(f'  Created individual: {participant}')
        
        # Create 2 organizers
        for i in range(2):
            organizer = create_organizer(user)
            self.stdout.write(f'  Created organizer: {organizer}')
        
        total = 5 + 2 + 2  # unit participants + individual + organizers
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {total} participants:'))
        self.stdout.write(f'  - 1 unit with 5 regular participants')
        self.stdout.write(f'  - 2 individual participants')
        self.stdout.write(f'  - 2 organizers')
        self.stdout.write(f'\nTest user: testuser_small (password: testpass123)')

