# AWS Study Tool

A web-based study application for practicing AWS certification exam questions with real-time feedback, progress tracking, and test analytics.


## Running the App

Start the Flask development server:
```
python app.py
```

Then open your browser to:
```
http://localhost:5000
```

## Project Structure

```
aws-tester/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── study_tool.db         # SQLite database (auto-created)
├── data/
│   ├── questions_merged.json    # Question bank with answers
│   └── solutions.json           # Answer solutions
├── scripts/
│   ├── reload_db_with_solutions.py  # Database initialization
│   └── study_tool.py               # CLI study tool
├── templates/            # HTML templates
│   ├── base.html
│   ├── index.html        # Home page with study modes
│   ├── question.html     # Question view
│   ├── review.html       # Answer review
│   └── history.html      # Test history
└── static/
    └── styles.css        # Styling
```

## Usage

1. **Start a Test**
   - Choose a study mode (Random, In Order, or Full Test)
   - Configure optional settings (number of questions, feedback)
   - Confirm to start

2. **During the Test**
   - Select your answer(s) using mouse clicks or keyboard (A/B/C/D)
   - Press Enter to submit or click "Submit Answer"
   - View feedback immediately if enabled
   - Navigate using the question sidebar
   - Press the timer to see elapsed time
   - Flag questions for later review

3. **Pause & Resume**
   - Click "Exit" to pause the test anytime
   - Resume from "Paused Sessions" on the home page
   - Progress is saved automatically

4. **Review**
   - View answers and explanations in the Review section
   - Check your performance history

## Database Commands

To query the database directly:
```
sqlite3 study_tool.db
SELECT * FROM tests;
SELECT * FROM test_answers;
```

