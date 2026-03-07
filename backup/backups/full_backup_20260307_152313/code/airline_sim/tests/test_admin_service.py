import unittest
from app.services.admin_service import AdminService

class TestAdminService(unittest.TestCase):

    def setUp(self):
        self.admin_service = AdminService()

    def test_authenticate_admin_valid(self):
        result = self.admin_service.authenticate_admin("admin", "RoadRunner1")
        self.assertTrue(result)

    def test_authenticate_admin_invalid(self):
        result = self.admin_service.authenticate_admin("admin", "wrongpassword")
        self.assertFalse(result)

    def test_get_team_data(self):
        team_data = self.admin_service.get_team_data()
        self.assertIsInstance(team_data, list)  # Assuming team data is a list

    def test_start_simulation(self):
        result = self.admin_service.start_simulation()
        self.assertTrue(result)

    def test_end_simulation(self):
        result = self.admin_service.end_simulation()
        self.assertTrue(result)

    def test_undo_last_period(self):
        result = self.admin_service.undo_last_period()
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()