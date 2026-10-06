from database import get_db_connection


connection = get_db_connection()

cursor = connection.cursor()


cursor.execute(
    """
    UPDATE students
    SET status = 'Inactive'
    WHERE id = ?
    """,
    (1,)
)


connection.commit()

connection.close()


print("Student updated.")
