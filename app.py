import csv
import io
import json
import re
from datetime import datetime
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    Response
)

from database import get_db_connection

app = Flask(__name__)
app.secret_key = "studenthub-secret-key"


# ==================================================
# DASHBOARD & ANALYTICS
# ==================================================

@app.route("/")
def dashboard():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Total students
    cursor.execute("SELECT COUNT(*) AS total_students FROM students")
    total_students = cursor.fetchone()["total_students"]

    # Active students
    cursor.execute("SELECT COUNT(*) AS active_students FROM students WHERE status = 'Active'")
    active_students = cursor.fetchone()["active_students"]

    # Inactive students
    cursor.execute("SELECT COUNT(*) AS inactive_students FROM students WHERE status = 'Inactive'")
    inactive_students = cursor.fetchone()["inactive_students"]

    # Total courses
    cursor.execute("SELECT COUNT(*) AS total_courses FROM courses")
    total_courses = cursor.fetchone()["total_courses"]

    # Overall Avg Score
    cursor.execute("SELECT AVG(score) AS avg_score FROM grades")
    avg_score_row = cursor.fetchone()["avg_score"]
    avg_score = round(avg_score_row, 1) if avg_score_row is not None else 0.0

    # Overall Attendance Rate
    cursor.execute("SELECT COUNT(*) AS total_att, SUM(CASE WHEN status = 'Present' THEN 1 ELSE 0 END) AS present_count FROM attendance")
    att_row = cursor.fetchone()
    if att_row and att_row["total_att"] > 0:
        att_rate = round((att_row["present_count"] / att_row["total_att"]) * 100, 1)
    else:
        att_rate = 100.0

    # Recent students
    cursor.execute("""
        SELECT
            students.id,
            students.name,
            courses.name AS course,
            students.status
        FROM students
        INNER JOIN courses ON students.course_id = courses.id
        ORDER BY students.id DESC
        LIMIT 5
    """)
    recent_students = cursor.fetchall()

    # Course-wise statistics
    cursor.execute("""
        SELECT
            courses.name AS course,
            COUNT(students.id) AS total
        FROM courses
        LEFT JOIN students ON courses.id = students.course_id
        GROUP BY courses.id, courses.name
        ORDER BY total DESC
    """)
    course_stats = cursor.fetchall()

    connection.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        active_students=active_students,
        inactive_students=inactive_students,
        total_courses=total_courses,
        avg_score=avg_score,
        att_rate=att_rate,
        recent_students=recent_students,
        course_stats=course_stats
    )


@app.route("/api/analytics")
def api_analytics():
    """Returns JSON analytics data for Chart.js dashboards."""
    connection = get_db_connection()
    cursor = connection.cursor()

    # Course distribution
    cursor.execute("""
        SELECT courses.name AS label, COUNT(students.id) AS count
        FROM courses
        LEFT JOIN students ON courses.id = students.course_id
        GROUP BY courses.id, courses.name
    """)
    course_dist = cursor.fetchall()

    # Status breakdown
    cursor.execute("""
        SELECT status AS label, COUNT(*) AS count
        FROM students
        GROUP BY status
    """)
    status_dist = cursor.fetchall()

    # Grades distribution
    cursor.execute("""
        SELECT subject, ROUND(AVG(score), 1) AS avg_score
        FROM grades
        GROUP BY subject
        LIMIT 6
    """)
    grade_dist = cursor.fetchall()

    # Attendance distribution
    cursor.execute("""
        SELECT status AS label, COUNT(*) AS count
        FROM attendance
        GROUP BY status
    """)
    att_dist = cursor.fetchall()

    connection.close()

    return jsonify({
        "courses": {"labels": [row["label"] for row in course_dist], "data": [row["count"] for row in course_dist]},
        "status": {"labels": [row["label"] for row in status_dist], "data": [row["count"] for row in status_dist]},
        "grades": {"labels": [row["subject"] for row in grade_dist], "data": [row["avg_score"] for row in grade_dist]},
        "attendance": {"labels": [row["label"] for row in att_dist], "data": [row["count"] for row in att_dist]}
    })


# ==================================================
# AI AGENT ("HUBBOT")
# ==================================================

