import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestApi(unittest.TestCase):
    def test_health_check(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_unauthenticated_session_create_rejected(self):
        response = client.post(
            "/api/v1/sessions",
            json={
                "session_id": "11111111-1111-1111-1111-111111111111",
                "started_at": "2026-10-14T10:00:00Z",
            },
        )
        self.assertIn(response.status_code, (401, 403))


if __name__ == "__main__":
    unittest.main()
