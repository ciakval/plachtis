"""
Seed database with a large amount of test data (up to 1000 participants).

Usage: python manage.py seed_large
"""
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from ._seeder import (
    get_or_create_test_user, create_unit, create_individual_participant, 
    create_organizer, UNIT_NAMES
)


class Command(BaseCommand):
    help = 'Seed database with large test data (up to 1000 participants)'

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
        
        self.stdout.write('Creating large test dataset (this may take a moment)...')
        
        user = get_or_create_test_user('testuser_large')
        
        # Generate more unit names
        extended_unit_names = UNIT_NAMES.copy()
        for i in range(50):
            extended_unit_names.append(f"{i + 20}. oddíl Testovací {i + 1}")
        
        # Create 60 units with varying participants (approx 700 total)
        total_regular = 0
        with transaction.atomic():
            for i, name in enumerate(random.sample(extended_unit_names, 60)):
                num_participants = random.randint(8, 15)
                unit = create_unit(user, name, num_participants=num_participants)
                total_regular += num_participants
                if (i + 1) % 10 == 0:
                    self.stdout.write(f'  Created {i + 1} units ({total_regular} participants)...')
        
        self.stdout.write(f'  Created 60 units with {total_regular} regular participants')
        
        # Create 150 individual participants
        num_individual = 150
        with transaction.atomic():
            for i in range(num_individual):
                create_individual_participant(user)
                if (i + 1) % 25 == 0:
                    self.stdout.write(f'  Created {i + 1} individual participants...')
        self.stdout.write(f'  Created {num_individual} individual participants')
        
        # Create 100 organizers
        num_organizers = 100
        with transaction.atomic():
            for i in range(num_organizers):
                create_organizer(user)
                if (i + 1) % 20 == 0:
                    self.stdout.write(f'  Created {i + 1} organizers...')
        self.stdout.write(f'  Created {num_organizers} organizers')
        
        total = total_regular + num_individual + num_organizers
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {total} participants:'))
        self.stdout.write(f'  - 60 units with {total_regular} regular participants')
        self.stdout.write(f'  - {num_individual} individual participants')
        self.stdout.write(f'  - {num_organizers} organizers')
        self.stdout.write(f'\nTest user: testuser_large (password: testpass123)')

