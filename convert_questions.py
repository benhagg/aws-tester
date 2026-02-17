import json

# Function to convert questions.txt to questions.json
def convert_questions_to_json(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:  # Specify UTF-8 encoding
        lines = file.readlines()

    questions = []
    current_question = {}
    question_number = 0

    for line in lines:
        line = line.strip()

        if line.startswith("Question #"):
            if current_question:
                questions.append(current_question)
                current_question = {}

            question_number += 1
            current_question["question_number"] = question_number
            current_question["question_text"] = ""
            current_question["options"] = []

        elif line.startswith("A.") or line.startswith("B.") or line.startswith("C.") or line.startswith("D."):
            current_question["options"].append(line)

        elif line:
            if "question_text" in current_question:
                current_question["question_text"] += (line + " ")

    if current_question:
        questions.append(current_question)

    with open(output_file, 'w', encoding='utf-8') as file:  # Specify UTF-8 encoding
        json.dump(questions, file, indent=2)

# File paths
input_file = "questions.txt"
output_file = "questions.json"

# Convert the file
convert_questions_to_json(input_file, output_file)

print(f"Conversion complete! Questions saved to {output_file}.")