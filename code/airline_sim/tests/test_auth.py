import unittest
from app.utils.auth import verify_password
import csv

class TestAuth(unittest.TestCase):

    def setUp(self):
        self.credentials = self.load_credentials()

    def load_credentials(self):
        credentials = {}
        with open('app/data/passwords/usernames.csv', mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                credentials[row[0]] = row[1]
        return credentials

    def test_valid_admin_login(self):
        username = "Admin"
        password = self.credentials.get(username)
        self.assertTrue(verify_password(username, password))

    def test_invalid_admin_login(self):
        username = "Admin"
        invalid_password = "wrongpassword"
        self.assertFalse(verify_password(username, invalid_password))

    def test_nonexistent_user(self):
        username = "NonExistentUser"
        password = "anyPassword"
        self.assertFalse(verify_password(username, password))

if __name__ == '__main__':
    unittest.main()