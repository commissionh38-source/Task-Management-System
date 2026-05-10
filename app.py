from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ======================
# DATABASE SETUP
# ======================
def init_db():
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            priority TEXT,
            due_date TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')

    conn.commit()
    conn.close()

init_db()

# ======================
# HOME
# ======================
@app.route("/", methods=["GET", "POST"])
def home():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    # ======================
    # ADD TASK
    # ======================
    if request.method == "POST":
        task = request.form.get("task")
        priority = request.form.get("priority")
        due_date = request.form.get("due_date")

        if task:
            c.execute(
                "INSERT INTO tasks (name, done, priority, due_date) VALUES (?, 0, ?, ?)",
                (task, priority, due_date)
            )
            conn.commit()

    # ======================
    # SEARCH + FILTER + SORT
    # ======================
    search = request.args.get("search", "")
    filter_type = request.args.get("filter")
    sort = request.args.get("sort")

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if search:
        query += " AND name LIKE ?"
        params.append(f"%{search}%")

    if filter_type == "completed":
        query += " AND done = 1"
    elif filter_type == "pending":
        query += " AND done = 0"

    if sort == "date":
        query += " ORDER BY due_date ASC"
    elif sort == "priority":
        query += """
        ORDER BY 
        CASE priority
            WHEN 'High' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'Low' THEN 3
        END
        """
    else:
        query += " ORDER BY id DESC"

    c.execute(query, params)
    tasks = c.fetchall()

    # ======================
    # DASHBOARD COUNTS
    # ======================
    c.execute("SELECT COUNT(*) FROM tasks WHERE done = 0")
    pending_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE done = 1")
    completed_count = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks")
    total_count = c.fetchone()[0]

    # ======================
    # OVERDUE COUNT
    # ======================
    c.execute("""
        SELECT COUNT(*) FROM tasks 
        WHERE due_date IS NOT NULL 
        AND due_date < date('now') 
        AND done = 0
    """)
    overdue_count = c.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        tasks=tasks,
        now=datetime.now,
        pending_count=pending_count,
        completed_count=completed_count,
        total_count=total_count,
        overdue_count=overdue_count
    )

# ======================
# DELETE
# ======================
@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

# ======================
# COMPLETE
# ======================
@app.route("/complete/<int:id>")
def complete(id):
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    c.execute("UPDATE tasks SET done = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for("home"))

# ======================
# EDIT
# ======================
@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit(id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()

    if request.method == "POST":
        new_name = request.form.get("task")
        new_priority = request.form.get("priority")
        new_date = request.form.get("due_date")

        c.execute(
            "UPDATE tasks SET name=?, priority=?, due_date=? WHERE id=?",
            (new_name, new_priority, new_date, id)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    c.execute("SELECT * FROM tasks WHERE id=?", (id,))
    task = c.fetchone()
    conn.close()

    return render_template("edit.html", task=task)

# ======================
# REGISTER
# ======================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("tasks.db")
        c = conn.cursor()

        try:
            c.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "User already exists"

        conn.close()
        return redirect(url_for("login"))

    return render_template("register.html")

# ======================
# LOGIN
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect("tasks.db")
        c = conn.cursor()

        c.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = username
            return redirect(url_for("home"))
        else:
            return "Invalid login"

    return render_template("login.html")

# ======================
# LOGOUT
# ======================
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

# ======================
# RUN
# ======================
if __name__ == "__main__":
    app.run(debug=True)