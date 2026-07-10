import csv

DEGREE_SUBJECTS = {
    1: [("BSM101", "Mathematics-I"), ("CS101", "Programming Basics"), ("PHY101", "Physics"), ("EE101", "Basic Electrical"), ("ENG101", "English")],
    2: [("BSM301", "Mathematics-III"), ("CS201", "Data Structures"), ("CS202", "Digital Logic"), ("ME201", "Engineering Mechanics"), ("HS201", "Economics")],
    3: [("CS301", "OOP with Java"), ("CS302", "DBMS"), ("CS303", "Computer Networks"), ("BSM302", "Mathematics-IV"), ("CS304", "OS Basics")],
    4: [("CS401", "Algorithms"), ("CS402", "Software Engineering"), ("CS403", "Theory of Computation"), ("CS404", "Microprocessors"), ("CS405", "Web Development")],
}

GRADE_POINTS = {
    "O": 10.0, "E": 9.0, "A": 8.0, "B": 7.0, "C": 6.0, "F": 0.0
}

import random

rows = []

for i in range(1, 101):
    roll_no = f"12024{i:03d}"
    for semester in [1, 2, 3, 4]:
        for subject_code, subject_name in DEGREE_SUBJECTS[semester]:
            grade = random.choice(["O", "E", "A", "B", "C"])  # skew away from F for now
            points = GRADE_POINTS[grade]
            credits = 4.0
            credit_points = points * credits
            rows.append([roll_no, semester, subject_code, subject_name, grade, points, credits, credit_points])

with open("bulk_marks.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["roll_no", "semester", "subject_code", "subject_name", "grade", "points", "credits", "credit_points"])
    writer.writerows(rows)

print(f"Generated {len(rows)} mark rows into bulk_marks.csv")