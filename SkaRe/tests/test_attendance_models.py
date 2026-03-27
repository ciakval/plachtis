from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from SkaRe.models import RegularParticipant, Unit, Entity, AttendanceLog
from datetime import date


def _make_unit(user):
    entity = Entity.objects.create(
        created_by=user,
        contact_email='u@example.com',
        contact_phone='123456789',
    )
    return Unit.objects.create(entity=entity, contact_person_name='Leader')


def _make_person(unit):
    return RegularParticipant.objects.create(
        unit=unit,
        first_name='Jan',
        last_name='Novak',
        date_of_birth=date(2000, 1, 1),
    )


class PersonAttendanceFieldsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.unit = _make_unit(self.user)
        self.person = _make_person(self.unit)

    def test_attendance_status_defaults_to_expected(self):
        from SkaRe.models import Person
        self.assertEqual(self.person.attendance_status, Person.AttendanceStatus.EXPECTED)

    def test_arrived_at_is_null_by_default(self):
        self.assertIsNone(self.person.arrived_at)

    def test_departed_at_is_null_by_default(self):
        self.assertIsNone(self.person.departed_at)

    def test_attendance_status_can_be_set_to_arrived(self):
        from SkaRe.models import Person
        self.person.attendance_status = Person.AttendanceStatus.ARRIVED
        self.person.arrived_at = timezone.now()
        self.person.save()
        self.person.refresh_from_db()
        self.assertEqual(self.person.attendance_status, 'arrived')
        self.assertIsNotNone(self.person.arrived_at)


class AttendanceLogTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', password='pw')
        self.staff = User.objects.create_user(username='staff', password='pw')
        self.unit = _make_unit(self.user)
        self.person = _make_person(self.unit)

    def test_can_create_log_entry(self):
        from SkaRe.models import Person
        log = AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.ARRIVED,
            changed_by=self.staff,
        )
        self.assertEqual(log.status, 'arrived')
        self.assertEqual(log.person, self.person)

    def test_note_defaults_to_empty(self):
        from SkaRe.models import Person
        log = AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.EXPECTED,
            changed_by=None,
        )
        self.assertEqual(log.note, '')

    def test_changed_at_is_set_automatically(self):
        from SkaRe.models import Person
        log = AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.ARRIVED,
            changed_by=self.staff,
        )
        self.assertIsNotNone(log.changed_at)

    def test_person_has_attendance_logs_reverse_relation(self):
        from SkaRe.models import Person
        AttendanceLog.objects.create(
            person=self.person,
            status=Person.AttendanceStatus.ARRIVED,
            changed_by=self.staff,
        )
        self.assertEqual(self.person.attendance_logs.count(), 1)
