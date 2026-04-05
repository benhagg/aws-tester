"""
Reload the database with correct answers from questions_merged.json.
This script updates test_answers.correct_answer, test_answers.is_correct,
and the stored correct_count in tests.
"""

import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
QUESTIONS_MERGED_PATH = DATA_DIR / "questions_merged.json"
DB_PATH = BASE_DIR / "study_tool.db"


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def reload_db_with_solutions():
    """Load solutions from JSON and update database test_answers"""
    
    # Load questions with solutions
    questions = load_json(QUESTIONS_MERGED_PATH)
    solutions_dict = {}
    for q in questions:
        # Convert "B & E" format to "B,E" format
        solution = q["solution"].replace(" & ", ",")
        solutions_dict[q["question_number"]] = solution
    
    # Connect to database
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Get all test_answers (either with missing correct_answer or need is_correct updated)
        cursor.execute(
            "SELECT id, question_number, selected_answer FROM test_answers"
        )
        rows = cursor.fetchall()
        
        print(f"Found {len(rows)} test_answers to process")
        
        # Update each answer with the solution from JSON and check if correct
        updated_count = 0
        for answer_id, question_number, selected_answer in rows:
            solution = solutions_dict.get(question_number)
            if solution:
                # Remove spaces from solution to format as comma-separated (no spaces)
                normalized_solution = ",".join(ans.strip() for ans in solution.split(","))
                # Check if selected_answer exactly matches correct_answer
                is_correct = 1 if selected_answer == normalized_solution else 0
                
                cursor.execute(
                    "UPDATE test_answers SET correct_answer = ?, is_correct = ? WHERE id = ?",
                    (normalized_solution, is_correct, answer_id)
                )
                updated_count += 1

        cursor.execute("SELECT id FROM tests")
        test_rows = cursor.fetchall()
        for (test_id,) in test_rows:
            cursor.execute(
                "SELECT COUNT(*) FROM test_answers WHERE test_id = ? AND is_correct = 1",
                (test_id,),
            )
            correct_count = cursor.fetchone()[0]
            cursor.execute(
                "UPDATE tests SET correct_count = ? WHERE id = ?",
                (correct_count, test_id),
            )
        
        conn.commit()
        print(f"Updated {updated_count} test_answers and refreshed tests.correct_count")


if __name__ == "__main__":
    reload_db_with_solutions()
