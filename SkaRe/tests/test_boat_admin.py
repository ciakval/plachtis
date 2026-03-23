import csv
import io
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from SkaRe.models import SailRegistryEntry, BoatClass


class SailRegistryCSVImportTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin', password='pw', email='admin@test.cz'
        )
        self.client.login(username='admin', password='pw')

    def _make_csv(self, rows):
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'sail_number', 'boat_name', 'class_name', 'subtype',
            'sail_area', 'harbor_number', 'harbor_name', 'contact_person',
        ])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        return output.getvalue().encode('utf-8')

    def _import_url(self):
        return reverse('admin:skare_sailregistryentry_import_csv')

    def test_import_creates_entries(self):
        csv_bytes = self._make_csv([
            {'sail_number': 'CZE 1', 'boat_name': 'Rychlík', 'class_name': 'Cadet',
             'subtype': '', 'sail_area': '7.5', 'harbor_number': '523',
             'harbor_name': 'Koráb', 'contact_person': 'Jan'},
        ])
        self.client.post(
            self._import_url(),
            {'csv_file': io.BytesIO(csv_bytes)},
        )
        self.assertEqual(SailRegistryEntry.objects.count(), 1)
        self.assertEqual(SailRegistryEntry.objects.first().boat_name, 'Rychlík')

    def test_import_replaces_existing_entries(self):
        SailRegistryEntry.objects.create(sail_number='OLD 1')
        csv_bytes = self._make_csv([
            {'sail_number': 'NEW 1', 'boat_name': '', 'class_name': '',
             'subtype': '', 'sail_area': '', 'harbor_number': '',
             'harbor_name': '', 'contact_person': ''},
        ])
        self.client.post(self._import_url(), {'csv_file': io.BytesIO(csv_bytes)})
        self.assertFalse(SailRegistryEntry.objects.filter(sail_number='OLD 1').exists())
        self.assertTrue(SailRegistryEntry.objects.filter(sail_number='NEW 1').exists())

    def test_empty_csv_clears_existing_data(self):
        SailRegistryEntry.objects.create(sail_number='KEEP ME')
        # CSV with only a header row — 0 data rows
        empty_csv = b'sail_number,boat_name,class_name,subtype,sail_area,harbor_number,harbor_name,contact_person\n'
        self.client.post(self._import_url(), {'csv_file': io.BytesIO(empty_csv)})
        self.assertEqual(SailRegistryEntry.objects.count(), 0)

    def test_get_shows_upload_form(self):
        response = self.client.get(self._import_url())
        self.assertEqual(response.status_code, 200)

    def test_non_admin_cannot_access(self):
        self.client.logout()
        regular = User.objects.create_user(username='regular', password='pw')
        self.client.login(username='regular', password='pw')
        response = self.client.get(self._import_url())
        self.assertNotEqual(response.status_code, 200)
