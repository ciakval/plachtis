"""
Seed database with a moderate amount of test data (up to 100 participants).

Usage: python manage.py seed_medium
"""
import random
from django.core.management.base import BaseCommand
from ._seeder import (
    get_or_create_test_user, create_unit, create_individual_participant, 
    create_organizer, UNIT_NAMES
)


class Command(BaseCommand):
    help = 'Seed database with medium test data (up to 100 participants)'

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
        
        self.stdout.write('Creating medium test dataset...')
        
        user = get_or_create_test_user('testuser_medium')
        
        # Create 8 units with varying participants (approx 60 total)
        total_regular = 0
        unit_names = random.sample(UNIT_NAMES, 8)
        for name in unit_names:
            num_participants = random.randint(5, 12)
            unit = create_unit(user, name, num_participants=num_participants)
            total_regular += num_participants
            self.stdout.write(f'  Created unit: {unit.entity.scout_unit_name} with {num_participants} participants')
        
        # Create 15 individual participants
        num_individual = 15
        for i in range(num_individual):
            participant = create_individual_participant(user)
            if i % 5 == 0:
                self.stdout.write(f'  Created {i + 1} individual participants...')
        self.stdout.write(f'  Created {num_individual} individual participants')
        
        # Create 20 organizers
        num_organizers = 20
        for i in range(num_organizers):
            organizer = create_organizer(user)
            if i % 5 == 0:
                self.stdout.write(f'  Created {i + 1} organizers...')
        self.stdout.write(f'  Created {num_organizers} organizers')
        
        total = total_regular + num_individual + num_organizers
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {total} participants:'))
        self.stdout.write(f'  - 8 units with {total_regular} regular participants')
        self.stdout.write(f'  - {num_individual} individual participants')
        self.stdout.write(f'  - {num_organizers} organizers')
        self.stdout.write(f'\nTest user: testuser_medium (password: testpass123)')

