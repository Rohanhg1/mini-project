from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

class TeacherTimetablePDFTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user('testuser', 'test@example.com', 'password')
        self.client.login(username='testuser', password='password')

    def test_download_teacher_timetable_pdf(self):
        # Set session data as if timetable was generated
        session = self.client.session
        session['total_teachers'] = 1
        session['timetables'] = {
            1: {
                'Mon': ['Math Integrated - Lab', 'Math Integrated', None, 'Math Integrated', 'Math Integrated', None, 'Math Integrated', 'Math Integrated', 'Math Integrated'],
                'Tue': [None, None, None, None, None, None, None, None, None],
                'Wed': [None, None, None, None, None, None, None, None, None],
                'Thu': [None, None, None, None, None, None, None, None, None],
                'Fri': [None, None, None, None, None, None, None, None, None],
            }
        }
        session['teacher_subjects'] = {'Test Teacher': ['Math Integrated']}
        session.save()

        # Test the PDF download
        response = self.client.get(reverse('download_teacher_timetable_pdf', kwargs={'teacher_name': 'Test Teacher'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('Test_Teacher_timetable.pdf', response['Content-Disposition'])

    def test_download_teacher_timetable_pdf_invalid_teacher(self):
        # Set session data
        session = self.client.session
        session['timetables'] = {}
        session['teacher_subjects'] = {}
        session.save()

        # Test with invalid teacher name
        response = self.client.get(reverse('download_teacher_timetable_pdf', kwargs={'teacher_name': 'Invalid Teacher'}))
        self.assertEqual(response.status_code, 302)  # Redirect to timetable_teachers

    def test_download_teacher_timetable_pdf_no_session(self):
        # No session data
        response = self.client.get(reverse('download_teacher_timetable_pdf', kwargs={'teacher_name': 'Test Teacher'}))
        self.assertEqual(response.status_code, 302)  # Redirect to timetable_teachers
