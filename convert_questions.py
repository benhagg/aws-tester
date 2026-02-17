import json
import re

# Function to convert questions.txt to questions.json
def convert_questions_to_json(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as file:  # Specify UTF-8 encoding
        lines = file.readlines()

    questions = []
    current_question = {}
    question_number = 0

    option_pattern = re.compile(r'^[A-F]\.\s')  # Match options starting with A., B., etc.
    current_option = ""

    for line in lines:
        line = line.strip()

        if line.startswith("Question #"):
            if current_question:
                if current_option:  # Save the last option
                    current_question["options"].append(current_option.strip())
                questions.append(current_question)
                current_question = {}
                current_option = ""

            question_number += 1
            current_question["question_number"] = question_number
            current_question["question_text"] = ""
            current_question["options"] = []
            current_question["select_num"] = 1  # Default to 1 unless specified

        elif option_pattern.match(line):
            if current_option:  # Save the previous option
                current_question["options"].append(current_option.strip())
            current_option = line  # Start a new option
        elif line:
            if current_option:  # Continue the current option
                current_option += " " + line
            elif "question_text" in current_question:
                current_question["question_text"] += (line + " ")

                # Check for "(Choose two.)" or "(Choose three.)" in the question text
                if "(Choose two.)" in current_question["question_text"]:
                    current_question["select_num"] = 2
                elif "(Choose three.)" in current_question["question_text"]:
                    current_question["select_num"] = 3

    if current_question:
        if current_option:  # Save the last option
            current_question["options"].append(current_option.strip())
        questions.append(current_question)

    with open(output_file, 'w', encoding='utf-8') as file:  # Specify UTF-8 encoding
        json.dump(questions, file, indent=2)

# File paths
input_file = "questions.txt"
output_file = "questions.json"

# Convert the file
convert_questions_to_json(input_file, output_file)

print(f"Conversion complete! Questions saved to {output_file}.")