from database import get_db_connection

connection = get_db_connection()
cursor = connection.cursor()

cursor.execute("""
SELECT
    students.id,
    students.name,
    students.email,
    courses.name AS course,
    students.status
FROM students
INNER JOIN courses
    ON students.course_id = courses.id
""")

students = cursor.fetchall()

for student in students:
    print(
        student["id"],
        student["name"],
        student["email"],
        student["course"],
        student["status"]
    )
cursor.execute("SELECT COUNT(*) AS total_students FROM students")
total_students = cursor.fetchone()["total_students"]
print(f"\nTotal Students: {total_students}")

cursor.execute("SELECT COUNT(*) AS active_students FROM students WHERE status = 'Active'")
active_students = cursor.fetchone()["active_students"]
print(f"\nActive Students: {active_students}")

cursor.execute("SELECT COUNT(*) AS inactive_students FROM students WHERE status = 'Inactive'")
inactive_students = cursor.fetchone()["inactive_students"]  
print(f"\nInactive Students: {inactive_students}")

cursor.execute("""SELECT COUNT(*) AS total_courses
FROM courses;
""")
total_courses = cursor.fetchone()["total_courses"]
print(f"\nTotal Courses: {total_courses}")

cursor.execute("""SELECT
    courses.name AS course,
    COUNT(students.id) AS total_students
FROM courses
LEFT JOIN students
    ON courses.id = students.course_id
GROUP BY courses.id, courses.name
ORDER BY total_students DESC;
""")
course_student_counts = cursor.fetchall()

for row in course_student_counts:
    print(f"{row['course']}: {row['total_students']} students")

connection.close()