@app.route("/ai-assistant")
def ai_assistant():
    return render_template("ai_assistant.html")


@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    """Smart AI assistant endpoint with database query execution and heuristic LLM logic."""
    data = request.get_json() or {}
    user_query = data.get("message", "").strip()

    if not user_query:
        return jsonify({"reply": "Please type a message or select a suggested prompt."})

    connection = get_db_connection()
    cursor = connection.cursor()

    query_lower = user_query.lower()
    reply = ""
    suggested_actions = []

    try:
        # Query 1: Total or Active/Inactive counts
        if "total student" in query_lower or "how many student" in query_lower or "student count" in query_lower:
            cursor.execute("SELECT COUNT(*) AS total FROM students")
            total = cursor.fetchone()["total"]
            cursor.execute("SELECT COUNT(*) AS active FROM students WHERE status='Active'")
            active = cursor.fetchone()["active"]
            cursor.execute("SELECT COUNT(*) AS inactive FROM students WHERE status='Inactive'")
            inactive = cursor.fetchone()["inactive"]
            reply = f"📊 **StudentHub Overview**:\n\n- **Total Enrolled Students**: `{total}`\n- **Active Students**: `{active}` ({(active/total*100):.1f}%)\n- **Inactive Students**: `{inactive}`\n\nWould you like me to show all inactive students or generate a risk report?"
            suggested_actions = ["List inactive students", "Show risk analysis", "Course breakdown"]

        # Query 2: Inactive students / Risk analysis
        elif "inactive" in query_lower or "at risk" in query_lower or "risk" in query_lower or "need help" in query_lower:
            cursor.execute("""
                SELECT students.id, students.name, students.email, courses.name AS course
                FROM students
                JOIN courses ON students.course_id = courses.id
                WHERE students.status = 'Inactive'
            """)
            inactives = cursor.fetchall()
            if inactives:
                reply = f"⚠️ **Found {len(inactives)} Inactive / At-Risk Student(s)**:\n\n"
                for s in inactives:
                    reply += f"- **{s['name']}** (ID: `{s['id']}`) | Course: *{s['course']}* | Email: `{s['email']}`\n"
                reply += "\n💡 **Recommendation**: Reach out via email or schedule an academic review session."
            else:
                reply = "🎉 Great news! There are currently **0 inactive students**. Everyone is active in their respective programs!"
            suggested_actions = ["Show active students", "Generate email draft", "View course stats"]

        # Query 3: Search student by name or email
        elif "find" in query_lower or "search" in query_lower or "who is" in query_lower or "tell me about" in query_lower:
            search_term = re.sub(r'(find|search|who is|tell me about|student|information|for)', '', query_lower).strip()
            if not search_term:
                search_term = query_lower

            cursor.execute("""
                SELECT students.*, courses.name AS course_name
                FROM students
                JOIN courses ON students.course_id = courses.id
                WHERE students.name LIKE ? OR students.email LIKE ? OR students.id = ?
            """, (f"%{search_term}%", f"%{search_term}%", search_term if search_term.isdigit() else -1))
            matches = cursor.fetchall()

            if matches:
                reply = f"🔎 **Found {len(matches)} matching student(s)**:\n\n"
                for m in matches:
                    reply += f"👤 **{m['name']}** (ID: `{m['id']}`)\n"
                    reply += f"  - 📚 Course: {m['course_name']}\n"
                    reply += f"  - ✉️ Email: `{m['email']}` | 📞 Phone: {m['phone'] or 'N/A'}\n"
                    reply += f"  - 📌 Status: **{m['status']}** | DOB: {m['date_of_birth'] or 'N/A'}\n\n"
            else:
                reply = f"🔍 No student found matching '**{search_term}**'. Try searching by partial name, student ID, or email address."

        # Query 4: Course breakdown / list courses
        elif "course" in query_lower or "program" in query_lower or "bca" in query_lower or "mca" in query_lower or "btech" in query_lower:
            cursor.execute("""
                SELECT courses.name, courses.code, courses.credits, courses.tuition_fee, COUNT(students.id) AS student_count
                FROM courses
                LEFT JOIN students ON courses.id = students.course_id
                GROUP BY courses.id
            """)
            c_list = cursor.fetchall()
            reply = "📚 **Course Directory & Enrollment Statistics**:\n\n"
            for c in c_list:
                reply += f"- **{c['name']}** (`{c['code']}`)\n  - Enrolled: `{c['student_count']}` students | Credits: `{c['credits']}` | Tuition: ₹{c['tuition_fee']:,.2f}\n"
            suggested_actions = ["Add new course", "Show top students", "Export student data"]

        # Query 5: Grades / Top performers
        elif "top" in query_lower or "grade" in query_lower or "score" in query_lower or "performance" in query_lower:
            cursor.execute("""
                SELECT students.name, courses.name AS course, AVG(grades.score) AS avg_score
                FROM grades
                JOIN students ON grades.student_id = students.id
                JOIN courses ON students.course_id = courses.id
                GROUP BY students.id
                ORDER BY avg_score DESC
                LIMIT 5
            """)
            top = cursor.fetchall()
            if top:
                reply = "🏆 **Top Performing Students (by GPA/Average Score)**:\n\n"
                for i, t in enumerate(top, 1):
                    reply += f"{i}. **{t['name']}** ({t['course']}) — `{t['avg_score']:.1f}%` Avg\n"
            else:
                reply = "No grade records found in database yet. Add grades in the Gradebook module."

        # Query 6: Add student natural language action
        elif "add student" in query_lower or "create student" in query_lower:
            reply = "➕ You can add a new student using the **[Add Student](/student/add)** form or tell me their details like: `Add student Rohan, rohan@example.com, BCA`."

        # Fallback / General Assistant response
        else:
            cursor.execute("SELECT COUNT(*) AS total FROM students")
            total = cursor.fetchone()["total"]
            reply = f"🤖 **HubBot AI Assistant**: I am here to help you manage StudentHub!\n\nI can help you with:\n- 📊 **Stats & Risk Analysis**: 'Show inactive students' or 'Risk report'\n- 👤 **Student Lookup**: 'Find student Rahul' or 'Who is Ayesha?'\n- 📚 **Academic Insights**: 'List courses' or 'Top performing students'\n- 📈 **System Overview**: Currently managing **{total}** students across multiple programs.\n\nHow can I assist you right now?"
            suggested_actions = ["Show total students", "List courses", "Top performers", "Show inactive students"]

    except Exception as e:
        reply = f"⚠️ HubBot encountered an internal query error: `{str(e)}`"
    finally:
        connection.close()

    return jsonify({
        "reply": reply,
        "suggested_actions": suggested_actions,
        "timestamp": datetime.now().strftime("%I:%M %p")
    })


