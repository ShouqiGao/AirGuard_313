import unittest

from services.subscription_service import validate_subscription_payload


class ValidateSubscriptionPayloadTest(unittest.TestCase):
    def setUp(self):
        self.valid_cities = ["Kuala Lumpur", "Johor Bahru"]

    def test_valid_payload(self):
        payload = {
            "username": "Ali",
            "email": "ali@example.com",
            "city": "kuala lumpur",
            "alert_time": "08:30",
        }
        validated, error = validate_subscription_payload(payload, self.valid_cities)
        self.assertIsNone(error)
        self.assertEqual(validated["city"], "Kuala Lumpur")

    def test_invalid_email(self):
        payload = {
            "username": "Ali",
            "email": "bad-email",
            "city": "Kuala Lumpur",
            "alert_time": "08:30",
        }
        _, error = validate_subscription_payload(payload, self.valid_cities)
        self.assertEqual(error, "Please provide a valid email address")

    def test_invalid_city(self):
        payload = {
            "username": "Ali",
            "email": "ali@example.com",
            "city": "Ipoh",
            "alert_time": "08:30",
        }
        _, error = validate_subscription_payload(payload, self.valid_cities)
        self.assertEqual(error, "Please select a valid city")


if __name__ == "__main__":
    unittest.main()
