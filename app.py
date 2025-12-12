from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "dev_secret_key"  # only for flash messages in dev
FILE = "tasks.json"

PRIORITY_ORDER = {"High": 0, "Medium": 1, "Low": 2}

# ---------------- Helper Functions ----------------
def load_tasks():
    if not os.path.exists(FILE):
        return []
    try:
        with open(FILE, "r") as f:
            return json.load(f)
    except:
        return []

def save_tasks(tasks):
    with open(FILE, "w") as f:
        json.dump(tasks, f, indent=4)

def parse_deadline(deadline_str):
    """Parse HTML datetime-local string like '2025-12-12T15:30' -> datetime, or None"""
    if not deadline_str:
        return None
    try:
        # fromisoformat supports 'YYYY-MM-DDTHH:MM' format
        return datetime.fromisoformat(deadline_str)
    except Exception:
        return None

def task_deadline_timestamp(task):
    if task.get("deadline"):
        try:
            return datetime.fromisoformat(task["deadline"]).timestamp()
        except:
            return float("inf")
    return float("inf")

def is_due_soon(task, hours=24):
    if task.get("deadline") and not task.get("completed"):
        try:
            dl = datetime.fromisoformat(task["deadline"])
            now = datetime.now()
            return now <= dl <= now + timedelta(hours=hours)
        except:
            return False
    return False

def sort_tasks(tasks):
    """Sort tasks by:
       1) not completed first (completed last)
       2) priority (High, Medium, Low)
       3) nearest deadline
    """
    def sort_key(t):
        completed = 1 if t.get("completed") else 0
        pr = PRIORITY_ORDER.get(t.get("priority", "Low"), 2)
        dl_ts = task_deadline_timestamp(t)
        return (completed, pr, dl_ts)
    return sorted(tasks, key=sort_key)

# ---------------- Routes ----------------

@app.route("/", methods=["GET", "POST"])
def index():
    tasks = load_tasks()

    if request.method == "POST":
        # Add new task
        task_text = request.form.get("task", "").strip()
        priority = request.form.get("priority", "Low")
        deadline_raw = request.form.get("deadline", "").strip()
        description = request.form.get("description", "").strip()

        if not task_text:
            flash("Task text is required.", "error")
            return redirect(url_for("index"))

        deadline_dt = parse_deadline(deadline_raw)
        deadline_iso = deadline_dt.isoformat() if deadline_dt else None

        new_task = {
            "task": task_text,
            "priority": priority,
            "deadline": deadline_iso,   # ISO string or None
            "description": description,
            "completed": False
        }
        tasks.append(new_task)
        save_tasks(tasks)
        flash("Task added.", "success")
        return redirect(url_for("index"))

    # GET - render tasks sorted and compute reminders
    tasks_sorted = sort_tasks(tasks)
    due_soon_list = [t for t in tasks_sorted if is_due_soon(t, hours=24)]
    return render_template("index.html", tasks=tasks_sorted, due_soon=due_soon_list)

@app.route("/delete/<int:task_id>")
def delete(task_id):
    tasks = load_tasks()
    if 0 <= task_id < len(tasks):
        tasks.pop(task_id)
        save_tasks(tasks)
        flash("Task deleted.", "success")
    else:
        flash("Invalid task ID.", "error")
    return redirect(url_for("index"))

@app.route("/toggle/<int:task_id>")
def toggle(task_id):
    tasks = load_tasks()
    if 0 <= task_id < len(tasks):
        tasks[task_id]["completed"] = not tasks[task_id].get("completed", False)
        save_tasks(tasks)
        flash("Task status updated.", "success")
    else:
        flash("Invalid task ID.", "error")
    return redirect(url_for("index"))

@app.route("/edit/<int:task_id>", methods=["GET", "POST"])
def edit(task_id):
    tasks = load_tasks()
    if not (0 <= task_id < len(tasks)):
        flash("Invalid task ID.", "error")
        return redirect(url_for("index"))

    task = tasks[task_id]
    if request.method == "POST":
        # Update task
        task_text = request.form.get("task", "").strip()
        priority = request.form.get("priority", "Low")
        deadline_raw = request.form.get("deadline", "").strip()
        description = request.form.get("description", "").strip()

        if not task_text:
            flash("Task text is required.", "error")
            return redirect(url_for("edit", task_id=task_id))

        deadline_dt = parse_deadline(deadline_raw)
        task["task"] = task_text
        task["priority"] = priority
        task["deadline"] = deadline_dt.isoformat() if deadline_dt else None
        task["description"] = description
        save_tasks(tasks)
        flash("Task updated.", "success")
        return redirect(url_for("index"))

    # prepare datetime-local value for form if present
    dl_value = ""
    if task.get("deadline"):
        try:
            # slice seconds to match datetime-local input (YYYY-MM-DDTHH:MM)
            dt = datetime.fromisoformat(task["deadline"])
            dl_value = dt.strftime("%Y-%m-%dT%H:%M")
        except:
            dl_value = ""

    return render_template("edit.html", task=task, task_id=task_id, dl_value=dl_value)

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)
