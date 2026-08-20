from locust import HttpUser, task, between
import random


COLLEGE_CODE = "VIT"
PASSWORD = "password123"

# Assuming your test data has students 12024001 to 12024100
ROLL_NUMBERS = [f"12024{i:03d}" for i in range(1, 101)]


class StudentUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.token = None

        roll_no = random.choice(ROLL_NUMBERS)

        response = self.client.post(
            "/api/auth/login",
            json={
                "college_code": COLLEGE_CODE,
                "roll_no": roll_no,
                "password": PASSWORD
            },
            name="Student Login"
        )

        if response.status_code == 200:
            try:
                self.token = response.json()["access_token"]
            except Exception:
                print(f"[LOGIN] Invalid JSON for {roll_no}")
                print(response.text)
        else:
            print(f"[LOGIN] {roll_no} -> {response.status_code}")
            print(response.text)

    @task
    def view_results(self):
        if not self.token:
            return

        semester = random.randint(1, 4)

        headers = {
            "Authorization": f"Bearer {self.token}"
        }

        with self.client.get(
            f"/api/results/me?semester={semester}&page=1",
            headers=headers,
            name="/api/results/me",
            catch_response=True,
        ) as response:

            if response.status_code == 200:
                response.success()

            else:
                response.failure(
                    f"Semester {semester} | "
                    f"Status {response.status_code} | "
                    f"{response.text}"
                )