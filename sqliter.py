import sqlite3


class SQLighter:

    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()

    def get_users(self):
        """Get all users from 'users' table"""
        with self.connection:
            return self.cursor.execute("SELECT * FROM 'users'").fetchall()

    def get_user(self, user_id):
        """
        Returns user from 'users' table if exists
        :param user_id:
        :return: tuple with user data if user exists else returns empty tuple ()
        """
        with self.connection:
            return self.cursor.execute("SELECT * FROM 'users' WHERE id = ?", (user_id,)).fetchone()

    def user_exists(self, user_id):
        """
        Checks if user exists in 'users' table
        :returns True if exists else False
        """
        with self.connection:
            result = self.cursor.execute("SELECT * FROM 'users' WHERE id = ?", (user_id,)).fetchall()
            return bool(len(result))

    def add_user(self, user_id, name, joined_at):
        """Adds user to 'users' table or updates if user already exists"""
        with self.connection:
            if self.user_exists(user_id):
                return self.cursor.execute("UPDATE 'users' SET name = ? WHERE id = ?", (name, user_id))

            return self.cursor.execute("INSERT INTO 'users' ('id', 'name', 'joined_at') VALUES (?, ?, ?)",
                                       (user_id, name, joined_at))

    def add_test(self, subject, answers, author_id, tests_number):
        """Adds new test to 'tests' table"""
        with self.connection:
            self.cursor.execute(
                "INSERT INTO 'tests' ('subject', 'answers', 'author_id', 'tests_number') VALUES (?, ?, ?, ?)",
                (subject, answers, author_id, tests_number))
            return self.cursor.lastrowid

    def get_tests(self):
        """:returns all tests from 'tests' table"""
        with self.connection:
            return self.cursor.execute("SELECT * FROM 'tests'").fetchall()

    def get_test(self, test_id):
        with self.connection:
            return self.cursor.execute("SELECT * FROM 'tests' WHERE id = ?", (test_id,)).fetchone()

    def user_passed_test(self, user_id, test_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM 'tests_results' WHERE student_id = ? AND test_id = ?",
                                         (user_id, test_id)).fetchall()
            return bool(len(result))

    def add_test_result(self, test_id, user_id, answers, correct_answers):
        sql = "INSERT INTO 'tests_results' ('test_id', 'student_id', 'answers', 'correct_answers') VALUES (?, ?, ?, ?)"
        with self.connection:
            return self.cursor.execute(sql, (test_id, user_id, answers, correct_answers))

    def get_test_results(self, test_id):
        with self.connection:
            return self.cursor.execute(
                "SELECT name, correct_answers FROM 'tests_results' \
                 INNER JOIN 'users' ON tests_results.student_id = users.id \
                 WHERE test_id = ? ORDER BY correct_answers DESC",
                (test_id,)).fetchall()

    def get_students_passed_test(self, test_id):
        with self.connection:
            return self.cursor.execute("SELECT student_id FROM 'tests_results' WHERE test_id = ?",
                                       (test_id,)).fetchall()

    def finish_test(self, test_id):
        with self.connection:
            return self.cursor.execute("UPDATE 'tests' SET finished = 1 WHERE id = ?", (test_id,))

    def delete_user(self, user_id):
        with self.connection:
            return self.cursor.execute("DELETE FROM 'users' WHERE id = ?", (user_id,))

    def close(self):
        self.connection.close()


db = SQLighter('testing_bot')