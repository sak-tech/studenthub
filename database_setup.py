from database import get_db_connection

def setup_database():
    connection = get_db_connection()
    cursor = connection.cursor()

    # --------------------------------------------------
    # DROP OLD TABLES FOR CLEAN RE-CREATION IF NEEDED
    # --------------------------------------------------
    cursor.execute("DROP TABLE IF EXISTS grades")
    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS students")
    cursor.execute("DROP TABLE IF EXISTS courses")

    # --------------------------------------------------
    # CREATE COURSES TABLE
    # --------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        code TEXT UNIQUE NOT NULL,
        description TEXT,
        credits INTEGER DEFAULT 3,
        tuition_fee REAL DEFAULT 0.0
    )
    """)

    # --------------------------------------------------
    # CREATE STUDENTS TABLE
    # --------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        phone TEXT,
        gender TEXT,
        course_id INTEGER NOT NULL,
        date_of_birth TEXT,
        enrollment_date TEXT DEFAULT CURRENT_DATE,
        status TEXT NOT NULL DEFAULT 'Active',
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE
    )
    """)

    # --------------------------------------------------
    # CREATE ATTENDANCE TABLE
    # --------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
        notes TEXT,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # --------------------------------------------------
    # CREATE GRADES TABLE
    # --------------------------------------------------
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        subject TEXT NOT NULL,
        score REAL NOT NULL,
        max_score REAL DEFAULT 100.0,
        grade TEXT,
        term TEXT DEFAULT 'Fall 2025',
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
    )
    """)

    # --------------------------------------------------
    # SEED COURSES
    # --------------------------------------------------
    courses = [
        ("BCA", "BCA-101", "Bachelor of Computer Applications - Focus on software dev, web, and databases.", 4, 45000.0),
        ("BSc IT", "BIT-102", "Bachelor of Science in Information Technology - System admin, networking, and IT infrastructure.", 4, 42000.0),
        ("MCA", "MCA-201", "Master of Computer Applications - Advanced algorithms, cloud computing, and AI systems.", 4, 65000.0),
        ("BTech Computer Science", "BTC-103", "Bachelor of Technology in CS - Data structures, computer architecture, and ML.", 4, 85000.0),
        ("BBA", "BBA-104", "Bachelor of Business Administration - Marketing, management, and financial analysis.", 3, 40000.0),
        ("MCom", "MCM-202", "Master of Commerce - Accounting, global economics, and corporate taxation.", 3, 50000.0)
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO courses (name, code, description, credits, tuition_fee)
        VALUES (?, ?, ?, ?, ?)
    """, courses)

    # --------------------------------------------------
    # SEED STUDENTS
    # --------------------------------------------------
    students = [
        ("Rahul Sharma", "rahul@example.com", "9876543210", "Male", 1, "2002-04-12", "2025-06-15", "Active"),
        ("Ayesha Khan", "ayesha@example.com", "9123456789", "Female", 2, "2003-08-21", "2025-06-18", "Active"),
        ("Arjun Mehta", "arjun@example.com", "9988776655", "Male", 1, "2002-11-10", "2025-06-20", "Active"),
        ("Emily Davis", "emily@example.com", "9876501234", "Female", 4, "2001-05-14", "2025-06-22", "Inactive"),
        ("Chris Wilson", "chris@example.com", "9765432109", "Male", 3, "2002-01-25", "2025-06-25", "Active"),
        ("Sara Patel", "sara@example.com", "9898989898", "Female", 5, "2003-03-17", "2025-07-01", "Active"),
        ("Kabir Shah", "kabir@example.com", "9000011111", "Male", 2, "2002-09-09", "2025-07-03", "Inactive"),
        ("Maya Thomas", "maya@example.com", "9888877777", "Female", 6, "2001-12-04", "2025-07-05", "Active")
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO students (name, email, phone, gender, course_id, date_of_birth, enrollment_date, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, students)

    # --------------------------------------------------
    # SEED ATTENDANCE RECORDS
    # --------------------------------------------------
    attendance_records = [
        # Student 1 (Rahul)
        (1, "2025-10-01", "Present", "On time"),
        (1, "2025-10-02", "Present", "On time"),
        (1, "2025-10-03", "Present", "Active engagement"),
        (1, "2025-10-04", "Late", "10 mins delay"),
        (1, "2025-10-05", "Present", "On time"),
        # Student 2 (Ayesha)
        (2, "2025-10-01", "Present", "On time"),
        (2, "2025-10-02", "Present", "On time"),
        (2, "2025-10-03", "Present", "Submitted assignment"),
        (2, "2025-10-04", "Present", "On time"),
        (2, "2025-10-05", "Present", "On time"),
        # Student 3 (Arjun)
        (3, "2025-10-01", "Present", "On time"),
        (3, "2025-10-02", "Absent", "Medical leave"),
        (3, "2025-10-03", "Present", "On time"),
        (3, "2025-10-04", "Present", "On time"),
        # Student 4 (Emily)
        (4, "2025-10-01", "Absent", "Unexcused"),
        (4, "2025-10-02", "Absent", "Unexcused"),
        # Student 5 (Chris)
        (5, "2025-10-01", "Present", "On time"),
        (5, "2025-10-02", "Present", "On time"),
        (5, "2025-10-03", "Late", "Traffic delay"),
        # Student 6 (Sara)
        (6, "2025-10-01", "Present", "On time"),
        (6, "2025-10-02", "Present", "On time"),
        # Student 7 (Kabir)
        (7, "2025-10-01", "Absent", "Personal reasons"),
        # Student 8 (Maya)
        (8, "2025-10-01", "Present", "On time"),
        (8, "2025-10-02", "Present", "On time")
    ]

    cursor.executemany("""
        INSERT INTO attendance (student_id, date, status, notes)
        VALUES (?, ?, ?, ?)
    """, attendance_records)

    # --------------------------------------------------
    # SEED GRADES
    # --------------------------------------------------
    grades_records = [
        # Rahul
        (1, "Python Programming", 92.0, 100.0, "A+", "Fall 2025"),
        (1, "Database Systems", 88.0, 100.0, "A", "Fall 2025"),
        (1, "Web Architecture", 95.0, 100.0, "A+", "Fall 2025"),
        # Ayesha
        (2, "Computer Networks", 85.0, 100.0, "A", "Fall 2025"),
        (2, "Operating Systems", 90.0, 100.0, "A+", "Fall 2025"),
        (2, "Cybersecurity Basics", 87.0, 100.0, "A", "Fall 2025"),
        # Arjun
        (3, "Python Programming", 78.0, 100.0, "B+", "Fall 2025"),
        (3, "Database Systems", 82.0, 100.0, "A-", "Fall 2025"),
        # Emily
        (4, "Data Structures", 64.0, 100.0, "C", "Fall 2025"),
        (4, "Algorithms", 58.0, 100.0, "D", "Fall 2025"),
        # Chris
        (5, "Advanced AI", 94.0, 100.0, "A+", "Fall 2025"),
        (5, "Cloud Computing", 91.0, 100.0, "A", "Fall 2025"),
        # Sara
        (6, "Principles of Management", 89.0, 100.0, "A", "Fall 2025"),
        (6, "Business Marketing", 92.0, 100.0, "A+", "Fall 2025"),
        # Kabir
        (7, "Computer Networks", 70.0, 100.0, "B", "Fall 2025"),
        # Maya
        (8, "Corporate Accounting", 96.0, 100.0, "A+", "Fall 2025")
    ]

    cursor.executemany("""
        INSERT INTO grades (student_id, subject, score, max_score, grade, term)
        VALUES (?, ?, ?, ?, ?, ?)
    """, grades_records)

    connection.commit()
    connection.close()
    print("Database setup completed successfully with expanded schema and seed data.")

if __name__ == "__main__":
    setup_database()