@app.route("/api/ai/student-insight/<int:student_id>", methods=["POST"])
def ai_student_insight(student_id):
    """Generates an AI analytical profile report for a specific student."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT students.*, courses.name AS course_name, courses.code AS course_code
        FROM students
        JOIN courses ON students.course_id = courses.id
        WHERE students.id = ?
    """, (student_id,))
    student = cursor.fetchone()

    if not student:
        connection.close()
        return jsonify({"error": "Student not found"}), 404

    # Fetch grades
    cursor.execute("SELECT subject, score, grade FROM grades WHERE student_id = ?", (student_id,))
    grades = cursor.fetchall()

    # Fetch attendance
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present,
            SUM(CASE WHEN status='Absent' THEN 1 ELSE 0 END) AS absent,
            SUM(CASE WHEN status='Late' THEN 1 ELSE 0 END) AS late
        FROM attendance WHERE student_id = ?
    """, (student_id,))
    att = cursor.fetchone()

    connection.close()

    total_att = att["total"] or 0
    present_att = att["present"] or 0
    att_rate = round((present_att / total_att * 100), 1) if total_att > 0 else 100.0

    scores = [g["score"] for g in grades]
    avg_score = round(sum(scores)/len(scores), 1) if scores else 0.0

    # Risk level determination
    if student["status"] == "Inactive" or att_rate < 75 or (scores and avg_score < 70):
        risk = "HIGH RISK / ATTENTION NEEDED"
        recommendations = "Schedule 1-on-1 counseling, send attendance reminder to parents, and offer tutoring support."
    elif avg_score >= 85 and att_rate >= 90:
        risk = "EXCELLENT PERFORMANCE"
        recommendations = "Recommend for honor roll recognition and advanced project leadership roles."
    else:
        risk = "STABLE / SATISFACTORY"
        recommendations = "Maintain current momentum and monitor upcoming mid-term exams."

    report = f"""### 🤖 HubBot AI Performance Insights for **{student['name']}**

