import json
import random
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_PATH = BASE_DIR / "questions_1.json"
DB_PATH = BASE_DIR / "study_tool.db"

app = Flask(__name__)
app.config["SECRET_KEY"] = "study-tool-dev"


def utc_now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL DEFAULT 0,
                started_at TEXT NOT NULL,
                last_resume_at TEXT,
                ended_at TEXT,
                total_elapsed_seconds REAL NOT NULL DEFAULT 0,
                show_feedback INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                question_number INTEGER NOT NULL,
                selected_answer TEXT NOT NULL,
                correct_answer TEXT,
                is_correct INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT NOT NULL,
                elapsed_seconds REAL NOT NULL,
                FOREIGN KEY (test_id) REFERENCES tests (id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS test_progress (
                test_id INTEGER PRIMARY KEY,
                order_json TEXT NOT NULL,
                current_index INTEGER NOT NULL,
                current_question_started_at TEXT,
                current_question_elapsed_seconds REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (test_id) REFERENCES tests (id)
            )
            """
        )
        try:
            conn.execute("ALTER TABLE tests ADD COLUMN show_feedback INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE tests ADD COLUMN name TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass


QUESTIONS = load_json(QUESTIONS_PATH)
QUESTIONS_BY_NUMBER = {q["question_number"]: q for q in QUESTIONS}
QUESTION_NUMBERS = [q["question_number"] for q in QUESTIONS]

init_db()


@app.template_filter("date_only")
def date_only(value):
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).strftime("%b %d, %Y %H:%M")
    except ValueError:
        return value[:16]


def db_query(query, params=(), one=False, commit=False):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        if commit:
            conn.commit()
        if one:
            return cursor.fetchone()
        return cursor.fetchall()


def normalize_answers(value):
    if not value:
        return []
    if isinstance(value, list):
        return [item.strip().upper() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = re.split(r"[,&]", value)
        normalized = [part.strip().upper() for part in parts]
        return [part for part in normalized if part]
    return []


def build_order(mode):
    ordered = sorted(QUESTION_NUMBERS)
    if mode == "random_questions":
        random.shuffle(ordered)
        return ordered
    if mode == "in_order_questions":
        return ordered
    if mode == "full_test_in_order":
        return ordered[:65]
    if mode == "full_test_random":
        return random.sample(ordered, min(65, len(ordered)))
    return ordered


def create_test(mode, show_feedback=False):
    order = build_order(mode)
    started_at = utc_now_iso()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tests (mode, status, total_questions, correct_count, started_at, last_resume_at, show_feedback)
            VALUES (?, ?, ?, 0, ?, ?, ?)
            """,
            (mode, "in_progress", len(order), started_at, started_at, 1 if show_feedback else 0),
        )
        test_id = cursor.lastrowid
        conn.execute(
            """
            INSERT INTO test_progress (test_id, order_json, current_index, current_question_started_at)
            VALUES (?, ?, 0, ?)
            """,
            (test_id, json.dumps(order), started_at),
        )
        conn.commit()
    return test_id


def get_progress(test_id):
    row = db_query(
        "SELECT order_json, current_index, current_question_started_at, current_question_elapsed_seconds FROM test_progress WHERE test_id = ?",
        (test_id,),
        one=True,
    )
    if not row:
        return None
    return {
        "order": json.loads(row["order_json"]),
        "current_index": row["current_index"],
        "current_question_started_at": row["current_question_started_at"],
        "current_question_elapsed_seconds": row["current_question_elapsed_seconds"],
    }


def update_progress(test_id, current_index, question_started_at, question_elapsed):
    db_query(
        """
        UPDATE test_progress
        SET current_index = ?, current_question_started_at = ?, current_question_elapsed_seconds = ?
        WHERE test_id = ?
        """,
        (current_index, question_started_at, question_elapsed, test_id),
        commit=True,
    )


