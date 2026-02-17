import json
import re
from pathlib import Path

# Load questions.json
def load_json(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Merge questions and solutions
def merge_questions_and_solutions(questions, solutions):
    merged_data = []

    solutions_dict = {item['question_number']: item for item in solutions}

    for question in questions:
        question_number = question['question_number']
        solution = solutions_dict.get(question_number)

        if solution:

            # Adjust to include 'answer_letter' as solution and 'explaination_text'
            merged_data.append({
                'question_number': question_number,
                'question_text': question['question_text'],
                'options': question.get('options', []),
                'solution': solution.get('answer_letter', None),
                'explanation': solution.get('explaination_text', None),
                'select_num': question.get('select_num', 1)  # Default to 1 if not provided
            })

    return merged_data

# Save merged data to a new file
def save_json(file_path, data):
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

# Main function
def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    questions_file = data_dir / "questions.json"
    solutions_file = data_dir / "solutions.json"
    output_file = data_dir / "questions_merged.json"

    questions = load_json(questions_file)
    solutions = load_json(solutions_file)

    merged_data = merge_questions_and_solutions(questions, solutions)

    save_json(output_file, merged_data)

if __name__ == "__main__":
    main()