- **Program**: {student['course_name']} (`{student['course_code']}`)
- **Account Status**: `{student['status']}`
- **Academic Score Avg**: `{avg_score}%` ({len(grades)} subjects recorded)
- **Attendance Rate**: `{att_rate}%` ({present_att}/{total_att} sessions present)
- **AI Risk Status**: **{risk}**

#### 📋 Subject Breakdown:
"""
    if grades:
        for g in grades:
            report += f"- **{g['subject']}**: `{g['score']}%` (Grade: `{g['grade']}`)\n"
    else:
        report += "- *No subject grades recorded yet.*\n"

    report += f"\n💡 **AI Recommended Action**: {recommendations}"

    return jsonify({"report": report, "student_id": student_id, "name": student["name"]})


# ==================================================
# STUDENT MANAGEMENT
# ==================================================

@app.route("/students")
def students():
    search = request.args.get("search", "").strip()
    course_id = request.args.get("course_id", "")
    status = request.args.get("status", "")

    connection = get_db_connection()
    cursor = connection.cursor()

    query = """
        SELECT
            students.id,
            students.name,
            students.email,
            students.phone,
            students.gender,
            students.status,
            courses.name AS course
        FROM students
        INNER JOIN courses ON students.course_id = courses.id
        WHERE 1 = 1
    """
    parameters = []

    if search:
        query += " AND (students.name LIKE ? OR students.email LIKE ? OR students.phone LIKE ?)"
        search_val = f"%{search}%"
        parameters.extend([search_val, search_val, search_val])

    if course_id:
        query += " AND students.course_id = ?"
        parameters.append(course_id)

    if status:
        query += " AND students.status = ?"
        parameters.append(status)

    query += " ORDER BY students.id DESC"
    cursor.execute(query, parameters)
    students_list = cursor.fetchall()

    cursor.execute("SELECT id, name FROM courses ORDER BY name")
    courses = cursor.fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=students_list,
        courses=courses,
        search=search,
        selected_course=course_id,
        selected_status=status
    )


@app.route("/student/add", methods=["GET", "POST"])
def add_student():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, name FROM courses ORDER BY name")
    courses = cursor.fetchall()

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        gender = request.form["gender"]
        course_id = request.form["course_id"]
        date_of_birth = request.form["date_of_birth"]
        status = request.form["status"]

        if not name or not email or not course_id:
            connection.close()
            flash("Name, email, and course are required.", "error")
            return redirect(url_for("add_student"))

        try:
            cursor.execute("""
                INSERT INTO students (name, email, phone, gender, course_id, date_of_birth, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, email, phone, gender, course_id, date_of_birth, status))
            connection.commit()
            flash("Student added successfully.", "success")
        except Exception as e:
            flash(f"Error adding student: {str(e)}", "error")
        finally:
            connection.close()

        return redirect(url_for("students"))

    connection.close()
    return render_template("student_form.html", student=None, courses=courses, form_title="Add Student")


@app.route("/student/<int:student_id>")
def student_detail(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.id,
            students.name,
            students.email,
            students.phone,
            students.gender,
            students.date_of_birth,
            students.enrollment_date,
            students.status,
            courses.name AS course,
            courses.code AS course_code
        FROM students
        INNER JOIN courses ON students.course_id = courses.id
        WHERE students.id = ?
    """, (student_id,))
    student = cursor.fetchone()

    if student is None:
        connection.close()
        flash("Student not found.", "error")
        return redirect(url_for("students"))

    # Fetch student's grades
    cursor.execute("SELECT * FROM grades WHERE student_id = ? ORDER BY id DESC", (student_id,))
    grades = cursor.fetchall()

    # Fetch student's attendance records
    cursor.execute("SELECT * FROM attendance WHERE student_id = ? ORDER BY date DESC LIMIT 10", (student_id,))
    attendance = cursor.fetchall()

    # Stats
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN status='Present' THEN 1 ELSE 0 END) AS present
        FROM attendance WHERE student_id = ?
    """, (student_id,))
    att_stats = cursor.fetchone()
    total_att = att_stats["total"] or 0
    present_att = att_stats["present"] or 0
    att_percentage = round((present_att / total_att * 100), 1) if total_att > 0 else 100.0

    scores = [g["score"] for g in grades]
    avg_score = round(sum(scores)/len(scores), 1) if scores else 0.0

    connection.close()

    return render_template(
        "student_detail.html",
        student=student,
        grades=grades,
        attendance=attendance,
        att_percentage=att_percentage,
        avg_score=avg_score
    )


