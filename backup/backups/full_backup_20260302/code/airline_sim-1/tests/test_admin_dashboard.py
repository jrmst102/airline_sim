import unittest
from app.ui.admin_dashboard import app

class TestAdminDashboard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.app = app.test_client()
        cls.app.testing = True

    def test_admin_dashboard_load(self):
        response = self.app.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Admin Dashboard', response.data)

    def test_admin_controls(self):
        response = self.app.post('/admin/start_simulation')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Simulation started', response.data)

        response = self.app.post('/admin/end_simulation')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Simulation ended', response.data)

    def test_team_data_view(self):
        response = self.app.get('/admin/team_data')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Team Data', response.data)

    def test_unauthorized_access(self):
        response = self.app.get('/admin/dashboard', follow_redirects=True)
        self.assertEqual(response.status_code, 403)
        self.assertIn(b'Access denied', response.data)

if __name__ == '__main__':
    unittest.main()