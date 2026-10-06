import unittest
from app import app

class TestStudentHub(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_dashboard_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"StudentHub Intelligence", response.data)

    def test_api_analytics(self):
        response = self.client.get('/api/analytics')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('courses', json_data)
        self.assertIn('status', json_data)

    def test_ai_chat_api(self):
        response = self.client.post('/api/ai/chat', json={"message": "Show total students"})
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('reply', json_data)
        self.assertIn('StudentHub Overview', json_data['reply'])

    def test_ai_student_insight(self):
        response = self.client.post('/api/ai/student-insight/1')
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertIn('report', json_data)

    def test_courses_route(self):
        response = self.client.get('/courses')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Academic Programs & Courses", response.data)

    def test_attendance_route(self):
        response = self.client.get('/attendance')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Attendance Records", response.data)

    def test_grades_route(self):
        response = self.client.get('/grades')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Student Gradebook & Performance", response.data)

    def test_csv_export(self):
        response = self.client.get('/students/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'text/csv')

if __name__ == '__main__':
    unittest.main()