def mark_paused(test_id):
    now = utc_now_iso()
    test = db_query("SELECT last_resume_at, total_elapsed_seconds FROM tests WHERE id = ?", (test_id,), one=True)
    progress = get_progress(test_id)
    total_elapsed = test["total_elapsed_seconds"]

    if test["last_resume_at"]:
        elapsed_delta = (datetime.fromisoformat(now) - datetime.fromisoformat(test["last_resume_at"]))
        total_elapsed += elapsed_delta.total_seconds()

    if progress and progress["current_question_started_at"]:
        question_elapsed = progress["current_question_elapsed_seconds"] or 0
        q_delta = (datetime.fromisoformat(now) - datetime.fromisoformat(progress["current_question_started_at"]))
        question_elapsed += q_delta.total_seconds()
        update_progress(test_id, progress["current_index"], None, question_elapsed)

    db_query(
        """
        UPDATE tests SET status = ?, last_resume_at = ?, total_elapsed_seconds = ? WHERE id = ?
        """,
        ("paused", None, total_elapsed, test_id),
        commit=True,
    )


def resume_test(test_id):
    now = utc_now_iso()
    progress = get_progress(test_id)
    if progress and progress["current_question_started_at"] is None:
        update_progress(test_id, progress["current_index"], now, progress["current_question_elapsed_seconds"])
    db_query(
        """
        UPDATE tests SET status = ?, last_resume_at = ? WHERE id = ?
        """,
        ("in_progress", now, test_id),
        commit=True,
    )


@app.route("/")
def home():
    paused_tests = db_query(
        "SELECT id, name, mode, started_at, total_questions FROM tests WHERE status = 'paused' ORDER BY started_at DESC"
    )
    recent_tests = db_query(
        """
        SELECT id, name, mode, status, total_questions, correct_count, started_at, ended_at, total_elapsed_seconds
        FROM tests
        WHERE status = 'completed'
        ORDER BY ended_at DESC
        LIMIT 5
        """
    )
    return render_template("index.html", paused_tests=paused_tests, recent_tests=recent_tests)


@app.route("/start", methods=["GET", "POST"])
def start():
    mode = request.values.get("mode")
    if not mode:
        return redirect(url_for("home"))
    allow_feedback = mode in {"random_questions", "in_order_questions"}
    show_feedback = False
    if allow_feedback:
        show_feedback = request.values.get("show_feedback") == "1"
    test_id = create_test(mode, show_feedback=show_feedback)
    return redirect(url_for("question", test_id=test_id))


@app.route("/resume")
def resume():
    test_id = request.args.get("test_id", type=int)
    if not test_id:
        return redirect(url_for("home"))
    resume_test(test_id)
    return redirect(url_for("question", test_id=test_id))


@app.route("/pause", methods=["POST"])
def pause():
    test_id = request.form.get("test_id", type=int)
    if test_id:
        mark_paused(test_id)
    return redirect(url_for("home"))


@app.route("/rename_test", methods=["POST"])
def rename_test():
    test_id = request.form.get("test_id", type=int)
    name = (request.form.get("name") or "").strip()
    if not test_id:
        return redirect(url_for("history"))
    if not name:
        test = db_query("SELECT mode, started_at FROM tests WHERE id = ?", (test_id,), one=True)
        if test:
            started_at = test["started_at"]
            name = f"{test['mode'].replace('_', ' ').title()} {datetime.fromisoformat(started_at).strftime('%b %d, %Y')}"
        else:
            name = "Untitled Test"
    if len(name) > 80:
        name = name[:80]
    db_query("UPDATE tests SET name = ? WHERE id = ?", (name, test_id), commit=True)
    return redirect(url_for("history"))


@app.route("/pause_beacon", methods=["POST"])
def pause_beacon():
    test_id = request.form.get("test_id", type=int)
    if not test_id:
        payload = request.get_json(silent=True) or {}
        try:
            test_id = int(payload.get("test_id"))
        except (TypeError, ValueError):
            test_id = None
    if test_id:
        mark_paused(test_id)
    return ("", 204)


@app.route("/question")
def question():
    test_id = request.args.get("test_id", type=int)
    if not test_id:
        return redirect(url_for("home"))
    test = db_query("SELECT * FROM tests WHERE id = ?", (test_id,), one=True)
    if not test:
        return redirect(url_for("home"))
    if test["status"] == "paused":
        return redirect(url_for("home"))
    progress = get_progress(test_id)
    if not progress:
        return redirect(url_for("home"))
    if progress["current_index"] >= len(progress["order"]):
        return redirect(url_for("history"))

    question_number = progress["order"][progress["current_index"]]
    question = QUESTIONS_BY_NUMBER.get(question_number)
    correct_answers = normalize_answers(question.get("solution"))
    is_last_question = (progress["current_index"] + 1) >= len(progress["order"])
    select_num = question.get("select_num", 1)

    return render_template(
        "question.html",
        test_id=test_id,
        question_number=question_number,
        question_text=question["question_text"],
        options=question["options"],
        current_index=progress["current_index"] + 1,
        total_questions=len(progress["order"]),
        correct_answers=correct_answers,
        explanation=question.get("explanation", ""),
        show_feedback=False,
        user_answers=[],
        is_last_question=is_last_question,
        select_num=select_num,
    )