@app.route("/student/edit/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT id, name FROM courses ORDER BY name")
    courses = cursor.fetchall()

    if student is None:
        connection.close()
        flash("Student not found.", "error")
        return redirect(url_for("students"))

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        phone = request.form["phone"].strip()
        gender = request.form["gender"]
        course_id = request.form["course_id"]
        date_of_birth = request.form["date_of_birth"]
        status = request.form["status"]

        cursor.execute("""
            UPDATE students
            SET name = ?, email = ?, phone = ?, gender = ?, course_id = ?, date_of_birth = ?, status = ?
            WHERE id = ?
        """, (name, email, phone, gender, course_id, date_of_birth, status, student_id))

        connection.commit()
        connection.close()
        flash("Student updated successfully.", "success")
        return redirect(url_for("student_detail", student_id=student_id))

    connection.close()
    return render_template("student_form.html", student=student, courses=courses, form_title="Edit Student")


@app.route("/student/delete/<int:student_id>", methods=["POST"])
def delete_student(student_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
    connection.commit()
    connection.close()

    flash("Student deleted successfully.", "success")
    return redirect(url_for("students"))


@app.route("/students/export")
def export_students():
    """Generates a downloadable CSV file of all student records."""
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            students.id,
            students.name,
            students.email,
            students.phone,
            students.gender,
            courses.name AS course,
            students.date_of_birth,
            students.enrollment_date,
            students.status
        FROM students
        JOIN courses ON students.course_id = courses.id
        ORDER BY students.id ASC
    """)
    rows = cursor.fetchall()
    connection.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Email", "Phone", "Gender", "Course", "Date of Birth", "Enrollment Date", "Status"])

    for row in rows:
        writer.writerow([
            row["id"],
            row["name"],
            row["email"],
            row["phone"],
            row["gender"],
            row["course"],
            row["date_of_birth"],
            row["enrollment_date"],
            row["status"]
        ])

    csv_data = output.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=studenthub_export.csv"}
    )


# ==================================================
# COURSE MANAGEMENT
# ==================================================

@app.route("/courses")
def courses():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            courses.*,
            COUNT(students.id) AS student_count
        FROM courses
        LEFT JOIN students ON courses.id = students.course_id
        GROUP BY courses.id
        ORDER BY courses.id ASC
    """)
    course_list = cursor.fetchall()
    connection.close()

    return render_template("courses.html", courses=course_list)


