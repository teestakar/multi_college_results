import requests

BASE_URL = "http://localhost:8000/api/auth/register"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiVklUX0FETUlOIiwidXNlcl90eXBlIjoiYWRtaW4iLCJjb2xsZWdlX2lkIjoiOGIwYjBiMzctNjFiNS00OWRiLThkMWQtYzNhNTc5OTQ1MjFjIiwiZXhwIjoxNzg1OTYwOTI3LCJ0eXBlIjoiYWNjZXNzIn0.cU7RgX8BxBzGUaaJlXHUuyKutJrTUgwc2ePBdoBwDkg"

headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

DEGREE = "B.Tech"
BRANCH = "CSE"
EMAIL = "teestakar447@gmail.com"
PASSWORD = "password123"
YEAR = 2024

NUM_STUDENTS = 100

for i in range(1, NUM_STUDENTS + 1):
    roll_no = f"12024{i:03d}"
    payload = {
        "roll_no": roll_no,
        "email": EMAIL,
        "password": PASSWORD,
        "name": f"Test Student {i}",
        "degree": DEGREE,
        "branch": BRANCH,
        "year": YEAR
    }
    r = requests.post(BASE_URL, json=payload, headers=headers)
    print(roll_no, r.status_code, r.json().get("message") or r.json().get("detail"))