@app.route("/answer", methods=["POST"])
def answer():
    test_id = request.form.get("test_id", type=int)
    selected_answers = normalize_answers(request.form.getlist("selected_answer"))
    if not test_id:
        return redirect(url_for("home"))

    test = db_query("SELECT * FROM tests WHERE id = ?", (test_id,), one=True)
    progress = get_progress(test_id)
    if not test or not progress:
        return redirect(url_for("home"))

    question_number = progress["order"][progress["current_index"]]
    question = QUESTIONS_BY_NUMBER.get(question_number, {})
    select_num = question.get("select_num", 1)
    if not selected_answers or len(selected_answers) != select_num:
        return redirect(url_for("question", test_id=test_id))
    correct_answers = normalize_answers(question.get("solution"))
    selected_answer = ",".join(selected_answers)
    is_correct = 1 if correct_answers and set(selected_answers) == set(correct_answers) else 0

    now = utc_now_iso()
    started_at = progress["current_question_started_at"] or now
    elapsed = progress["current_question_elapsed_seconds"]
    if progress["current_question_started_at"]:
        elapsed += (
            datetime.fromisoformat(now) - datetime.fromisoformat(progress["current_question_started_at"])
        ).total_seconds()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            INSERT INTO test_answers (test_id, question_number, selected_answer, correct_answer, is_correct, started_at, ended_at, elapsed_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (test_id, question_number, selected_answer, ",".join(correct_answers), is_correct, started_at, now, elapsed),
        )
        conn.commit()

    if is_correct:
        db_query(
            "UPDATE tests SET correct_count = correct_count + 1 WHERE id = ?",
            (test_id,),
            commit=True,
        )

    if test["show_feedback"] and test["mode"] in {"random_questions", "in_order_questions"}:
        update_progress(test_id, progress["current_index"], None, elapsed)
        is_last_question = (progress["current_index"] + 1) >= len(progress["order"])
        select_num = question.get("select_num", 1)
        return render_template(
            "question.html",
            test_id=test_id,
            question_number=question_number,
            question_text=question.get("question_text", ""),
            options=question.get("options", []),
            current_index=progress["current_index"] + 1,
            total_questions=len(progress["order"]),
            correct_answers=correct_answers,
            explanation=question.get("explanation", ""),
            show_feedback=True,
            user_answers=selected_answers,
            is_last_question=is_last_question,
            select_num=select_num,
        )

    next_index = progress["current_index"] + 1
    if next_index >= len(progress["order"]):
        total_elapsed = test["total_elapsed_seconds"]
        if test["last_resume_at"]:
            total_elapsed += (
                datetime.fromisoformat(now) - datetime.fromisoformat(test["last_resume_at"])
            ).total_seconds()
        db_query(
            """
            UPDATE tests
            SET status = ?, ended_at = ?, total_elapsed_seconds = ?
            WHERE id = ?
            """,
            ("completed", now, total_elapsed, test_id),
            commit=True,
        )
        update_progress(test_id, next_index, None, 0)
        return redirect(url_for("history"))

    update_progress(test_id, next_index, now, 0)
    return redirect(url_for("question", test_id=test_id))


@app.route("/next", methods=["POST"])
def next_question():
    test_id = request.form.get("test_id", type=int)
    if not test_id:
        return redirect(url_for("home"))

    test = db_query("SELECT * FROM tests WHERE id = ?", (test_id,), one=True)
    progress = get_progress(test_id)
    if not test or not progress:
        return redirect(url_for("home"))

    now = utc_now_iso()
    next_index = progress["current_index"] + 1
    if next_index >= len(progress["order"]):
        total_elapsed = test["total_elapsed_seconds"]
        if test["last_resume_at"]:
            total_elapsed += (
                datetime.fromisoformat(now) - datetime.fromisoformat(test["last_resume_at"])
            ).total_seconds()
        db_query(
            """
            UPDATE tests
            SET status = ?, ended_at = ?, total_elapsed_seconds = ?
            WHERE id = ?
            """,
            ("completed", now, total_elapsed, test_id),
            commit=True,
        )
        update_progress(test_id, next_index, None, 0)
        return redirect(url_for("history"))

    update_progress(test_id, next_index, now, 0)
    return redirect(url_for("question", test_id=test_id))


