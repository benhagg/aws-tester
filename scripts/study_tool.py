import json
from pathlib import Path

def load_data(file_path):
    """Load JSON data from a file."""
    with open(file_path, 'r', encoding="utf-8") as file:
        return json.load(file)

def save_user_response(history_file, question_number, user_answer, correct_answer):
    """Save the user's response to a history file."""
    if not Path(history_file).exists():
        history = []
    else:
        with open(history_file, 'r', encoding="utf-8") as file:
            history = json.load(file)

    history.append({
        "question_number": question_number,
        "user_answer": user_answer,
        "correct_answer": correct_answer,
        "is_correct": user_answer == correct_answer
    })

    with open(history_file, 'w', encoding="utf-8") as file:
        json.dump(history, file, indent=4)

def run_study_tool(questions_file, solutions_file, history_file):
    """Run the interactive study tool."""
    questions = load_data(questions_file)
    solutions = load_data(solutions_file)

    print("Welcome to the AWS Study Tool!\n")

    for question in questions:
        question_number = question["question_number"]
        question_text = question["question_text"]
        options = question["options"]

        print(f"Question {question_number}: {question_text}\n")
        for option in options:
            print(option)

        user_answer = input("\nYour answer (e.g., A, B, C, D): ").strip().upper()

        solution = next((s for s in solutions if s["question_number"] == question_number), None)
        if solution:
            correct_answer = solution["answer_letter"]
            explanation = solution["explaination_text"]

            if user_answer == correct_answer:
                print("\nCorrect!\n")
            else:
                print(f"\nIncorrect. The correct answer is {correct_answer}.\n")

            print(f"Explanation: {explanation}\n")

            # Save the user's response
            save_user_response(history_file, question_number, user_answer, correct_answer)
        else:
            print("\nSolution not found for this question.\n")

        input("Press Enter to continue to the next question...\n")

    print("\nThank you for using the AWS Study Tool! Good luck with your studies!\n")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"
    QUESTIONS_FILE = DATA_DIR / "questions.json"
    SOLUTIONS_FILE = DATA_DIR / "solutions.json"
    HISTORY_FILE = DATA_DIR / "answer_history.json"

    run_study_tool(QUESTIONS_FILE, SOLUTIONS_FILE, HISTORY_FILE)