@app.route("/course/add", methods=["GET", "POST"])
def add_course():
    if request.method == "POST":
        name = request.form["name"].strip()
        code = request.form["code"].strip().upper()
        description = request.form["description"].strip()
        credits = request.form.get("credits", 3)
        tuition_fee = request.form.get("tuition_fee", 0.0)

        if not name or not code:
            flash("Course Name and Code are required.", "error")
            return redirect(url_for("add_course"))

        connection = get_db_connection()
        cursor = connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO courses (name, code, description, credits, tuition_fee)
                VALUES (?, ?, ?, ?, ?)
            """, (name, code, description, credits, tuition_fee))
            connection.commit()
            flash("Course added successfully.", "success")
        except Exception as e:
            flash(f"Error creating course: {str(e)}", "error")
        finally:
            connection.close()

        return redirect(url_for("courses"))

    return render_template("course_form.html", course=None, form_title="Add Course")


@app.route("/course/edit/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    course = cursor.fetchone()

    if not course:
        connection.close()
        flash("Course not found.", "error")
        return redirect(url_for("courses"))

    if request.method == "POST":
        name = request.form["name"].strip()
        code = request.form["code"].strip().upper()
        description = request.form["description"].strip()
        credits = request.form.get("credits", 3)
        tuition_fee = request.form.get("tuition_fee", 0.0)

        cursor.execute("""
            UPDATE courses
            SET name = ?, code = ?, description = ?, credits = ?, tuition_fee = ?
            WHERE id = ?
        """, (name, code, description, credits, tuition_fee, course_id))

        connection.commit()
        connection.close()
        flash("Course updated successfully.", "success")
        return redirect(url_for("courses"))

    connection.close()
    return render_template("course_form.html", course=course, form_title="Edit Course")


@app.route("/course/delete/<int:course_id>", methods=["POST"])
def delete_course(course_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        connection.commit()
        flash("Course deleted successfully.", "success")
    except Exception as e:
        flash(f"Cannot delete course: {str(e)}", "error")
    finally:
        connection.close()

    return redirect(url_for("courses"))


# ==================================================
# ATTENDANCE TRACKER
# ==================================================

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == "POST":
        student_id = request.form["student_id"]
        date = request.form.get("date", datetime.now().strftime("%Y-%m-%d"))
        status = request.form["status"]
        notes = request.form.get("notes", "").strip()

        cursor.execute("""
            INSERT INTO attendance (student_id, date, status, notes)
            VALUES (?, ?, ?, ?)
        """, (student_id, date, status, notes))

        connection.commit()
        flash("Attendance recorded successfully.", "success")
        return redirect(url_for("attendance"))

    # GET
    cursor.execute("""
        SELECT attendance.*, students.name AS student_name, courses.name AS course_name
        FROM attendance
        JOIN students ON attendance.student_id = students.id
        JOIN courses ON students.course_id = courses.id
        ORDER BY attendance.date DESC, attendance.id DESC
        LIMIT 50
    """)
    records = cursor.fetchall()

    cursor.execute("SELECT id, name FROM students ORDER BY name")
    all_students = cursor.fetchall()

    connection.close()
    return render_template("attendance.html", records=records, students=all_students)


@app.route("/attendance/delete/<int:attendance_id>", methods=["POST"])
def delete_attendance(attendance_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM attendance WHERE id = ?", (attendance_id,))
    connection.commit()
    connection.close()
    flash("Attendance record removed.", "success")
    return redirect(url_for("attendance"))


# ==================================================
# GRADEBOOK MODULE
# ==================================================

@app.route("/grades", methods=["GET", "POST"])
def grades():
    connection = get_db_connection()
    cursor = connection.cursor()

    if request.method == "POST":
        student_id = request.form["student_id"]
        subject = request.form["subject"].strip()
        score = float(request.form.get("score", 0))
        max_score = float(request.form.get("max_score", 100))
        term = request.form.get("term", "Fall 2025").strip()

        # Grade calculation
        pct = (score / max_score) * 100
        if pct >= 90:
            grade = "A+"
        elif pct >= 85:
            grade = "A"
        elif pct >= 80:
            grade = "A-"
        elif pct >= 75:
            grade = "B+"
        elif pct >= 70:
            grade = "B"
        elif pct >= 60:
            grade = "C"
        elif pct >= 50:
            grade = "D"
        else:
            grade = "F"

        cursor.execute("""
            INSERT INTO grades (student_id, subject, score, max_score, grade, term)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (student_id, subject, score, max_score, grade, term))

        connection.commit()
        flash("Grade entry saved.", "success")
        return redirect(url_for("grades"))

    # GET
    cursor.execute("""
        SELECT grades.*, students.name AS student_name, courses.name AS course_name
        FROM grades
        JOIN students ON grades.student_id = students.id
        JOIN courses ON students.course_id = courses.id
        ORDER BY grades.id DESC
    """)
    records = cursor.fetchall()

    cursor.execute("SELECT id, name FROM students ORDER BY name")
    all_students = cursor.fetchall()

    connection.close()
    return render_template("grades.html", records=records, students=all_students)


@app.route("/grades/delete/<int:grade_id>", methods=["POST"])
def delete_grade(grade_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
    connection.commit()
    connection.close()
    flash("Grade record deleted.", "success")
    return redirect(url_for("grades"))


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":
    app.run(debug=True)