@app.route("/history")
def history():
    summary = db_query(
        """
        SELECT
            COUNT(*) AS total_answers,
            SUM(is_correct) AS correct_answers
        FROM test_answers
        """,
        one=True,
    )
    tests = db_query(
        """
        SELECT id, name, mode, status, total_questions, correct_count, started_at, ended_at, total_elapsed_seconds
        FROM tests
        ORDER BY started_at DESC
        """
    )
    recent_tests = db_query(
        """
        SELECT id, name, mode, status, total_questions, correct_count, started_at, ended_at, total_elapsed_seconds
        FROM tests
        WHERE status = 'completed'
        ORDER BY ended_at DESC
        LIMIT 5
        """
    )
    total_answers = summary["total_answers"] or 0
    correct_answers = summary["correct_answers"] or 0
    total_time = sum(test["total_elapsed_seconds"] or 0 for test in tests)
    percent_correct = (correct_answers / total_answers * 100) if total_answers else 0

    return render_template(
        "history.html",
        total_answers=total_answers,
        correct_percent=percent_correct,
        total_time=total_time,
        tests=tests,
        recent_tests=recent_tests,
    )


@app.route("/review")
def review():
    test_id = request.args.get("test_id", type=int)
    answer_id = request.args.get("answer_id", type=int)
    params = ()
    query = (
        """
        SELECT ta.id, ta.test_id, ta.question_number, ta.selected_answer, ta.correct_answer, ta.is_correct,
               ta.elapsed_seconds, t.mode, t.started_at, t.name
        FROM test_answers ta
        JOIN tests t ON t.id = ta.test_id
        """
    )
    if test_id:
        query += " WHERE ta.test_id = ?"
        params = (test_id,)
    query += " ORDER BY ta.id ASC"
    rows = db_query(query, params)
    items = []
    for row in rows:
        question = QUESTIONS_BY_NUMBER.get(row["question_number"], {})
        items.append(
            {
                "id": row["id"],
                "test_id": row["test_id"],
                "mode": row["mode"],
                "name": row["name"],
                "started_at": row["started_at"],
                "question_number": row["question_number"],
                "question_text": question.get("question_text", ""),
                "selected_answer": row["selected_answer"],
                "correct_answer": row["correct_answer"],
                "is_correct": row["is_correct"],
                "elapsed_seconds": row["elapsed_seconds"],
            }
        )

    selected_item = None
    if answer_id:
        detail_params = (answer_id,)
        detail_query = (
            """
            SELECT ta.id, ta.test_id, ta.question_number, ta.selected_answer, ta.correct_answer, ta.is_correct,
                   ta.elapsed_seconds, t.mode, t.started_at, t.name
            FROM test_answers ta
            JOIN tests t ON t.id = ta.test_id
            WHERE ta.id = ?
            """
        )
        if test_id:
            detail_query += " AND ta.test_id = ?"
            detail_params = (answer_id, test_id)
        row = db_query(detail_query, detail_params, one=True)
        if row:
            question = QUESTIONS_BY_NUMBER.get(row["question_number"], {})
            selected_item = {
                "id": row["id"],
                "test_id": row["test_id"],
                "mode": row["mode"],
                "name": row["name"],
                "started_at": row["started_at"],
                "question_number": row["question_number"],
                "question_text": question.get("question_text", ""),
                "options": question.get("options", []),
                "user_answers": normalize_answers(row["selected_answer"]),
                "correct_answers": normalize_answers(row["correct_answer"]),
                "is_correct": row["is_correct"],
                "elapsed_seconds": row["elapsed_seconds"],
                "explanation": question.get("explanation", ""),
                "select_num": question.get("select_num", 1),
            }

    return render_template(
        "review.html",
        items=items,
        test_id=test_id,
        selected_item=selected_item,
    )


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
