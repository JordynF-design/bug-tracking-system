import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)

app.secret_key = "bug-tracker-secret-key"

DATABASE = "bugs.db"



def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'Open',
            assigned_to TEXT
        )
    """)
    conn.commit()
    conn.close()


create_table()



@app.route("/")
def home():
    conn = get_db_connection()

    # Get all bugs for dashboard statistics
    all_bugs = conn.execute(
        "SELECT * FROM bugs ORDER BY id DESC"
    ).fetchall()

    # Get search and filter values
    search = request.args.get("search", "").strip()
    priority = request.args.get("priority", "").strip()
    status = request.args.get("status", "").strip()
    sort_by = request.args.get("sort_by", "").strip()

    # Build the filtered query
    query = "SELECT * FROM bugs WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE ? OR description LIKE ? OR assigned_to LIKE ?)"
        params.extend([f"%{search}%"] * 3)

    if priority:
        query += " AND priority = ?"
        params.append(priority)

    if status:
        query += " AND status = ?"
        params.append(status)

    # Available sorting options
    sort_options = {
        "id": "id DESC",
        "title": "title COLLATE NOCASE ASC",
        "priority": "CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 END",
        "status": "CASE status WHEN 'Open' THEN 1 WHEN 'In Progress' THEN 2 WHEN 'Resolved' THEN 3 END"
    }

    order_by = sort_options.get(sort_by, "id DESC")
    query += f" ORDER BY {order_by}"

    # Get filtered bugs
    bugs = conn.execute(query, params).fetchall()
    conn.close()

    # Dashboard statistics
    total_bugs = len(all_bugs)
    open_bugs = sum(1 for bug in all_bugs if bug["status"] == "Open")
    in_progress = sum(1 for bug in all_bugs if bug["status"] == "In Progress")
    resolved_bugs = sum(1 for bug in all_bugs if bug["status"] == "Resolved")

    return render_template(
        "index.html",
        bugs=bugs,
        total_bugs=total_bugs,
        open_bugs=open_bugs,
        in_progress=in_progress,
        resolved_bugs=resolved_bugs
    )


@app.route("/report", methods=["GET", "POST"])
def report_bug():
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        priority = request.form["priority"]
        assigned_to = request.form["assigned_to"]

        conn = get_db_connection()
        conn.execute(
            """INSERT INTO bugs
            (title, description, priority, assigned_to)
            VALUES (?, ?, ?, ?)""",
            (title, description, priority, assigned_to)
        )
        conn.commit()
        conn.close()

        flash("Bug reported successfully!", "success")

        return redirect(url_for("home"))

    return render_template("report_bug.html")


@app.route("/update_status", methods=["POST"])
def update_status():
    bug_id = request.form["bug_id"]
    new_status = request.form["status"]

    conn = get_db_connection()
    conn.execute(
        "UPDATE bugs SET status = ? WHERE id = ?",
        (new_status, bug_id)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))

@app.route("/delete_bug/<int:bug_id>", methods=["POST"])
def delete_bug(bug_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM bugs WHERE id = ?", (bug_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


@app.route("/edit_bug/<int:bug_id>", methods=["GET", "POST"])
def edit_bug(bug_id):
    conn = get_db_connection()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        priority = request.form["priority"]
        assigned_to = request.form["assigned_to"]

        conn.execute(
            """UPDATE bugs
               SET title = ?, description = ?, priority = ?, assigned_to = ?
               WHERE id = ?""",
            (title, description, priority, assigned_to, bug_id)
        )

        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    bug = conn.execute(
        "SELECT * FROM bugs WHERE id = ?", (bug_id,)
    ).fetchone()

    conn.close()
    return render_template("edit_bug.html", bug=bug)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
